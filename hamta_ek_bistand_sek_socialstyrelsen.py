import sys
import os
import asyncio
import subprocess

# --- säkerställ att playwright finns ---
def ensure_package(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"📦 Installerar {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_package("playwright")

from playwright.async_api import async_playwright

soc_url = "https://sdb.socialstyrelsen.se/if_ekb_manad/val.aspx"

async def export_one(page, tmpdir, i):

    # Gå till startsidan inför varje varv för att nollställa UI
    await page.goto(soc_url, wait_until="domcontentloaded")
    
    # --- urval (exempel enligt din kod) ---
    await page.wait_for_selector("text=Dalarnas län", state="visible")
    # await page.click("text=Dalarnas län")  # urval kommun/län: avaktiverat i ditt exempel
    await page.click("text=Alla kommuner")
    await page.click("text=Alla län")
    
    # Välj mått
    await page.wait_for_selector("#ph1_val_matt_pRad3", state="visible")
    await page.click("text=Utbetalt ekonomiskt bistånd tkr")
    
    # Välj alla år
    await page.wait_for_selector("#ph1_val_ar_hlAdd", state="visible")
    await page.click("#ph1_val_ar_hlAdd")
    
    # Välj alla månader
    await page.wait_for_selector("#ph1_val_manad_hlAdd", state="visible")
    await page.click("#ph1_val_manad_hlAdd")
    
    # Välj bakgrund i hushållet
    await page.wait_for_selector("#UTRIKES_HUSH", state="visible")
    await page.select_option("#UTRIKES_HUSH", str(i))
    #await page.click("value=1")
    
    # Visa resultat
    await page.wait_for_selector("#ph1_val_data_lnkVisaResultat", state="visible")
    await page.click("#ph1_val_data_lnkVisaResultat")
    
    # Flytta "År" från kolumner till rader
    await page.wait_for_selector("#ph1_ListBoxKolumner", state="visible")
    await page.select_option("#ph1_ListBoxKolumner", value="AR")
    await page.click("#ph1_ButtonKolumnerTillRader")
    
    # Exportera till Excel
    await page.wait_for_selector("#ph1_lbXLS", state="visible")
    async with page.expect_download() as download_info:
      await page.click("#ph1_lbXLS")
    download = await download_info.value
    
    # Spara i tmpdir
    filnamn = os.path.join(tmpdir, download.suggested_filename)
    await download.save_as(filnamn)
    
    #return filnamn

async def main():
    # ta emot tmpdir från R (eller default)
    tmpdir = sys.argv[1] if len(sys.argv) > 1 else "scb_tmp"
    os.makedirs(tmpdir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # Kör export två eller tre gånger (exempel 3)
        sparade = []
        for i in range(3):
          try:
            fil = await export_one(page, tmpdir, i)
            sparade.append(fil)
            # Här kan du lägga en liten paus om sajten är känslig för frekventa anrop:
            # await page.wait_for_timeout(500)  # 0,5 sek
          except Exception as e:
            print(f"Fel i varv {i+1}: {e}")

        await browser.close()

        # Rapportera resultat
        # for f in sparade:
        #   print(f"✅ Fil sparad: {f}")

if __name__ == "__main__":
  import asyncio
  asyncio.run(main())




# 
# async def main():
#     # --- ta emot tmpdir från R ---
#     tmpdir = sys.argv[1] if len(sys.argv) > 1 else "scb_tmp"
#     os.makedirs(tmpdir, exist_ok=True)
# 
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         context = await browser.new_context(accept_downloads=True)
#         page = await context.new_page()
#         test_url = "https://sdb.socialstyrelsen.se/if_ekb_manad/val.aspx"
# 
#         await page.goto(test_url, wait_until="networkidle")
# 
#         # klicka kryssrutor
#         await page.wait_for_selector("text=Dalarnas län", state="visible")
#         #await page.click("text=Dalarnas län")
#         await page.click("text=Alla kommuner")
#         await page.click("text=Alla län")
# 
#         # Välj mått - dvs. Utbetalt ekonomiskt bistånd tkr
#         await page.wait_for_selector("#ph1_val_matt_pRad3", state="visible")
#         await page.click("text=Utbetalt ekonomiskt bistånd tkr")
#         
#         # välj alla år
#         await page.wait_for_selector("#ph1_val_ar_hlAdd", state="visible")
#         await page.click("#ph1_val_ar_hlAdd")
#         
#         # välj alla månader
#         await page.wait_for_selector("#ph1_val_manad_hlAdd", state="visible")
#         await page.click("#ph1_val_manad_hlAdd")
#         
#         # visa resultat
#         await page.wait_for_selector("#ph1_val_data_lnkVisaResultat", state="visible")
#         await page.click("#ph1_val_data_lnkVisaResultat")
# 
#         # välj "År" i kolumner och flytta till rader
#         await page.select_option("#ph1_ListBoxKolumner", value="AR")
#         await page.click("#ph1_ButtonKolumnerTillRader")
#         
#         # exportera till Excel och fånga nedladdningen
#         await page.wait_for_selector("#ph1_lbXLS", state="visible")
#         async with page.expect_download() as download_info:
#             await page.click("#ph1_lbXLS")
#         download = await download_info.value
# 
#         # spara i tmpdir
#         filnamn = os.path.join(tmpdir, download.suggested_filename)
#         await download.save_as(filnamn)
#         # print(f"✅ Fil sparad: {filnamn}")
# 
# 
# 
#         await browser.close()
# 
# if __name__ == "__main__":
#     asyncio.run(main())
