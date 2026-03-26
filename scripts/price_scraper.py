import json
import csv
import time
import re
import unicodedata
import random
from urllib.parse import quote
from playwright.sync_api import sync_playwright


# -----------------------------
# carregar redes
# -----------------------------
with open("data/redes.json", "r", encoding="utf-8") as f:
    redes = json.load(f)

# -----------------------------
# carregar produtos
# -----------------------------
with open("data/produtos.json", "r", encoding="utf-8") as f:
    produtos = json.load(f)


# -----------------------------
# salvar no CSV
# -----------------------------
def salvar_csv(registro):
    arquivo = "outputs/precos.csv"

    cabecalho = [
        "data_hora",
        "grupo_comparacao",
        "rede",
        "empresa",
        "marca",
        "ean",
        "produto",
        "volume_ml",
        "concentracao_mg_ml",
        "total_mg",
        "tipo_produto",
        "preco_principal",
        "preco_promocional",
        "url"
    ]

    try:
        with open(arquivo, "x", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cabecalho)
            writer.writeheader()
    except FileExistsError:
        pass

    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cabecalho)
        writer.writerow(registro)


# -----------------------------
# utilitários
# -----------------------------
def remover_acentos(texto):
    if not texto:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )


def normalizar_texto(texto):
    if not texto:
        return ""

    texto = remover_acentos(str(texto).lower().strip())
    texto = texto.replace("ml.", "ml")
    texto = texto.replace("mg.", "mg")
    texto = texto.replace("solucao oral", "solucao")
    texto = texto.replace("solucao gotas", "solucao")
    texto = texto.replace("gotas", "solucao")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def extrair_precos(texto):
    if not texto:
        return []

    padrao = r"R\$\s*\d{1,4}(?:\.\d{3})*,\d{2}"
    encontrados = re.findall(padrao, texto)

    unicos = []
    vistos = set()

    for preco in encontrados:
        preco_limpo = " ".join(preco.split())
        if preco_limpo not in vistos:
            vistos.add(preco_limpo)
            unicos.append(preco_limpo)

    return unicos


def preco_para_float(preco_texto):
    preco_texto = str(preco_texto).replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(preco_texto)


def escolher_preco_promocional(lista_precos, preco_minimo=1.0):
    if not lista_precos:
        return "NAO_ENCONTRADO"

    validos = []

    for preco in lista_precos:
        try:
            valor = preco_para_float(preco)
            if preco_minimo <= valor < 100000:
                validos.append((valor, preco))
        except Exception:
            continue

    if not validos:
        return "NAO_ENCONTRADO"

    validos.sort(key=lambda x: x[0])
    return validos[0][1]


def escolher_preco_promocional_por_produto(lista_precos, produto):
    if not lista_precos:
        return "NAO_ENCONTRADO"

    try:
        volume_ml = float(str(produto.get("volume_ml", "")).replace(",", "."))
    except Exception:
        volume_ml = 0.0

    try:
        concentracao = float(str(produto.get("concentracao_mg_ml", "")).replace(",", "."))
    except Exception:
        concentracao = 0.0

    preco_minimo = 100.0

    if volume_ml and concentracao:
        total_estimado = volume_ml * concentracao
        if total_estimado < 80:
            preco_minimo = 50.0

    return escolher_preco_promocional(lista_precos, preco_minimo=preco_minimo)


def escolher_preco_panvel_pdp_por_produto(lista_precos, produto):
    if not lista_precos:
        return "NAO_ENCONTRADO"

    try:
        volume_ml = float(str(produto.get("volume_ml", "")).replace(",", "."))
    except Exception:
        volume_ml = 0.0

    try:
        concentracao = float(str(produto.get("concentracao_mg_ml", "")).replace(",", "."))
    except Exception:
        concentracao = 0.0

    preco_minimo = 100.0

    if volume_ml and concentracao:
        total_estimado = volume_ml * concentracao
        if total_estimado < 80:
            preco_minimo = 50.0

    validos = []

    for preco in lista_precos:
        try:
            valor = preco_para_float(preco)
            if preco_minimo <= valor < 100000:
                validos.append((valor, preco))
        except Exception:
            continue

    if not validos:
        return "NAO_ENCONTRADO"

    validos.sort(key=lambda x: x[0], reverse=True)
    return validos[0][1]


def montar_busca_inteligente(produto, rede_nome):
    busca_original = produto.get("produto_busca", "")
    marca = produto.get("marca", "")
    concentracao = produto.get("concentracao_mg_ml", "")
    volume_ml = produto.get("volume_ml", "")

    if rede_nome in ["DrogariaSaoPaulo", "PagueMenos"]:
        nome_normalizado = normalizar_texto(busca_original)

        if "extrato de cannabis sativa" in nome_normalizado:
            partes = ["canabidiol"]

            if concentracao:
                partes.append(f"{concentracao}mg/ml")

            if volume_ml:
                partes.append(f"{volume_ml}ml")

            if marca:
                partes.append(marca)

            return " ".join(partes)

    return busca_original


def esperar_humano(page, minimo=1200, maximo=2600):
    tempo = random.randint(minimo, maximo)
    page.wait_for_timeout(tempo)


def rolar_humano(page):
    try:
        page.mouse.wheel(0, random.randint(300, 700))
        page.wait_for_timeout(random.randint(500, 1100))
        page.mouse.wheel(0, -random.randint(150, 450))
        page.wait_for_timeout(random.randint(400, 900))
    except Exception:
        pass


