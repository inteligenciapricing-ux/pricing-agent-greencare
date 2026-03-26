import os
import re
import json
import unicodedata
from urllib.parse import quote
from playwright.sync_api import sync_playwright


# =============================
# CONFIGURAÇÕES
# =============================
URL_BASE = "https://www.panvel.com"
BUSCA_TESTE = "canabidiol 23,75mg/ml 10ml"
PASTA_OUTPUT = "outputs"


# =============================
# UTILITÁRIOS
# =============================
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
    texto = re.sub(r"\s+", " ", texto)
    return texto


def garantir_pasta_output():
    os.makedirs(PASTA_OUTPUT, exist_ok=True)


def href_parece_produto_panvel(href):
    if not href:
        return False

    href_lower = href.lower()

    if "/busca" in href_lower:
        return False

    if "/search" in href_lower:
        return False

    if "javascript:" in href_lower:
        return False

    if href_lower.endswith("#"):
        return False

    # heurística ampla para primeira fase
    if "/p-" in href_lower:
        return True

    if href_lower.endswith(".html"):
        return True

    if "/produto/" in href_lower:
        return True

    return False


def montar_url_busca(busca):
    # primeira tentativa
    return f"{URL_BASE}/busca?q={quote(busca)}"


# =============================
# DEBUG PANVEL
# =============================
def run():
    garantir_pasta_output()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox"
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
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
            }
        )

        page = context.new_page()

        try:
            print("=" * 80)
            print("TESTE PANVEL DEBUG")
            print("=" * 80)

            url_busca = montar_url_busca(BUSCA_TESTE)

            print(f"[PANVEL] Busca teste: {BUSCA_TESTE}")
            print(f"[PANVEL] URL inicial: {url_busca}")

            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            try:
                page.mouse.wheel(0, 900)
                page.wait_for_timeout(1200)
                page.mouse.wheel(0, -500)
                page.wait_for_timeout(1000)
            except Exception:
                pass

            print(f"[PANVEL] Título da página: {page.title()}")
            print(f"[PANVEL] URL final: {page.url}")

            html = page.content()
            caminho_html = os.path.join(PASTA_OUTPUT, "panvel_debug.html")
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(html)

            caminho_png = os.path.join(PASTA_OUTPUT, "panvel_debug.png")
            page.screenshot(path=caminho_png, full_page=True)

            print(f"[PANVEL] HTML salvo em: {caminho_html}")
            print(f"[PANVEL] Screenshot salvo em: {caminho_png}")

            anchors = page.locator("a")
            qtd_anchors = anchors.count()
            print(f"[PANVEL] Total de âncoras: {qtd_anchors}")

            candidatos = []
            vistos = set()
            limite = min(qtd_anchors, 400)

            for i in range(limite):
                try:
                    a = anchors.nth(i)
                    href = a.get_attribute("href")

                    if not href:
                        continue

                    if not href.startswith("http"):
                        href = URL_BASE.rstrip("/") + "/" + href.lstrip("/")

                    if href in vistos:
                        continue

                    if not href_parece_produto_panvel(href):
                        continue

                    texto = ""
                    try:
                        texto = a.inner_text(timeout=500).strip()
                    except Exception:
                        pass

                    texto_norm = normalizar_texto(texto)

                    candidatos.append({
                        "indice": i,
                        "href": href,
                        "texto": texto,
                        "texto_norm": texto_norm
                    })

                    vistos.add(href)

                except Exception:
                    continue

            print(f"[PANVEL] Candidatos de produto encontrados: {len(candidatos)}")

            for item in candidatos[:20]:
                print("-" * 80)
                print(f"índice: {item['indice']}")
                print(f"href: {item['href']}")
                print(f"texto: {item['texto']}")

            caminho_json = os.path.join(PASTA_OUTPUT, "panvel_candidatos.json")
            with open(caminho_json, "w", encoding="utf-8") as f:
                json.dump(candidatos[:50], f, ensure_ascii=False, indent=2)

            print(f"[PANVEL] JSON de candidatos salvo em: {caminho_json}")

            print("=" * 80)
            print("FIM TESTE PANVEL DEBUG")
            print("=" * 80)

        finally:
            try:
                page.close()
            except Exception:
                pass
            context.close()
            browser.close()


if __name__ == "__main__":
    run()