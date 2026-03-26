from playwright.sync_api import sync_playwright
from urllib.parse import quote

REDE = "DrogariaSaoPaulo"
URL_BASE = "https://www.drogariasaopaulo.com.br"
BUSCA = "Canabidiol 23,75mg/ml 10ml GreenCare"


def testar_dpsp():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

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
            url_busca = f"{URL_BASE}/pesquisa?q={quote(BUSCA)}"

            print("=" * 80)
            print(f"DEBUG DPSP - {REDE}")
            print("=" * 80)
            print(f"Busca: {BUSCA}")
            print(f"URL: {url_busca}")
            print()

            page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)

            print("=" * 80)
            print("TÍTULO")
            print("=" * 80)
            print(page.title())
            print()

            print("=" * 80)
            print("URL FINAL")
            print("=" * 80)
            print(page.url)
            print()

            seletores_teste = [
                '[data-testid="product-card"]',
                '[class*="product-card"]',
                '[class*="ProductCard"]',
                '[class*="product-grid-item"]',
                '[class*="productGridItem"]',
                '[class*="product-item"]',
                '[class*="productItem"]',
                '[class*="shelf-item"]',
                '[class*="shelfItem"]',
                'article',
                'li',
                'a[href*="/produto/"]',
                'a[href*=".html"]',
                '[class*="vtex-search-result"]',
                '[class*="galleryItem"]',
                '[class*="gallery-item"]'
            ]

            print("=" * 80)
            print("CONTAGEM DE SELETORES")
            print("=" * 80)

            for seletor in seletores_teste:
                try:
                    qtd = page.locator(seletor).count()
                    print(f"{seletor} -> {qtd}")
                except Exception as e:
                    print(f"{seletor} -> ERRO: {e}")

            print()

            html = page.content()

            with open("outputs/dpsp_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            page.screenshot(path="outputs/dpsp_debug.png", full_page=True)

            print("=" * 80)
            print("ARQUIVOS GERADOS")
            print("=" * 80)
            print("HTML: outputs/dpsp_debug.html")
            print("PNG : outputs/dpsp_debug.png")
            print()

            print("=" * 80)
            print("PRIMEIROS 3000 CARACTERES DO HTML")
            print("=" * 80)
            print(html[:3000])
            print()

            input("Pressione ENTER para fechar...")

        finally:
            browser.close()


if __name__ == "__main__":
    testar_dpsp()