def aplicar_stealth_basico(page):
    try:
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });

            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            window.chrome = {
                runtime: {}
            };

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );
        """)
    except Exception:
        pass


# -----------------------------
# scoring técnico
# -----------------------------
def score_texto_produto(produto, texto, href=""):
    texto_norm = normalizar_texto(texto)
    href_norm = normalizar_texto(href)

    marca = normalizar_texto(produto.get("marca", ""))
    volume_ml = normalizar_texto(produto.get("volume_ml", ""))
    concentracao = normalizar_texto(produto.get("concentracao_mg_ml", ""))
    busca = normalizar_texto(produto.get("produto_busca", ""))

    score = 0.0
    motivos = []

    if volume_ml:
        if f"{volume_ml}ml" in texto_norm or f"{volume_ml} ml" in texto_norm or f"{volume_ml}ml" in href_norm:
            score += 15
            motivos.append("volume_ml")
        else:
            score -= 50
            motivos.append("volume_nao_bate")

    if concentracao:
        if (
            f"{concentracao}mg/ml" in texto_norm
            or f"{concentracao} mg/ml" in texto_norm
            or f"{concentracao}mg/ml" in href_norm
            or f"{concentracao}".replace(",", "-") in href_norm
        ):
            score += 20
            motivos.append("concentracao_mg_ml")
        else:
            score -= 60
            motivos.append("concentracao_nao_bate")

    if marca:
        if marca in texto_norm or marca in href_norm:
            score += 12
            motivos.append("marca")

    if "canabidiol" in texto_norm or "canabidiol" in href_norm:
        score += 8
        motivos.append("canabidiol")

    if "extrato de cannabis sativa" in busca:
        if "extrato" in texto_norm or "cannabis" in texto_norm or "extrato" in href_norm:
            score += 8
            motivos.append("extrato_cannabis")

    if busca and busca in texto_norm:
        score += 15
        motivos.append("busca_exata_no_texto")

    return score, motivos


# -----------------------------
# RD
# -----------------------------
def obter_cards_rd(page):
    seletores_rd = [
        '[data-testid="product-card"]',
        '[class*="product-card"]',
        '[class*="ProductCard"]',
        "article",
        "li"
    ]

    for seletor in seletores_rd:
        try:
            elementos = page.locator(seletor)
            quantidade = elementos.count()
            if quantidade > 0:
                print(f"[SCRAPER] Cards localizados com seletor: {seletor} | quantidade: {quantidade}")
                return elementos, seletor, quantidade
        except Exception:
            continue

    return None, None, 0


def extrair_nome_card(card):
    seletores_nome = [
        "h2",
        "h3",
        "span",
        "p",
        "a[title]",
        "[title]",
        '[class*="name"]',
        '[class*="title"]',
        '[class*="productName"]',
        '[class*="product-name"]'
    ]

    for seletor in seletores_nome:
        try:
            loc = card.locator(seletor)
            qtd = min(loc.count(), 10)

            for i in range(qtd):
                try:
                    texto = loc.nth(i).inner_text(timeout=800).strip()
                    if texto and len(texto) > 8 and "R$" not in texto:
                        return texto
                except Exception:
                    pass
        except Exception:
            pass

    try:
        texto = card.inner_text(timeout=1500).strip()
        if texto:
            linhas = [x.strip() for x in texto.split("\n") if x.strip()]
            for linha in linhas:
                if "R$" not in linha and len(linha) > 8:
                    return linha
    except Exception:
        pass

    return ""


def extrair_url_card(card, url_base):
    try:
        href = card.get_attribute("href")
        if href:
            if href.startswith("http"):
                return href
            return url_base.rstrip("/") + "/" + href.lstrip("/")
    except Exception:
        pass

    try:
        link = card.locator("a").first.get_attribute("href")
        if link:
            if link.startswith("http"):
                return link
            return url_base.rstrip("/") + "/" + link.lstrip("/")
    except Exception:
        pass

    return ""


def extrair_precos_card(card):
    try:
        texto_card = card.inner_text(timeout=2500)
        return extrair_precos(texto_card)
    except Exception:
        return []


def selecionar_melhor_card(cards, quantidade, produto, url_base, limite=20):
    melhor = None
    top = []

    total_avaliar = min(quantidade, limite)

    for idx in range(total_avaliar):
        try:
            card = cards.nth(idx)
            nome_card = extrair_nome_card(card)

            if not nome_card:
                continue

            precos_card = extrair_precos_card(card)
            url_card = extrair_url_card(card, url_base)

            if not precos_card:
                continue

            score, motivos = score_texto_produto(produto, nome_card, url_card)

            item = {
                "indice": idx,
                "nome_card": nome_card,
                "precos_card": precos_card,
                "url_card": url_card,
                "score": score,
                "motivos": motivos
            }

            top.append(item)

            if melhor is None or item["score"] > melhor["score"]:
                melhor = item

        except Exception:
            continue

    top.sort(key=lambda x: x["score"], reverse=True)
    return melhor, top[:5]


def preparar_navegacao_rd(page, rede_info):
    url_base = rede_info["url_base"]

    try:
        page.goto(url_base, wait_until="domcontentloaded", timeout=60000)
        esperar_humano(page, 1800, 3200)
        rolar_humano(page)
    except Exception:
        pass


def buscar_rd(page, produto, rede_info):
    busca = produto["produto_busca"]
    rede = rede_info["nome"]
    url_base = rede_info["url_base"]

    preparar_navegacao_rd(page, rede_info)

    url_busca = f"{url_base}/search?w={quote(busca)}"

    print(f"[{rede}] Abrindo busca RD...")
    print(f"[{rede}] URL: {url_busca}")

    page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
    esperar_humano(page, 2200, 4200)
    rolar_humano(page)

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    print(f"[{rede}] Título da página: {page.title()}")

    cards, seletor_usado, quantidade = obter_cards_rd(page)

    if not cards or quantidade == 0:
        print(f"[{rede}] Nenhum card de produto encontrado.")
        return "", "NAO_ENCONTRADO", page.url

    melhor_card, top5 = selecionar_melhor_card(cards, quantidade, produto, url_base)

    print(f"[{rede}] Seletor de card usado: {seletor_usado}")
    print(f"[{rede}] Top matches encontrados:")
    for item in top5:
        print(
            f"    índice={item['indice']} | score={item['score']} | "
            f"nome={item['nome_card']} | motivos={item['motivos']} | precos={item['precos_card']}"
        )

    if melhor_card is None:
        print(f"[{rede}] Nenhum card válido encontrado após scoring.")
        return "", "NAO_ENCONTRADO", page.url

    preco_promocional = escolher_preco_promocional_por_produto(melhor_card["precos_card"], produto)

    print(f"[{rede}] Melhor card escolhido: {melhor_card['nome_card']}")
    print(f"[{rede}] Motivos do match: {melhor_card['motivos']}")
    print(f"[{rede}] Preço escolhido: {preco_promocional}")

    return melhor_card["nome_card"], preco_promocional, melhor_card["url_card"] or page.url


# -----------------------------
# DPSP
# -----------------------------
def esperar_resultados_dpsp(page):
    try:
        page.wait_for_timeout(5000)
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, -1800)
        page.wait_for_timeout(1500)
    except Exception:
        pass


def href_parece_produto_dpsp(href):
    if not href:
        return False

    href_lower = href.lower()

    if "/pesquisa?" in href_lower:
        return False

    if "/search?" in href_lower:
        return False

    if "privacytools" in href_lower:
        return False

    if "javascript:" in href_lower:
        return False

    if href_lower.endswith("#"):
        return False

    return "/p" in href_lower


def texto_parece_produto_dpsp(texto, href, produto):
    texto_norm = normalizar_texto(texto)
    href_norm = normalizar_texto(href)

    if not texto_norm or len(texto_norm) < 8:
        return False

    if "resultado de busca" in texto_norm:
        return False

    marca = normalizar_texto(produto.get("marca", ""))
    volume_ml = normalizar_texto(produto.get("volume_ml", ""))
    concentracao = normalizar_texto(produto.get("concentracao_mg_ml", ""))

    if volume_ml:
        ok_volume = (
            f"{volume_ml}ml" in texto_norm
            or f"{volume_ml} ml" in texto_norm
            or f"{volume_ml}ml" in href_norm
        )
        if not ok_volume:
            return False

    if concentracao:
        concentracao_slug = concentracao.replace(",", "-")
        ok_concentracao = (
            f"{concentracao}mg/ml" in texto_norm
            or f"{concentracao} mg/ml" in texto_norm
            or f"{concentracao}mg/ml" in href_norm
            or concentracao_slug in href_norm
        )
        if not ok_concentracao:
            return False

    if marca:
        if marca not in texto_norm and marca not in href_norm:
            return False

    if "canabidiol" not in texto_norm and "canabidiol" not in href_norm and "cannabis" not in href_norm:
        return False

    return True


def extrair_card_contexto_dpsp(anchor):
    candidatos_xpath = [
        "ancestor::article[1]",
        "ancestor::li[1]",
        "ancestor::div[contains(@class,'product')][1]",
        "ancestor::div[contains(@class,'shelf')][1]",
        "ancestor::div[contains(@class,'card')][1]",
        "ancestor::div[1]"
    ]

    for xp in candidatos_xpath:
        try:
            card = anchor.locator(f"xpath={xp}")
            if card.count() > 0:
                txt = card.first.inner_text(timeout=1000).strip()
                if txt and len(txt) > 10:
                    return card.first, txt
        except Exception:
            pass

    try:
        txt = anchor.inner_text(timeout=1000).strip()
        return anchor, txt
    except Exception:
        return anchor, ""


def extrair_candidatos_dpsp(page, produto, url_base):
    candidatos = []
    vistos = set()

    try:
        anchors = page.locator("a")
        qtd = anchors.count()
        print(f"[SCRAPER] Âncoras totais na DPSP: {qtd}")
    except Exception:
        return []

    limite = min(qtd, 350)

    for i in range(limite):
        try:
            a = anchors.nth(i)

            href = a.get_attribute("href")
            if not href:
                continue

            if not href.startswith("http"):
                href = url_base.rstrip("/") + "/" + href.lstrip("/")

            if href in vistos:
                continue

            if not href_parece_produto_dpsp(href):
                continue

            texto_link = ""
            try:
                texto_link = a.inner_text(timeout=500).strip()
            except Exception:
                pass

            if not texto_parece_produto_dpsp(texto_link, href, produto):
                continue

            _, texto_card = extrair_card_contexto_dpsp(a)

            score, motivos = score_texto_produto(produto, texto_link + " " + texto_card, href)
            precos_card = extrair_precos(texto_card)
            preco_card = escolher_preco_promocional_por_produto(precos_card, produto)

            item = {
                "href": href,
                "texto_link": texto_link,
                "texto_card": texto_card,
                "precos_card": precos_card,
                "preco_card": preco_card,
                "score": score,
                "motivos": motivos
            }

            vistos.add(href)
            candidatos.append(item)

        except Exception:
            continue

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    return candidatos


def buscar_dpsp(page, produto, rede_info):
    rede = rede_info["nome"]
    url_base = rede_info["url_base"]
    busca = montar_busca_inteligente(produto, rede)

    url_busca = f"{url_base}/pesquisa?q={quote(busca)}"

    print(f"[{rede}] Tentando busca direta DPSP...")
    print(f"[{rede}] Busca usada: {busca}")
    print(f"[{rede}] URL: {url_busca}")

    page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
    esperar_resultados_dpsp(page)

    print(f"[{rede}] Título da página: {page.title()}")
    print(f"[{rede}] URL final após busca: {page.url}")

    candidatos = extrair_candidatos_dpsp(page, produto, url_base)

    print(f"[{rede}] Links candidatos válidos: {len(candidatos)}")
    for i, item in enumerate(candidatos[:5]):
        print(
            f"[{rede}] Candidato {i}: {item['href']} | "
            f"texto={item['texto_link']} | score={item['score']} | "
            f"motivos={item['motivos']} | precos_card={item['precos_card']}"
        )

    if not candidatos:
        print(f"[{rede}] Nenhum link válido após filtro de texto + URL.")
        return "", "NAO_ENCONTRADO", page.url

    candidatos_validos = []

    for item in candidatos[:5]:
        if item["preco_card"] == "NAO_ENCONTRADO":
            continue

        if item["score"] < 10:
            continue

        if "volume_nao_bate" in item["motivos"]:
            continue

        if "concentracao_nao_bate" in item["motivos"]:
            continue

        nome_produto = item["texto_link"] if item["texto_link"] else produto["produto_busca"]

        candidatos_validos.append({
            "nome": nome_produto,
            "preco": item["preco_card"],
            "url": item["href"],
            "score": item["score"],
            "motivos": item["motivos"]
        })

    print(f"[{rede}] Top matches encontrados:")
    for idx, item in enumerate(candidatos_validos[:5]):
        print(
            f"    índice={idx} | score={item['score']} | "
            f"nome={item['nome']} | motivos={item['motivos']} | preco={item['preco']}"
        )

    if not candidatos_validos:
        print(f"[{rede}] Nenhum card válido encontrado após scoring.")
        return "", "NAO_ENCONTRADO", page.url

    melhor = sorted(candidatos_validos, key=lambda x: x["score"], reverse=True)[0]

    print(f"[{rede}] Melhor card escolhido: {melhor['nome']}")
    print(f"[{rede}] Motivos do match: {melhor['motivos']}")
    print(f"[{rede}] Preço escolhido: {melhor['preco']}")

    return melhor["nome"], melhor["preco"], melhor["url"]


# -----------------------------
# Pague Menos
# -----------------------------
def esperar_resultados_paguemenos(page):
    try:
        page.wait_for_timeout(5000)
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1200)
        page.mouse.wheel(0, -800)
        page.wait_for_timeout(1200)
    except Exception:
        pass


def href_parece_produto_paguemenos(href):
    if not href:
        return False

    href_lower = href.lower()

    if "/busca?" in href_lower:
        return False

    if "/search?" in href_lower:
        return False

    if "javascript:" in href_lower:
        return False

    if href_lower.endswith("#"):
        return False

    return href_lower.endswith("/p") or "/p?" in href_lower or "/p/" in href_lower


def texto_parece_produto_paguemenos(texto, href, produto):
    texto_norm = normalizar_texto(texto)
    href_norm = normalizar_texto(href)

    if not texto_norm or len(texto_norm) < 8:
        return False

    marca = normalizar_texto(produto.get("marca", ""))
    volume_ml = normalizar_texto(produto.get("volume_ml", ""))
    concentracao = normalizar_texto(produto.get("concentracao_mg_ml", ""))

    score_local = 0

    if volume_ml:
        if (
            f"{volume_ml}ml" in texto_norm
            or f"{volume_ml} ml" in texto_norm
            or f"{volume_ml}ml" in href_norm
        ):
            score_local += 1

    if concentracao:
        concentracao_slug = concentracao.replace(",", "-")
        if (
            f"{concentracao}mg/ml" in texto_norm
            or f"{concentracao} mg/ml" in texto_norm
            or f"{concentracao}mg/ml" in href_norm
            or concentracao_slug in href_norm
        ):
            score_local += 1

    if marca:
        if marca in texto_norm or marca in href_norm:
            score_local += 1

    if (
        "canabidiol" in texto_norm
        or "canabidiol" in href_norm
        or "cannabis" in texto_norm
        or "cannabis" in href_norm
    ):
        score_local += 1

    return score_local >= 2


def extrair_nome_limpo_paguemenos(texto_card):
    if not texto_card:
        return ""

    linhas = [x.strip() for x in texto_card.split("\n") if x.strip()]
    linhas_boas = []

    textos_ruins = [
        "desconto de laboratorio",
        "por ate"
    ]

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if any(item in linha_norm for item in textos_ruins):
            continue

        if "r$" in linha:
            continue

        if linha_norm.isdigit():
            continue

        if len(linha_norm) < 5:
            continue

        linhas_boas.append(linha)

    if not linhas_boas:
        return ""

    nome = " ".join(linhas_boas[:3]).strip()
    return nome


def extrair_card_contexto_paguemenos(anchor):
    candidatos_xpath = [
        "ancestor::article[1]",
        "ancestor::li[1]",
        "ancestor::div[contains(@class,'product')][1]",
        "ancestor::div[contains(@class,'card')][1]",
        "ancestor::div[1]"
    ]

    for xp in candidatos_xpath:
        try:
            card = anchor.locator(f"xpath={xp}")
            if card.count() > 0:
                texto_bruto = card.first.inner_text(timeout=1000).strip()
                if texto_bruto and len(texto_bruto) > 10:
                    return card.first, texto_bruto
        except Exception:
            pass

    try:
        texto_bruto = anchor.inner_text(timeout=1000).strip()
        return anchor, texto_bruto if texto_bruto else ""
    except Exception:
        return anchor, ""


def extrair_candidatos_paguemenos(page, produto, url_base):
    candidatos = []
    vistos = set()

    try:
        anchors = page.locator("a")
        qtd = anchors.count()
        print(f"[SCRAPER] Âncoras totais na PagueMenos: {qtd}")
    except Exception:
        return []

    limite = min(qtd, 350)

    for i in range(limite):
        try:
            a = anchors.nth(i)

            href = a.get_attribute("href")
            if not href:
                continue

            if not href.startswith("http"):
                href = url_base.rstrip("/") + "/" + href.lstrip("/")

            if href in vistos:
                continue

            if not href_parece_produto_paguemenos(href):
                continue

            texto_link = ""
            try:
                texto_link = a.inner_text(timeout=500).strip()
            except Exception:
                pass

            texto_combinado_base = f"{texto_link} {href}"

            if not texto_parece_produto_paguemenos(texto_combinado_base, href, produto):
                try:
                    _, texto_card_teste = extrair_card_contexto_paguemenos(a)
                    texto_combinado_teste = f"{texto_link} {texto_card_teste} {href}"
                    if not texto_parece_produto_paguemenos(texto_combinado_teste, href, produto):
                        continue
                except Exception:
                    continue

            _, texto_card_bruto = extrair_card_contexto_paguemenos(a)
            nome_limpo = extrair_nome_limpo_paguemenos(texto_card_bruto)

            texto_para_score = f"{texto_link} {texto_card_bruto}"
            score, motivos = score_texto_produto(produto, texto_para_score, href)

            precos_card = extrair_precos(texto_card_bruto)
            preco_card = escolher_preco_promocional_por_produto(precos_card, produto)

            item = {
                "href": href,
                "texto_link": texto_link,
                "texto_card_bruto": texto_card_bruto,
                "nome_limpo": nome_limpo,
                "precos_card": precos_card,
                "preco_card": preco_card,
                "score": score,
                "motivos": motivos
            }

            vistos.add(href)
            candidatos.append(item)

        except Exception:
            continue

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    return candidatos


def buscar_paguemenos(page, produto, rede_info):
    rede = rede_info["nome"]
    url_base = rede_info["url_base"]
    busca = montar_busca_inteligente(produto, rede)

    url_busca = f"{url_base}/busca?termo={quote(busca)}"

    print(f"[{rede}] Tentando busca direta Pague Menos...")
    print(f"[{rede}] Busca usada: {busca}")
    print(f"[{rede}] URL: {url_busca}")

    page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
    esperar_resultados_paguemenos(page)

    print(f"[{rede}] Título da página: {page.title()}")
    print(f"[{rede}] URL final após busca: {page.url}")

    candidatos = extrair_candidatos_paguemenos(page, produto, url_base)

    print(f"[{rede}] Links candidatos válidos: {len(candidatos)}")
    for i, item in enumerate(candidatos[:5]):
        print(
            f"[{rede}] Candidato {i}: {item['href']} | "
            f"nome_limpo={item['nome_limpo']} | score={item['score']} | "
            f"motivos={item['motivos']} | precos_card={item['precos_card']}"
        )

    if not candidatos:
        print(f"[{rede}] Nenhum link válido após filtro de texto + URL.")
        return "", "NAO_ENCONTRADO", page.url

    candidatos_validos = []

    for item in candidatos[:5]:
        if item["preco_card"] == "NAO_ENCONTRADO":
            continue

        if item["score"] < 10:
            continue

        if "volume_nao_bate" in item["motivos"]:
            continue

        if "concentracao_nao_bate" in item["motivos"]:
            continue

        nome_produto = item["nome_limpo"] if item["nome_limpo"] else (item["texto_link"] if item["texto_link"] else produto["produto_busca"])

        candidatos_validos.append({
            "nome": item["nome_limpo"] if item["nome_limpo"] else nome_produto,
            "preco": item["preco_card"],
            "url": item["href"],
            "score": item["score"],
            "motivos": item["motivos"]
        })

    print(f"[{rede}] Top matches encontrados:")
    for idx, item in enumerate(candidatos_validos[:5]):
        print(
            f"    índice={idx} | score={item['score']} | "
            f"nome={item['nome']} | motivos={item['motivos']} | preco={item['preco']}"
        )

    if not candidatos_validos:
        print(f"[{rede}] Nenhum card válido encontrado após scoring.")
        return "", "NAO_ENCONTRADO", page.url

    melhor = sorted(candidatos_validos, key=lambda x: x["score"], reverse=True)[0]

    print(f"[{rede}] Melhor card escolhido: {melhor['nome']}")
    print(f"[{rede}] Motivos do match: {melhor['motivos']}")
    print(f"[{rede}] Preço escolhido: {melhor['preco']}")

    return melhor["nome"], melhor["preco"], melhor["url"]


# -----------------------------
# Panvel
# -----------------------------
def construir_url_busca_panvel(produto):
    termo = "canabidiol"
    return f"https://www.panvel.com/panvel/buscarProduto.do?termoPesquisa={quote(termo)}"


def href_parece_produto_panvel(href):
    if not href:
        return False

    href_lower = href.lower()

    if "buscarproduto.do" in href_lower:
        return False

    if "javascript:" in href_lower:
        return False

    if href_lower.endswith("#"):
        return False

    if "mailto:" in href_lower:
        return False

    if "facebook" in href_lower or "instagram" in href_lower or "linkedin" in href_lower:
        return False

    if "whatsapp" in href_lower:
        return False

    if "/categoria/" in href_lower:
        return False

    if "/institucional/" in href_lower:
        return False

    if "/atendimento/" in href_lower:
        return False

    if "/lojas/" in href_lower:
        return False

    if "/servicos/" in href_lower:
        return False

    if "/busca" in href_lower:
        return False

    if "/search" in href_lower:
        return False

    if "/produto/" in href_lower:
        return True

    if "/p-" in href_lower:
        return True

    if href_lower.endswith(".html"):
        return True

    return False


def extrair_card_contexto_panvel(anchor):
    candidatos_xpath = [
        "ancestor::div[contains(@class,'product')][1]",
        "ancestor::div[contains(@class,'produto')][1]",
        "ancestor::div[contains(@class,'item')][1]",
        "ancestor::li[1]",
        "ancestor::article[1]",
        "ancestor::div[1]"
    ]

    melhores = []

    for xp in candidatos_xpath:
        try:
            card = anchor.locator(f"xpath={xp}")
            if card.count() == 0:
                continue

            texto = card.first.inner_text(timeout=1200).strip()
            if not texto or len(texto) < 10:
                continue

            precos = extrair_precos(texto)

            melhores.append({
                "card": card.first,
                "texto": texto,
                "tamanho": len(texto),
                "qtd_precos": len(precos)
            })
        except Exception:
            continue

    if melhores:
        com_preco = [x for x in melhores if x["qtd_precos"] > 0]

        if com_preco:
            com_preco.sort(key=lambda x: x["tamanho"])
            return com_preco[0]["card"], com_preco[0]["texto"]

        melhores.sort(key=lambda x: x["tamanho"])
        return melhores[0]["card"], melhores[0]["texto"]

    try:
        texto = anchor.inner_text(timeout=1000).strip()
        return anchor, texto if texto else ""
    except Exception:
        return anchor, ""


def extrair_nome_limpo_panvel(texto_card):
    if not texto_card:
        return ""

    linhas = [x.strip() for x in texto_card.split("\n") if x.strip()]
    linhas_boas = []

    textos_ruins = [
        "comprar",
        "adicionar",
        "carrinho",
        "favoritos",
        "compare",
        "veja mais",
        "patrocinado"
    ]

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if "r$" in linha.lower():
            break

        if linha_norm.startswith("por "):
            break

        if any(item in linha_norm for item in textos_ruins):
            continue

        if len(linha_norm) < 6:
            continue

        linhas_boas.append(linha)

        if len(linhas_boas) >= 2:
            break

    if not linhas_boas:
        return ""

    return " ".join(linhas_boas).strip()


def panvel_tem_concentracao_conflitante(texto, concentracao_correta):
    texto_norm = normalizar_texto(texto)
    concentracoes_catalogo = sorted(
        list({normalizar_texto(str(p.get("concentracao_mg_ml", ""))) for p in produtos if p.get("concentracao_mg_ml", "")}),
        key=len,
        reverse=True
    )

    for conc in concentracoes_catalogo:
        if not conc:
            continue

        if conc == concentracao_correta:
            continue

        if conc in texto_norm or conc.replace(",", "-") in texto_norm:
            return True

    return False


def panvel_tem_volume_conflitante(texto, volume_correto):
    texto_norm = normalizar_texto(texto)
    volumes_catalogo = sorted(
        list({normalizar_texto(str(p.get("volume_ml", ""))) for p in produtos if p.get("volume_ml", "")}),
        key=len,
        reverse=True
    )

    for vol in volumes_catalogo:
        if not vol:
            continue

        if vol == volume_correto:
            continue

        if f"{vol}ml" in texto_norm or f"{vol} ml" in texto_norm:
            return True

    return False


def texto_parece_produto_panvel_exato(nome_limpo, href, produto):
    nome_norm = normalizar_texto(nome_limpo)
    href_norm = normalizar_texto(href)

    marca = normalizar_texto(produto.get("marca", ""))
    volume_ml = normalizar_texto(produto.get("volume_ml", ""))
    concentracao = normalizar_texto(produto.get("concentracao_mg_ml", ""))
    busca_norm = normalizar_texto(produto.get("produto_busca", ""))

    produto_eh_extrato = "extrato de cannabis sativa" in busca_norm

    if volume_ml:
        ok_volume = (
            f"{volume_ml}ml" in nome_norm
            or f"{volume_ml} ml" in nome_norm
            or f"{volume_ml}ml" in href_norm
            or f"-{volume_ml}-ml" in href_norm
        )
        if not ok_volume:
            return False

    if concentracao:
        ok_concentracao = (
            f"{concentracao}mg/ml" in nome_norm
            or f"{concentracao} mg/ml" in nome_norm
            or f"{concentracao}mg/ml" in href_norm
            or concentracao.replace(",", "-") in href_norm
        )
        if not ok_concentracao:
            return False

    if marca:
        if marca not in nome_norm and marca not in href_norm:
            return False

    if produto_eh_extrato:
        if (
            "extrato" not in nome_norm
            and "cannabis" not in nome_norm
            and "extrato" not in href_norm
            and "cannabis" not in href_norm
        ):
            return False
    else:
        if "extrato-cannabis-sativa" in href_norm:
            return False

    if panvel_tem_concentracao_conflitante(href_norm, concentracao):
        return False

    if panvel_tem_volume_conflitante(href_norm, volume_ml):
        return False

    return True


def extrair_candidatos_panvel(page, produto):
    candidatos = []
    vistos = set()

    try:
        anchors = page.locator("a[href]")
        qtd = anchors.count()
        print(f"[PANVEL] Âncoras totais encontradas: {qtd}")
    except Exception:
        return []

    limite = min(qtd, 450)

    for i in range(limite):
        try:
            a = anchors.nth(i)

            href = a.get_attribute("href")
            if not href:
                continue

            if not href.startswith("http"):
                href = "https://www.panvel.com" + (href if href.startswith("/") else "/" + href)

            if href in vistos:
                continue

            if not href_parece_produto_panvel(href):
                continue

            texto_link = ""
            try:
                texto_link = a.inner_text(timeout=500).strip()
            except Exception:
                pass

            _, texto_card = extrair_card_contexto_panvel(a)
            nome_limpo = extrair_nome_limpo_panvel(texto_card)

            if not texto_parece_produto_panvel_exato(nome_limpo, href, produto):
                continue

            texto_para_score = f"{nome_limpo} {href}"
            score, motivos = score_texto_produto(produto, texto_para_score, href)

            precos_card = extrair_precos(texto_card)
            preco_card = escolher_preco_promocional_por_produto(precos_card, produto)

            item = {
                "indice": i,
                "href": href,
                "texto_link": texto_link,
                "texto_card": texto_card,
                "nome_limpo": nome_limpo,
                "precos_card": precos_card,
                "preco_card": preco_card,
                "score": score,
                "motivos": motivos
            }

            vistos.add(href)
            candidatos.append(item)

        except Exception:
            continue

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    return candidatos


def extrair_nome_pdp_panvel(page, produto):
    seletores_nome = [
        "h1",
        '[class*="product-name"]',
        '[class*="produto-nome"]',
        '[class*="productName"]',
        '[class*="title"]'
    ]

    for seletor in seletores_nome:
        try:
            elementos = page.locator(seletor)
            qtd = min(elementos.count(), 5)

            for i in range(qtd):
                try:
                    texto = elementos.nth(i).inner_text(timeout=1200).strip()
                    if texto and len(texto) > 8 and "R$" not in texto:
                        return texto
                except Exception:
                    pass
        except Exception:
            pass

    try:
        titulo = page.title().strip()
        if titulo:
            return titulo
    except Exception:
        pass

    return produto.get("produto_busca", "")


def extrair_preco_pdp_panvel(page, produto):
    try:
        page.wait_for_timeout(2500)
    except Exception:
        pass

    nome_h1 = ""
    h1 = None

    try:
        h1 = page.locator("h1").first
        nome_h1 = h1.inner_text(timeout=2000).strip()
    except Exception:
        pass

    print(f"[PANVEL][PDP FIX] Nome H1: {nome_h1}")

    containers = []

    if h1 is not None:
        xpaths_ancora = [
            "xpath=ancestor::div[1]",
            "xpath=ancestor::div[2]",
            "xpath=ancestor::div[3]",
            "xpath=ancestor::section[1]",
            "xpath=ancestor::section[2]",
            "xpath=ancestor::main[1]"
        ]

        for xp in xpaths_ancora:
            try:
                loc = h1.locator(xp)
                if loc.count() > 0:
                    containers.append((f"h1->{xp}", loc.first))
            except Exception:
                pass

    seletores_produto = [
        '[class*="product-detail"]',
        '[class*="productDetail"]',
        '[class*="product-info"]',
        '[class*="productInfo"]',
        '[class*="product"]',
        '[class*="produto"]',
        '[class*="details"]',
        "main"
    ]

    for sel in seletores_produto:
        try:
            loc = page.locator(sel)
            qtd = min(loc.count(), 4)
            for i in range(qtd):
                try:
                    containers.append((f"selector:{sel}[{i}]", loc.nth(i)))
                except Exception:
                    pass
        except Exception:
            pass

    vistos_texto = set()

    for origem, container in containers:
        try:
            texto = container.inner_text(timeout=3000).strip()
            if not texto:
                continue

            texto_norm = normalizar_texto(texto)
            if texto_norm in vistos_texto:
                continue
            vistos_texto.add(texto_norm)

            score_container, motivos_container = score_texto_produto(produto, texto, page.url)

            precos = extrair_precos(texto)
            preco = escolher_preco_panvel_pdp_por_produto(precos, produto)

            print(
                f"[PANVEL][PDP FIX] origem={origem} | score={score_container} | "
                f"motivos={motivos_container} | precos={precos} | escolhido={preco}"
            )

            if score_container < 10:
                continue

            if "volume_nao_bate" in motivos_container:
                continue

            if "concentracao_nao_bate" in motivos_container:
                continue

            if preco != "NAO_ENCONTRADO":
                return preco

        except Exception:
            continue

    try:
        main = page.locator("main")
        if main.count() > 0:
            texto = main.first.inner_text(timeout=3000)
            precos = extrair_precos(texto)
            preco = escolher_preco_panvel_pdp_por_produto(precos, produto)

            print(f"[PANVEL][PDP FIX] fallback main | precos={precos} | escolhido={preco}")

            if preco != "NAO_ENCONTRADO":
                return preco
    except Exception:
        pass

    return "NAO_ENCONTRADO"


def buscar_panvel(page, produto, rede_info):
    rede = rede_info["nome"]
    url_busca = construir_url_busca_panvel(produto)

    print(f"[{rede}] Tentando busca Panvel...")
    print(f"[{rede}] Busca base usada: canabidiol")
    print(f"[{rede}] URL: {url_busca}")

    page.goto("https://www.panvel.com", wait_until="domcontentloaded", timeout=60000)
    esperar_humano(page, 1800, 2800)

    page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
    esperar_humano(page, 3500, 5000)
    rolar_humano(page)

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    print(f"[{rede}] Título da página: {page.title()}")
    print(f"[{rede}] URL final após busca: {page.url}")

    candidatos = extrair_candidatos_panvel(page, produto)

    print(f"[{rede}] Candidatos válidos encontrados: {len(candidatos)}")
    for item in candidatos[:10]:
        print(
            f"[{rede}] Candidato {item['indice']}: {item['href']} | "
            f"nome={item['nome_limpo']} | score={item['score']} | "
            f"motivos={item['motivos']} | precos_card={item['precos_card']} | preco_card={item['preco_card']}"
        )

    if not candidatos:
        print(f"[{rede}] Nenhum candidato válido encontrado.")
        return "", "NAO_ENCONTRADO", page.url

    candidatos_validos = []

    for item in candidatos[:12]:
        if item["score"] < 10:
            continue

        if "volume_nao_bate" in item["motivos"]:
            continue

        if "concentracao_nao_bate" in item["motivos"]:
            continue

        candidatos_validos.append(item)

    print(f"[{rede}] Top candidatos que irão para validação na PDP:")
    for idx, item in enumerate(candidatos_validos[:5]):
        print(
            f"    índice={idx} | score={item['score']} | "
            f"nome={item['nome_limpo']} | motivos={item['motivos']} | url={item['href']}"
        )

    if not candidatos_validos:
        print(f"[{rede}] Nenhum candidato válido encontrado após scoring.")
        return "", "NAO_ENCONTRADO", page.url

    for idx, item in enumerate(candidatos_validos[:5], start=1):
        url_produto = item["href"]

        print(f"[{rede}] Abrindo PDP {idx}/{min(len(candidatos_validos), 5)}: {url_produto}")

        try:
            page.goto(url_produto, wait_until="domcontentloaded", timeout=60000)
            esperar_humano(page, 2500, 4200)

            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            rolar_humano(page)

            nome_pdp = extrair_nome_pdp_panvel(page, produto)
            score_pdp, motivos_pdp = score_texto_produto(produto, nome_pdp, page.url)

            print(f"[{rede}] Nome na PDP: {nome_pdp}")
            print(f"[{rede}] Score na PDP: {score_pdp} | motivos: {motivos_pdp}")

            if "volume_nao_bate" in motivos_pdp:
                print(f"[{rede}] PDP descartada por volume incompatível.")
                continue

            if "concentracao_nao_bate" in motivos_pdp:
                print(f"[{rede}] PDP descartada por concentração incompatível.")
                continue

            preco_pdp = extrair_preco_pdp_panvel(page, produto)
            print(f"[{rede}] Preço extraído da PDP: {preco_pdp}")

            if preco_pdp == "NAO_ENCONTRADO":
                continue

            nome_final = nome_pdp if nome_pdp else (item["nome_limpo"] if item["nome_limpo"] else produto["produto_busca"])

            print(f"[{rede}] Produto final escolhido: {nome_final}")
            print(f"[{rede}] URL final: {page.url}")
            print(f"[{rede}] Preço final escolhido: {preco_pdp}")

            return nome_final, preco_pdp, page.url

        except Exception as e:
            print(f"[{rede}] Erro ao abrir/ler PDP: {e}")
            continue

    print(f"[{rede}] Nenhum preço válido encontrado na PDP.")
    return "", "NAO_ENCONTRADO", page.url


# -----------------------------
# despacho por rede
# -----------------------------
def buscar_preco_por_rede(page, produto, rede_info):
    nome_rede = rede_info["nome"]

    if nome_rede in ["Drogasil", "DrogaRaia", "Raia"]:
        return buscar_rd(page, produto, rede_info)

    if nome_rede == "DrogariaSaoPaulo":
        return buscar_dpsp(page, produto, rede_info)

    if nome_rede == "PagueMenos":
        return buscar_paguemenos(page, produto, rede_info)

    if nome_rede == "Panvel":
        return buscar_panvel(page, produto, rede_info)

    if nome_rede == "DrogariaPacheco":
        print(f"[{nome_rede}] Temporariamente pausada por bloqueio/ERR_CONNECTION_RESET.")
        return "", "NAO_ENCONTRADO", ""

    print(f"[{nome_rede}] Rede cadastrada, mas ainda não implementada.")
    return "", "NAO_ENCONTRADO", ""


# -----------------------------
# gestão segura de page
# -----------------------------
def garantir_page_ativa(context, page=None):
    try:
        if page is not None and not page.is_closed():
            return page
    except Exception:
        pass

    nova_page = context.new_page()
    aplicar_stealth_basico(nova_page)
    return nova_page


def fechar_page_se_aberta(page):
    try:
        if page is not None and not page.is_closed():
            page.close()
    except Exception:
        pass


# -----------------------------
# motor principal
# -----------------------------
def run():
    browser = None
    context = None
    page = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )

            context = browser.new_context(
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/133.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 900},
                color_scheme="light",
                extra_http_headers={
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Upgrade-Insecure-Requests": "1",
                    "DNT": "1"
                }
            )

            print("=" * 80)
            print("INICIANDO CICLO DE COLETA")
            print("=" * 80)

            for i, rede in enumerate(redes, start=1):
                print(f"\n>>> Rede {i}/{len(redes)}: {rede['nome']}")

                page = garantir_page_ativa(context, None)

                try:
                    for j, produto in enumerate(produtos, start=1):
                        print(f"   -> Produto {j}/{len(produtos)}: {produto['produto_busca']}")

                        try:
                            page = garantir_page_ativa(context, page)
                            esperar_humano(page, 900, 1700)

                            nome_encontrado, preco_promocional, url_final = buscar_preco_por_rede(
                                page=page,
                                produto=produto,
                                rede_info=rede
                            )

                            if preco_promocional == "NAO_ENCONTRADO":
                                print(f"[{rede['nome']}] Preço não encontrado para este SKU.")
                                continue

                            registro = {
                                "data_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "grupo_comparacao": produto.get("grupo_comparacao", ""),
                                "rede": rede["nome"],
                                "empresa": produto.get("empresa", ""),
                                "marca": produto.get("marca", ""),
                                "ean": produto.get("ean", ""),
                                "produto": nome_encontrado if nome_encontrado else produto.get("produto_busca", ""),
                                "volume_ml": produto.get("volume_ml", ""),
                                "concentracao_mg_ml": produto.get("concentracao_mg_ml", ""),
                                "total_mg": produto.get("total_mg", ""),
                                "tipo_produto": produto.get("tipo_produto", ""),
                                "preco_principal": "",
                                "preco_promocional": preco_promocional,
                                "url": url_final
                            }

                            salvar_csv(registro)
                            print(f"[{rede['nome']}] Registro salvo no CSV")

                        except Exception as e:
                            print(f"[{rede['nome']}] Erro neste produto: {e}")

                finally:
                    fechar_page_se_aberta(page)
                    page = None

            print("\nCICLO FINALIZADO")
            print("=" * 80)

    finally:
        fechar_page_se_aberta(page)

        try:
            if context is not None:
                context.close()
        except Exception:
            pass

        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    run()