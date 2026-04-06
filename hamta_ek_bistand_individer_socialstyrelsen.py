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

async def main():
    # --- ta emot tmpdir från R ---
    tmpdir = sys.argv[1] if len(sys.argv) > 1 else "scb_tmp"
    os.makedirs(tmpdir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        # context = await browser.new_context(accept_downloads=True)
        # page = await context.new_page()
        socialstyrelsen_db_url = "https://sdb.socialstyrelsen.se/if_ekb_manad/val.aspx"

        # loopa för att göra ett uttag för inrikes och ett för utrikes födda
        
        for value, suffix in [("0", "inrikes"), ("1", "utrikes")]:
            
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            await page.goto(socialstyrelsen_db_url, wait_until="networkidle")
    
            # klicka kryssrutor
            await page.wait_for_selector("text=Dalarnas län", state="visible")
            #await page.click("text=Dalarnas län")
            await page.click("text=Alla kommuner")
            await page.click("text=Alla län")
    
            # Välj tabell - dvs. individer
            await page.wait_for_selector("#ph1_val_tabell_pRad3", state="visible")
            await page.click("text=Biståndsmottagare")
            
            # välj alla år 
            await page.wait_for_selector("#ph1_val_ar_hlAdd", state="visible")
            await page.click("#ph1_val_ar_hlAdd")
            
            #await page.wait_for_selector("#AR", state="visible")
            
            # # Hämta alla values från listan
            # all_values = await page.eval_on_selector(
            #     "#AR",
            #     "sel => Array.from(sel.options).map(o => o.value)"
            # )
            # 
            # # Filtrera bort 2014–2016
            # excluded = {"2014", "2015", "2016"}
            # to_select = [v for v in all_values if v not in excluded]
            # 
            # # Sätt exakt urval (ersätter ev. befintlig selektion)
            # await page.select_option("#AR", to_select)
            # 
            # # Trigga onchange-handlaren om sidan väntar på den (din DOM visar onchange='antal_Ar()')
            # await page.dispatch_event("#AR", "change")
    
    
            # välj alla månader
            await page.wait_for_selector("#ph1_val_manad_hlAdd", state="visible")
            await page.click("#ph1_val_manad_hlAdd")
            
            # # välj sökande eller medsökande av ekonmiskt bistånd
            # await page.wait_for_selector("#ph1_Val_PERSORDNGRP_pRad3", state="visible")
            # await page.click("value=1")
    
            # välj inrikes och utrikes född
            await page.wait_for_selector("#UTRIKES_BIST", state="visible")
            await page.select_option("#UTRIKES_BIST", value)
            await page.dispatch_event("#UTRIKES_BIST", "change")
            
            # visa resultat
            # await page.wait_for_selector("#ph1_val_data_lnkVisaResultat", state="visible")
            # await page.click("#ph1_val_data_lnkVisaResultat")
            await page.wait_for_selector("#ph1_val_data_lnkVisaResultat", state="visible")
            async with page.expect_navigation(wait_until="networkidle"):
                await page.click("#ph1_val_data_lnkVisaResultat")
    
            # välj "År" i kolumner och flytta till rader
            await page.select_option("#ph1_ListBoxKolumner", value="AR")
            await page.click("#ph1_ButtonKolumnerTillRader")
            
            # exportera till Excel och fånga nedladdningen
            await page.wait_for_selector("#ph1_lbXLS", state="visible")
            async with page.expect_download() as download_info:
                await page.click("#ph1_lbXLS")
            download = await download_info.value
    
            # spara i tmpdir
            #filnamn = os.path.join(tmpdir, download.suggested_filename)
            filnamn = os.path.join(tmpdir, download.suggested_filename.replace(".xlsx", f"_{suffix}.xlsx"))
            await download.save_as(filnamn)
            await page.wait_for_timeout(500)  # liten paus för att undvika race conditions
            # print(f"✅ Fil sparad: {filnamn}")
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
