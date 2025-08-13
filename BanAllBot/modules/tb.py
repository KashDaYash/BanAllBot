import os
import re
import asyncio
import tempfile
import math
from typing import Optional, List
from urllib.parse import urlencode, urlparse, parse_qs
import base64
import time
import json
import sys

# Selenium Imports - NUEVO
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified

import httpx
from BanAllBot import app

# ---- Helpers (Sin cambios) --------------------------------------------------

TERABOX_RX = re.compile(r"https?://(?:www\.)?(?:terabox|1024terabox)\.com/s/\S+", re.I)

def pick_best_link(item: dict) -> Optional[str]:
    return item.get("dl_cdn") or item.get("fastdlink") or item.get("dlink") or item.get("fdlink")

def extract_dl_url(dl_cdn: str) -> str:
    """
    dl_cdn usually has ?data=<base64> → final .vdo URL.
    If not found, return as-is.
    """
    try:
        q = parse_qs(urlparse(dl_cdn).query)
        b64 = q.get("data", [None])[0]
        if not b64:
            return dl_cdn
        raw = base64.b64decode(b64).decode("utf-8", "ignore")
        return raw
    except Exception:
        return dl_cdn

def human(n: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(units)-1:
        f /= 1024.0
        i += 1
    return f"{f:.2f} {units[i]}"

async def edit_safe(msg: Message, text: str):
    try:
        await msg.edit_text(text)
    except MessageNotModified:
        pass

# ---- Selenium auto-install (manejado por webdriver-manager) --------
# La función ensure_playwright_chromium ya no es necesaria.
# webdriver-manager se encarga de descargar el driver correcto.

# ---- Core scraping & download (Reescrito con Selenium) ---------------------

def capture_api_json_selenium(share_url: str, wait_seconds: int = 20, headless: bool = True) -> List[dict]:
    """
    Abre teradownloader /download?l=... usando Selenium y captura el JSON
    devuelto por /api?data=... usando selenium-wire.
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
    
    # Argumentos comunes para ejecutar en servidores/contenedores
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    # Usar webdriver-manager para instalar y configurar el driver automáticamente
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    api_items = None
    
    try:
        q = urlencode({"l": share_url})
        driver.get(f"https://teradownloader.com/download?{q}")

        # El sitio muestra "Please wait 15-20 sec..."
        print(f"Waiting for {wait_seconds} seconds for the page to make API calls...")
        time.sleep(wait_seconds)

        # Buscar en las peticiones capturadas por selenium-wire
        for request in driver.requests:
            if request.response and request.url.startswith("https://teradownloader.com/api?data="):
                # Asegurarse de que la respuesta es JSON
                content_type = request.response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        # El cuerpo de la respuesta está en bytes, decodificar y cargar como JSON
                        body_decoded = request.response.body.decode('utf-8')
                        api_items = json.loads(body_decoded)
                        print("API JSON response captured successfully.")
                        break # Salir del bucle una vez encontrado
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"Failed to decode API response: {e}")
                        pass
    finally:
        # Asegurarse de que el navegador se cierre
        driver.quit()

    if not api_items:
        raise RuntimeError(
            "API JSON capture failed. Cloudflare/Turnstile or unsupported link.\n"
            "Tip: set HEADLESS=false to run non-headless locally and solve challenge once."
        )
    return api_items

# ---- Función de descarga (Sin cambios) --------------------------------------
async def download_with_progress(url: str, dest_path: str, progress_cb=None):
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or 0)
            downloaded = 0
            chunk = 1 << 20  # 1 MB
            with open(dest_path, "wb") as f:
                async for data in r.aiter_bytes(chunk_size=chunk):
                    if data:
                        f.write(data)
                        downloaded += len(data)
                        if progress_cb:
                            await progress_cb(downloaded, total)

# ---- Bot (Modificado para llamar a la función de Selenium) ------------------

@app.on_message(filters.command("download"))
async def handle_text(_, msg: Message):
    if not getattr(msg, "command", None) or len(msg.command) < 2:
        return await msg.reply_text("Usage: `/download <terabox_share_url>`", quote=True)

    possible_url = msg.command[1]
    m = TERABOX_RX.search(possible_url) or TERABOX_RX.search(msg.text or "")
    if not m:
        return await msg.reply_text("Please send a valid Terabox share URL.", quote=True)

    share_url = m.group(0)
    status = await msg.reply_text("⏳ Getting download info…", quote=True)

    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    wait_sec = int(os.environ.get("WAIT_SECONDS", "20"))

    try:
        # Ejecutar la función síncrona de Selenium en un hilo para no bloquear el bucle de eventos de asyncio
        items = await asyncio.to_thread(capture_api_json_selenium, share_url, wait_seconds=wait_sec, headless=headless)
        if not items:
            return await edit_safe(status, "❌ No items found in API response.")
        item = items[0]
    except Exception as e:
        # sys.exc_info() se puede usar para un traceback más detallado si es necesario
        return await edit_safe(status, f"❌ Failed to capture API JSON:\n`{e}`")

    best = pick_best_link(item)
    if not best:
        return await edit_safe(status, "❌ No downloadable link in API JSON.")
    final_url = extract_dl_url(best)

    filename = item.get("server_filename") or "download.bin"
    size_str = item.get("size")
    size_h = human(int(size_str)) if size_str and str(size_str).isdigit() else "unknown"
    await edit_safe(status, f"⬇️ Downloading **{filename}** ({size_h})…")

    MAX_BOT_SIZE = int(os.environ.get("MAX_BOT_SIZE_BYTES", str(2 * 1024 * 1024 * 1024)))

    tmpdir = tempfile.mkdtemp(prefix="tdl_")
    out_path = os.path.join(tmpdir, filename.replace("/", "_"))

    async def progress(downloaded, total):
        try:
            if total > 0:
                pct = downloaded * 100 // total
                if pct % 5 == 0:
                    await edit_safe(status, f"⬇️ Downloading **{filename}** — {pct}% ({human(downloaded)}/{human(total)})")
            else:
                if downloaded % (10 * (1 << 20)) == 0:
                    await edit_safe(status, f"⬇️ Downloading **{filename}** — {human(downloaded)}")
        except FloodWait as fw:
            await asyncio.sleep(fw.value)

    if size_str and str(size_str).isdigit():
        if int(size_str) > MAX_BOT_SIZE:
            return await edit_safe(status, f"⚠️ File is {size_h}, which likely exceeds bot send limit. Aborting.")

    try:
        await download_with_progress(final_url, out_path, progress_cb=progress)
    except httpx.HTTPError as he:
        return await edit_safe(status, f"❌ HTTP error while downloading:\n`{he}`\nLink may have expired. Try again.")
    except Exception as e:
        return await edit_safe(status, f"❌ Download failed:\n`{e}`")

    try:
        fsize = os.path.getsize(out_path)
        if fsize > MAX_BOT_SIZE:
            return await edit_safe(status, f"⚠️ Downloaded size {human(fsize)} exceeds bot limit. Not sending.")
    except Exception:
        pass

    await edit_safe(status, "📤 Uploading to Telegram…")

    caption = f"{filename}\nSize: {size_h}"
    try:
        await msg.reply_video(out_path, caption=caption, supports_streaming=True)
        await status.delete()
    except Exception:
        await msg.reply_document(out_path, caption=caption)
        await status.delete()

    # import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
 
