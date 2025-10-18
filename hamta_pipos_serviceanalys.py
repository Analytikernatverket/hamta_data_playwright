import sys
import os
import asyncio
import subprocess

# sökväg + rscript.exe som skickas med från R som argument två
if len(sys.argv) > 2:
    r_sokvag_rscript_exe = sys.argv[2]
else:
    r_sokvag_rscript_exe = "Rscript"  # fallback om inget skickas in

# --- skapa funktion för att hämta användarnamn och lösenord från keyring-paketet i r
def get_r_keyring_credentials(service, username=None):
    """
    Hämta username + password från R:s keyring via subprocess.
    
    Parameters
    ----------
    service : str
        Namnet på keyring-service (t.ex. "pipos")
    username : str, optional
        Användarnamn. Om None -> tar första raden från key_list(service)
    
    Returns
    -------
    (username, password) : tuple of str
    """
    if username:
        r_cmd = f'''
        library(keyring)
        cat(key_get(service="{service}", username="{username}"))
        '''
        result = subprocess.run(
            [r_sokvag_rscript_exe, "-e", r_cmd],
            capture_output=True, text=True, check=True
        )
        password = result.stdout.strip()
        return username, password
    else:
        r_cmd = f'''
        library(keyring)
        users <- key_list(service="{service}")$username
        if (length(users) == 0) stop("Ingen användare hittades i keyring")
        user <- users[1]
        pw <- key_get(service="{service}", username=user)
        cat(paste(user, pw, sep=";"))
        '''
        result = subprocess.run(
            [r_sokvag_rscript_exe, "-e", r_cmd],
            capture_output=True, text=True, check=True
        )
        user, password = result.stdout.strip().split(";", 1)
        return user, password


# --- säkerställ att playwright finns ---
def ensure_package(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"📦 Installerar {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def ensure_playwright(browser="chromium"):
    """
    Säkerställ att Playwright och angiven webbläsare är installerade.
    
    Parameters
    ----------
    browser : str
        "chromium", "firefox" eller "webkit"
    """
    # Se till att playwright finns
    ensure_package("playwright")

    # Installera webbläsare om de inte redan finns
    subprocess.check_call([sys.executable, "-m", "playwright", "install", browser])

ensure_playwright("chromium")
ensure_package("pandas")

from playwright.async_api import async_playwright

async def main():
    # --- ta emot tmpdir från R ---
    tmpdir = sys.argv[1]
    os.makedirs(tmpdir, exist_ok=True)
    
    anv, pwd = get_r_keyring_credentials("pipos")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        pipos_url = "https://serviceanalys.tillvaxtverket.se/sa2/start"

        await page.goto(pipos_url, wait_until="networkidle")

        # fyll i användarnamn och lösenord (sparas med keyring-paketet i R med service = "pipos"
        await page.fill("#username", anv)
        await page.fill("#password", pwd)
        await page.click("#kc-login")
        
        # Klicka på knappen Tabeller och statistik
        await page.wait_for_selector("text=Tabeller och statistik", state = "visible")
        await page.get_by_text("Tabeller och statistik").click()

        # Klicka på knappen Servicetabell
        await page.wait_for_selector("text=Servicetabell", state = "visible")
        await page.get_by_text("Servicetabell").click()

        # exportera till Excel och fånga nedladdningen
        await page.wait_for_selector("button:has-text('Ladda ner som Excel-fil')", state="visible")
        async with page.expect_download() as download_info:
            await page.click("button:has-text('Ladda ner som Excel-fil')")
        download = await download_info.value

        # spara filen i den temporära mapp tmpdir som skickats med som argument till skriptet
        sokvag_filnamn = os.path.join(tmpdir, download.suggested_filename)
        
        await download.save_as(sokvag_filnamn)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
