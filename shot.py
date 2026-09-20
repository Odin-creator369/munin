import asyncio, sys, os
from playwright.async_api import async_playwright
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
REP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1320,"height":1000}, device_scale_factor=2)
        for f in ["index.html","blind_eye.html","roster.html","gate.html","realms.html"]:
            await pg.goto("file://" + os.path.join(REP, f))
            await pg.wait_for_timeout(250)
            await pg.screenshot(path=os.path.join(OUT, f.replace(".html",".png")))
            print("shot", f)
        await b.close()
asyncio.run(main())
