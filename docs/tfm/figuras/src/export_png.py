"""Exporta a PNG el SVG de cada diagrama de archify para insertarlo en el .docx.

Uso: python3 export_png.py <carpeta_html> <carpeta_png> nombre1 [nombre2 ...]

Abre <carpeta_html>/<nombre>.html en Chromium (Playwright) con tema claro, oculta los
controles del visor y la cuadrícula de fondo, traduce el título de la leyenda y guarda
<carpeta_png>/<nombre>.png recortando el margen en blanco. No modifica el HTML.
"""
import asyncio
import sys

from PIL import Image, ImageChops
from playwright.async_api import async_playwright

CSS = """
html, body { background: #ffffff !important; }
body * { visibility: hidden !important; }
svg[data-quality-profile], svg[data-quality-profile] * { visibility: visible !important; }
svg[data-quality-profile] rect[fill="url(#grid)"] { display: none !important; }
"""


def trim(path, pad=40):
    im = Image.open(path).convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255)))
    box = diff.point(lambda v: 255 if v > 8 else 0).getbbox()
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
    im.crop(box).save(path, optimize=True)


async def main(html_dir, png_dir, names):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name in names:
            ctx = await browser.new_context(viewport={"width": 1500, "height": 1100},
                                            device_scale_factor=2.5, color_scheme="light")
            await ctx.add_init_script("try{localStorage.setItem('archify-theme','light')}catch(e){}")
            page = await ctx.new_page()
            await page.goto(f"file://{html_dir}/{name}.html")
            await page.evaluate("document.documentElement.setAttribute('data-theme','light')")
            await page.add_style_tag(content=CSS)
            await page.evaluate("""() => { for (const t of document.querySelectorAll('svg[data-quality-profile] text'))
                                     if (t.textContent.trim() === 'Legend') t.textContent = 'Leyenda'; }""")
            await page.wait_for_timeout(300)
            out = f"{png_dir}/{name}.png"
            await page.locator("svg[data-quality-profile]").first.screenshot(path=out)
            await ctx.close()
            trim(out)
            print("PNG", out)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
