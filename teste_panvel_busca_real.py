import os
from playwright.sync_api import sync_playwright

BUSCA = "canabidiol"
PASTA_OUTPUT = "outputs"


def run():
    os.makedirs(PASTA_OUTPUT, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
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
            )
        )

        page = context.new_page()

        try:
            print("Abrindo Panvel...")
            page.goto("https://www.panvel.com", timeout=60000)

            page.wait_for_timeout(4000)

            print("Tentando localizar campo de busca...")

            # tenta vários seletores possíveis
            possiveis_inputs = [
                "input[type='search']",
                "input[name='q']",
                "input[placeholder*='Buscar']",
                "input"
            ]

            input_encontrado = None

            for seletor in possiveis_inputs:
                try:
                    campo = page.locator(seletor).first
                    campo.wait_for(timeout=3000)

                    if campo.is_visible():
                        input_encontrado = campo
                        print(f"Campo encontrado com seletor: {seletor}")
                        break
                except:
                    continue

            if not input_encontrado:
                print("❌ Campo de busca NÃO encontrado")
                return

            # digitar busca
            input_encontrado.click()
            input_encontrado.fill(BUSCA)

            page.wait_for_timeout(1000)

            # pressionar enter
            input_encontrado.press("Enter")

            print("Buscando...")

            page.wait_for_timeout(5000)

            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            print("URL final:", page.url)
            print("Título:", page.title())

            # salvar debug
            html_path = os.path.join(PASTA_OUTPUT, "panvel_busca_real.html")
            page.screenshot(path=os.path.join(PASTA_OUTPUT, "panvel_busca_real.png"), full_page=True)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())

            print("HTML salvo em:", html_path)

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()