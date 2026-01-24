
#!/usr/bin/env python
import sys
import os
import re
import argparse
import asyncio
import subprocess

# --- säkerställ att playwright finns ---

def ensure_package(pkg: str):
    try:
        __import__(pkg)
    except ImportError:
        print(f"📦 Installerar {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_package("playwright")

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

TILLVAXTVERKET_URL = (
  "https://tillvaxtdata.tillvaxtverket.se/statistikportal#page=72b01aa0-1d4a-425c-8684-dbce0319b39e"
)

# ---------- Hjälpfunktioner ----------

def svenska_tecken_byt_ut(s: str) -> str:
    """
    Normalisera filnamn: å/ä/ö -> a/a/o, mellanslag -> _, ta bort konstiga tecken, till lowercase.
    """
    if not s:
        return ""
    mapping = str.maketrans({
        "å": "a", "ä": "a", "ö": "o",
        "Å": "A", "Ä": "A", "Ö": "O",
        " ": "_",
    })
    s = s.translate(mapping)
    s = re.sub(r"[^0-9A-Za-z_.\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()

async def find_frame_with(page, css: str):
    """
    Returnera första frame som matchar css-selektorn; annars main frame.
    """
    for fr in page.frames:
        try:
            if await fr.locator(css).count() > 0:
                return fr
        except Exception:
            pass
    return page.main_frame

async def wait_net_settle(page, dom: bool = True, network: bool = True):
    """
    Vänta på domcontentloaded och två networkidle-fönster för stabilitet.
    """
    if dom:
        await page.wait_for_load_state("domcontentloaded")
    if network:
        for _ in range(2):
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except PWTimeoutError:
                pass

# ---------- Exportlogik ----------

async def export_once(page, outdir: str):
    """
    Reproducerar ditt reticulate-flöde:
      - flik: Utveckling över tid
      - Län: dots -> Markera alla -> stäng
      - Sverige/Utland: öppna collapsed select -> välj 'Utland' -> stäng
      - Topp 10 kommuner: öppna -> 'Alla' -> stäng
      - Hitta rätt 'Export Excel' med evaluate + regex
      - Ladda ner och spara fil
    """
    # 1) Till startsidan
    await page.goto(TILLVAXTVERKET_URL, wait_until="domcontentloaded")
    await wait_net_settle(page)

    # 2) Hitta frame där interaktionerna finns (eller fallback till main)
    fr = await find_frame_with(page, "text=Utveckling över tid")

    # 3) Välj fliken/panelen “Utveckling över tid”
    await fr.get_by_text("Utveckling över tid", exact=True).click()

    # 4) Län: öppna → dots → "Markera alla" → stäng
    
    
    # 1) Öppna Län-dropdown (scopat till rätt container)
    await fr.locator("[aria-owns='dip_qv_pulldown_Ln']").click()
    ln_container = fr.locator("#dip_qv_pulldown_Ln")
    await ln_container.wait_for(state="visible", timeout=6000)
    await ln_container.scroll_into_view_if_needed()
    
    # 2) Öppna markeringsmenyn via knappen inne i Län-sektionen
    sel_opts_btn = ln_container.locator("[aria-label='selection options']")
    if await sel_opts_btn.count() == 0:
        # fallback: använd ikon-bilden, men kräv synlighet och scopa till containern
        sel_opts_btn = ln_container.locator("img[src$='dots.png']:visible")
    await sel_opts_btn.first.click()
    
    # 3) DEFINIERA MENY-LOCATORN ALLTID (innan du försöker klicka i den)
    menu = fr.locator("[role='menu'], [role='listbox'], .menu, .ui-menu, .dropdown-menu").first
    await menu.wait_for(state="visible", timeout=4000)
    
    # 4) Klicka "Markera alla" – prova ARIA-roll först, fall back till text
    await menu.locator("text=Markera alla").first.click()

    # 5) Stäng Län-rutan om det finns en stäng-knapp
    close_btn = ln_container.locator("[aria-label='close']")
    if await close_btn.count() > 0:
        await close_btn.click()
    
    # 6) Stabilisering (valfritt men brukar hjälpa)
    try:
        await fr.page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        pass

    # 5) Sverige/Utland: öppna "collapsed" kontroll och välj 'Utland' -> stäng
    # Klicka print-spanen bredvid selecten:
    # CSS: #quickview_SverigeUtland + span.dip_collapsed_selector_print
    await fr.click('[aria-owns="dip_qv_pulldown_SverigeUtland"]')
    await fr.wait_for_selector("#dip_qv_pulldown_SverigeUtland", state="visible", timeout=6000)
    await fr.locator('#dip_qv_pulldown_SverigeUtland td:has-text("Utland")').first.click()
    await fr.locator('#dip_qv_pulldown_SverigeUtland [aria-label="close"]').click()
    await wait_net_settle(page)

    
    # 6) Topp 10 kommuner: öppna -> "Alla" -> (stäng om close finns)
    await fr.locator("[aria-owns='dip_qv_pulldown_Toppantallnkommuner']").click()
    try:
        # Försök varianten där pulldown-containern är synlig
        await fr.wait_for_selector("#dip_qv_pulldown_Toppantallnkommuner", state="visible", timeout=6000)
        await fr.locator('#dip_qv_pulldown_Toppantallnkommuner td:has-text("Alla")').first.click()
    
        # stäng om det finns en close-knapp (denna try/except är NESTAD och hör till samma gren)
        try:
            await fr.locator('#dip_qv_pulldown_Toppantallnkommuner [aria-label="close"]').click()
        except Exception:
            pass
    
    except PWTimeoutError:
        # Fallback om komponenten använder picklist-container istället
        await fr.wait_for_selector("[id^='dip_qv_picklist_Toppantallnkommuner']", state="visible", timeout=6000)
        await fr.locator("[id^='dip_qv_picklist_Toppantallnkommuner'] td:has-text('Alla')").first.click()
    
    await wait_net_settle(page)

    await asyncio.sleep(6)   # väntar 6 sekunder

    # 7) Hitta rätt "Export Excel" via evaluate, matcha rubrik (Skåne|Stockholm|Västra Götaland)
    all_excel_with_context = await fr.evaluate("""
      () => {
        const links = document.querySelectorAll('a.dvp_clickaction_link_text');
        return Array.from(links)
          .filter(link => (link.textContent || '').includes('Excel'))
          .map((link, index) => {
            const parent = link.closest('.dvp_chart_link_div') || link.closest('table') || link.closest('div');
            let title = '';
            const prev = parent?.previousElementSibling;
            if (prev) { title = (prev.textContent || '').trim().slice(0, 100); }
            const heading = parent?.querySelector('h1, h2, h3, h4, .dvp_chart_title, [aria-label]');
            if (heading) { title = (heading.textContent || '').trim() || heading.getAttribute('aria-label'); }
            const ariaLabel = parent?.getAttribute('aria-label');
            return {
              index,
              parent_id: parent?.id || null,
              title: title || null,
              aria_label: ariaLabel || null,
              parent_class: parent?.className || null
            };
          });
      }
    """)

    pattern = re.compile(r"(Skåne|Stockholm|Västra Götaland)", re.I)
    matches = [d["index"] for d in all_excel_with_context if pattern.search(d.get("title") or "")]
    excel_idx = matches[0] if matches else 0
    
    # 8) Klicka export och spara
    excel_links = fr.locator("a.dvp_clickaction_link_text", has_text="Excel")
    count = await excel_links.count()
    if count == 0:
      print("⚠️  Hittar ingen 'Export Excel' – avbryter.")
      print([d.get("title") for d in all_excel_with_context])
      return None
    
    i = excel_idx if excel_idx < count else 0
    
    link = excel_links.nth(i)
    await link.scroll_into_view_if_needed()
    await link.wait_for(state="visible", timeout=4000)

    async with page.expect_download() as dl_info:
      await excel_links.nth(i).click()
    download = await dl_info.value

    raw_name = f"Utlandska {download.suggested_filename}"
    raw_name = raw_name.replace(",", "")
    filnamn = svenska_tecken_byt_ut(raw_name)
    save_path = os.path.join(outdir, filnamn)
    await download.save_as(save_path)
    print(f"✅ Sparad: {save_path}")
    
    return save_path

# ---------- CLI / main ----------

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="scb_tmp", help="Mapp att spara nedladdade filer i")
    ap.add_argument("--headless", action="store_true", help="Kör utan UI")
    return ap.parse_args()

async def run():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            _ = await export_once(page, args.outdir)
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
