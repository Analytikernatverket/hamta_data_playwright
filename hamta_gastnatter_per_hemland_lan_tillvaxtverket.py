
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
    Returnera första frame som innehåller css-selektorn; annars main frame.
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
    Liten stabiliserare: vänta på domcontentloaded och ett par networkidle-fönster.
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

async def export_all(page, outdir: str):
    """
    - Navigerar till sidan
    - Väljer fliken 'Utveckling över tid'
    - Väljer 'Alla' i Toppantalländer
    - Hämtar alla Län
    - Väljer varje Län och laddar ner 'Export Excel' för rätt panel
    """
    # 1) Till startsidan
    await page.goto(TILLVAXTVERKET_URL, wait_until="domcontentloaded")
    await wait_net_settle(page)

    # 2) Hitta frame där interaktionerna finns
    fr = await find_frame_with(page, "text=Utveckling över tid")

    # 3) Välj fliken/panelen “Utveckling över tid”
    await fr.get_by_text("Utveckling över tid", exact=True).click()

    # 4) Öppna “Toppantalländer” och klicka “Alla”
    topp_btn = fr.locator('[aria-owns="dip_qv_pulldown_Toppantallnder"]')
    await topp_btn.click()

    try:
        # a) variant där pulldown-containern blir synlig
        await fr.wait_for_selector("#dip_qv_pulldown_Toppantallnder", state="visible", timeout=5000)
        await fr.locator('#dip_qv_pulldown_Toppantallnder td:has-text("Alla")').first.click()
    except PWTimeoutError:
        # b) vanlig “picklist”-popup i dip_*-komponenter
        await fr.wait_for_selector("[id^='dip_qv_picklist_Toppantallnder']", state="visible", timeout=5000)
        await fr.locator("[id^='dip_qv_picklist_Toppantallnder'] td:has-text('Alla')").first.click()

    await wait_net_settle(page)

    # 5) Hämta alla län
    alla_lan = await fr.evaluate("""
      () => {
        const container = document.getElementById('dip_qv_pulldown_Ln');
        if (!container) return [];
        const items = container.querySelectorAll('.dip_quickview_item');
        return Array.from(items)
          .filter(item => item.id && item.id.startsWith('item_'))
          .map(item => item.textContent.trim());
      }
    """)
    if not alla_lan:
        print("⚠️  Hittade inga län i 'dip_qv_pulldown_Ln'. Avbryter.")
        return []

    # 6) Hitta rätt “Export Excel”-länk baserat på rubriktitel
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

    pat = re.compile(r"(Afghanistan|Albanien|Australien|Belgien)", re.I)
    match_indices = [d["index"] for d in all_excel_with_context if pat.search(d.get("title") or "")]
    excel_idx = match_indices[0] if match_indices else 0  # fallback

    # 7) Exportera för varje län
    saved = []
    for valt_lan in alla_lan:
        try:
            # Öppna Län-dropdown
            await fr.locator('[aria-owns="dip_qv_pulldown_Ln"]').click()
            await fr.wait_for_selector("#dip_qv_pulldown_Ln", state="visible", timeout=5000)

            # Välj län
            await fr.locator(f"#dip_qv_pulldown_Ln .dip_quickview_item:has-text('{valt_lan}')").first.click()

            # Stäng rutan
            await fr.locator('#dip_qv_pulldown_Ln [aria-label="close"]').click()

            await wait_net_settle(page)

            # Klicka rätt "Export Excel"
            excel_links = fr.locator("a.dvp_clickaction_link_text:has-text('Export Excel')")
            count = await excel_links.count()
            if count == 0:
                print(f"⚠️  Hittar ingen 'Export Excel' vid län '{valt_lan}' – hoppar över.")
                continue

            i = excel_idx if excel_idx < count else 0

            async with page.expect_download() as dl_info:
                await excel_links.nth(i).click()
            download = await dl_info.value

            raw_name = f"{valt_lan}_{download.suggested_filename}"
            filnamn = raw_name # svenska_tecken_byt_ut(raw_name)
            path = os.path.join(outdir, filnamn)
            await download.save_as(path)
            print(f"✅ Sparad: {path}")
            saved.append(path)
            
            # Öppna Län-dropdown
            await fr.locator("[aria-owns='dip_qv_pulldown_Ln']").click()
            
            # Klicka återställ-knappen (deselect all)
            await fr.click("[role='button'][aria-label='deselect all']")
            
            # Stäng rutan
            await fr.locator('#dip_qv_pulldown_Ln [aria-label="close"]').click()


        except Exception as e:
            print(f"❌ Fel vid län '{valt_lan}': {e}")

    return saved

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
            saved = await export_all(page, args.outdir)
        finally:
            await context.close()
            await browser.close()

    if saved:
        print("\n--- Sammanfattning ---")
        for f in saved:
            print(f"• {f}")

if __name__ == "__main__":
    asyncio.run(run())
