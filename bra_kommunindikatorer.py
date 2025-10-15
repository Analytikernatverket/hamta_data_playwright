import sys
import subprocess

def ensure_package(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"📦 Installerar {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_package("playwright")
ensure_package("requests")

import requests
from playwright.async_api import async_playwright
from urllib.parse import quote
import os
import asyncio

async def run(download_dir, kommuner):
  os.makedirs(download_dir, exist_ok=True)

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(accept_downloads=True)
    page = await context.new_page()

    await page.goto("https://bra.se/statistik/indikatorer-for-kommuners-lagesbild", wait_until="networkidle")

    for kommun in kommuner:
     
        # fyll i sökfältet
        await page.fill("input[name='query'][placeholder='Ange sökord']", kommun)
        await page.keyboard.press("Enter")
        
        # vänta på att länken till Excel-filen dyker upp
        encoded = quote(kommun)
        await page.wait_for_selector(f"a[href$='{encoded}.xlsx']")
        
        href = await page.get_attribute(f"a[href$='{encoded}.xlsx']", "href")
        
        full_url = f"https://bra.se{href}"
        print(full_url)
        resp = requests.get(full_url)
        print(f"Sparar till: {os.path.abspath(os.path.join(download_dir, kommun + '.xlsx'))}")

        with open(os.path.abspath(os.path.join(download_dir, f"{kommun}.xlsx")), "wb") as f:
            f.write(resp.content)
        print(f"✅ Klart: {kommun}")

        # ladda ner filen
        # async with page.expect_download() as download_info:
        #   await page.click(f"a[href='{href}']")
        # download = await download_info.value
        # 
        # filnamn = download.suggested_filename
        # print(filnamn)
        # path = os.path.join(download_dir, filnamn)
        # print(path)
        # await download.save_as(path)

    await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Användning: python ladda_ner_kommuner.py <mapp> <kommun1> <kommun2> ...")
        sys.exit(1)

    download_dir = sys.argv[1]
    kommuner = sys.argv[2:]
    asyncio.run(run(download_dir, kommuner))
