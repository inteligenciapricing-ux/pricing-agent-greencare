from playwright.sync_api import sync_playwright
from urllib.parse import quote


URL_BASE = "https://www.drogariasaopaulo.com.br"
BUSCA = "Canabidiol 23,75mg/ml 10ml GreenCare"


def contar_seletor_js(page, seletor):
    script = """
    (sel) => {
        try {
            return document.querySelectorAll(sel).length;
        } catch (e) {
            return -1;
        }
    }
    """
    return page.evaluate(script, seletor)


def testar():
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
            url = f"{URL_BASE}/pesquisa?q={quote(BUSCA)}"

            print("=" * 80)
            print("TESTE DE SELETORES DPSP")
            print("=" * 80)
            print(f"BUSCA: {BUSCA}")
            print(f"URL: {url}")
            print()

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
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

            seletores = [
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
                'a[href*=".html"]',
                'a[href*="/produto"]',
                'a[href*="/medicamento"]',
                'img[alt*="Canabidiol"]',
                'img[alt*="GreenCare"]'
            ]

            print("=" * 80)
            print("CONTAGEM DE SELETORES")
            print("=" * 80)

            for seletor in seletores:
                qtd = contar_seletor_js(page, seletor)
                print(f"{seletor} -> {qtd}")

            print()

            print("=" * 80)
            print("PRIMEIROS LINKS .HTML ENCONTRADOS")
            print("=" * 80)

            links = page.locator('a[href*=".html"]')
            total_links = min(links.count(), 10)

            for i in range(total_links):
                try:
                    href = links.nth(i).get_attribute("href")
                    texto = links.nth(i).inner_text(timeout=1000).strip()
                    print(f"[{i}] href={href}")
                    print(f"    texto={texto[:200]}")
                except Exception as e:
                    print(f"[{i}] erro ao ler link: {e}")

            print()

            html = page.content()

            with open("outputs/dpsp_seletores_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            page.screenshot(path="outputs/dpsp_seletores_debug.png", full_page=True)

            print("=" * 80)
            print("ARQUIVOS GERADOS")
            print("=" * 80)
            print("HTML: outputs/dpsp_seletores_debug.html")
            print("PNG : outputs/dpsp_seletores_debug.png")
            print()

            input("Pressione ENTER para fechar...")

        finally:
            browser.close()


if __name__ == "__main__":
    testar()