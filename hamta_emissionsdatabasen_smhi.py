import sys
import asyncio
from playwright.async_api import async_playwright

async def run(download_dir):
  async with async_playwright() as p:
      browser = await p.chromium.launch(headless=False)
      context = await browser.new_context(accept_downloads=True)
      page = await context.new_page()

      await page.goto("https://nationellaemissionsdatabasen.smhi.se/")

      # vänta på nedladdning
      async with page.expect_download() as download_info:
        await page.click("button:has-text('Excel')")
      download = await download_info.value

      # spara filen i angiven mapp
      path = f"{download_dir}/{download.suggested_filename}"
      await download.save_as(path)
      
      await browser.close()

if __name__ == "__main__":
  download_dir = sys.argv[1]
asyncio.run(run(download_dir))
