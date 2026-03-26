from playwright.sync_api import sync_playwright
import re
from datetime import datetime

URL = "https://www.drogasil.com.br/canabidiol-mantecorp-23-75mg-gotas-10ml.html"


def limpar_preco(texto):
    if not texto:
        return None

    match = re.search(r"R\$\s*([0-9\.\,]+)", texto)
    if not match:
        return None

    preco_str = match.group(1).replace(".", "").replace(",", ".")

    try:
        return float(preco_str)
    except ValueError:
        return None


def extrair_preco_da_pagina(page):
    seletores = [
        "text=/R\\$\\s*[0-9\\.,]+/",
        "[data-testid='price-current']",
        "[class*='price']",
        "[class*='Price']",
        "span:has-text('R$')",
        "div:has-text('R$')"
    ]

    for seletor in seletores:
        try:
            elementos = page.locator(seletor).all()
            for el in elementos:
                try:
                    texto = el.inner_text(timeout=2000).strip()
                    preco = limpar_preco(texto)
                    if preco is not None:
                        return preco, seletor, texto
                except:
                    pass
        except:
            pass

    html = page.content()

    padroes = [
        r'R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})',
        r'"price"\s*:\s*"([0-9\.,]+)"',
        r'"price"\s*:\s*([0-9\.,]+)',
        r'"finalPrice"\s*:\s*"([0-9\.,]+)"',
        r'"finalPrice"\s*:\s*([0-9\.,]+)'
    ]

    for padrao in padroes:
        match = re.search(padrao, html, flags=re.IGNORECASE)
        if match:
            valor = match.group(1)
            if not valor.startswith("R$"):
                valor = f"R$ {valor}"
            preco = limpar_preco(valor)
            if preco is not None:
                return preco, f"HTML regex: {padrao}", valor

    return None, None, None


def extrair_nome_da_pagina(page):
    candidatos = [
        "h1",
        "title"
    ]

    for seletor in candidatos:
        try:
            if seletor == "title":
                titulo = page.title()
                if titulo:
                    return titulo.replace(" | Drogasil", "").strip()
            else:
                el = page.locator(seletor).first
                if el:
                    texto = el.inner_text(timeout=2000).strip()
                    if texto:
                        return texto
        except:
            pass

    return None


def testar_html_drogasil():
    print("\n" + "=" * 80)
    print("TESTE HTML DROGASIL COM PLAYWRIGHT")
    print("=" * 80)
    print(f"URL: {URL}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )

        context = browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900}
        )

        page = context.new_page()

        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)

            page.wait_for_timeout(5000)

            print("=" * 80)
            print("STATUS")
            print("=" * 80)
            print(response.status if response else "Sem response")
            print()

            titulo = page.title()

            print("=" * 80)
            print("TITLE")
            print("=" * 80)
            print(titulo)
            print()

            nome = extrair_nome_da_pagina(page)
            preco, origem, texto_bruto = extrair_preco_da_pagina(page)

            print("=" * 80)
            print("RESULTADO")
            print("=" * 80)
            print(f"Produto: {nome}")
            print(f"Preço: {preco}")
            print(f"Origem do preço: {origem}")
            print(f"Texto bruto do preço: {texto_bruto}")
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            page.screenshot(path="outputs_teste_drogasil.png", full_page=True)

            print("=" * 80)
            print("SCREENSHOT")
            print("=" * 80)
            print("Arquivo salvo: outputs_teste_drogasil.png")
            print()

            if preco is None:
                print("=" * 80)
                print("ATENÇÃO")
                print("=" * 80)
                print("A página abriu, mas o preço não foi encontrado automaticamente.")
                print("Me mande o print do navegador aberto e o terminal.")
            else:
                print("=" * 80)
                print("SUCESSO")
                print("=" * 80)
                print("Captura de preço funcionando com navegador real.")

            input("\nPressione ENTER para fechar o navegador...")

        except Exception as e:
            print("=" * 80)
            print("ERRO")
            print("=" * 80)
            print(str(e))
            input("\nPressione ENTER para fechar o navegador...")

        finally:
            browser.close()


if __name__ == "__main__":
    testar_html_drogasil()