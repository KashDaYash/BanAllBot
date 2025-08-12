import os
import re
import asyncio
import tempfile
import math
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs
import base64

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified

import httpx
from playwright.async_api import async_playwright
from BanAllBot import app 
# ---- Helpers ----------------------------------------------------------------

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

# ---- Core scraping & download -----------------------------------------------

async def capture_api_json(share_url: str, wait_seconds: int = 20, headless: bool = True) -> list[dict]:
    """
    Open teradownloader /download?l=... and capture the JSON returned by /api?data=...
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        api_items = None

        async def on_response(res):
            nonlocal api_items
            url = res.url
            if url.startswith("https://teradownloader.com/api?data="):
                ct = (res.headers.get("content-type") or "").lower()
                if "application/json" in ct:
                    try:
                        api_items = await res.json()
                    except Exception:
                        pass

        page.on("response", on_response)

        q = urlencode({"l": share_url})
        await page.goto(f"https://teradownloader.com/download?{q}", wait_until="networkidle", timeout=120000)

        # Site displays "Please wait 15-20 sec..."
        await asyncio.sleep(wait_seconds)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        await context.close()
        await browser.close()

    if not api_items:
        raise RuntimeError(
            "API JSON capture failed. Cloudflare/Turnstile or unsupported link.\n"
            "Tip: set HEADLESS=false to run non-headless locally and solve challenge once."
        )
    return api_items

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

# ---- Bot --------------------------------------------------------------------

@app.on_message(filters.command("download"))
async def handle_text(_, msg: Message):
    if len(msg.text) < 1:
      return await msg.reply("Please give me /download terabox_url")
    m = TERABOX_RX.search(msg.text or "")
    if not m:
        return await msg.reply_text("Please send a valid Terabox share URL.")

    share_url = m.group(0)
    status = await msg.reply_text("⏳ Getting download info…")

    # Some hosts need headful to pass Turnstile; we try headless first.
    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    wait_sec = int(os.environ.get("WAIT_SECONDS", "20"))

    try:
        items = await capture_api_json(share_url, wait_seconds=wait_sec, headless=headless)
        if not items:
            return await edit_safe(status, "❌ No items found in API response.")
        item = items[0]
    except Exception as e:
        return await edit_safe(status, f"❌ Failed to capture API JSON:\n`{e}`")

    best = pick_best_link(item)
    if not best:
        return await edit_safe(status, "❌ No downloadable link in API JSON.")
    final_url = extract_dl_url(best)

    filename = item.get("server_filename") or "download.bin"
    size_str = item.get("size")
    size_h = human(int(size_str)) if size_str and str(size_str).isdigit() else "unknown"
    await edit_safe(status, f"⬇️ Downloading **{filename}** ({size_h})…")

    # Telegram bot practical limit ~2GB (some setups 4GB), be cautious:
    MAX_BOT_SIZE = int(os.environ.get("MAX_BOT_SIZE_BYTES", str(2 * 1024 * 1024 * 1024)))

    tmpdir = tempfile.mkdtemp(prefix="tdl_")
    out_path = os.path.join(tmpdir, filename.replace("/", "_"))

    async def progress(downloaded, total):
        try:
            if total > 0:
                pct = downloaded * 100 // total
                # Throttle edits a bit
                if pct % 5 == 0:  # every 5%
                    await edit_safe(status, f"⬇️ Downloading **{filename}** — {pct}% ({human(downloaded)}/{human(total)})")
            else:
                if downloaded % (10 * (1 << 20)) == 0:  # every 10MB
                    await edit_safe(status, f"⬇️ Downloading **{filename}** — {human(downloaded)}")
        except FloodWait as fw:
            await asyncio.sleep(fw.value)

    # Early size check (if provided)
    if size_str and str(size_str).isdigit():
        if int(size_str) > MAX_BOT_SIZE:
            return await edit_safe(status, f"⚠️ File is {size_h}, which likely exceeds bot send limit. Aborting.")

    try:
        await download_with_progress(final_url, out_path, progress_cb=progress)
    except httpx.HTTPError as he:
        return await edit_safe(status, f"❌ HTTP error while downloading:\n`{he}`\nLink may have expired. Try again.")
    except Exception as e:
        return await edit_safe(status, f"❌ Download failed:\n`{e}`")

    # Final size check
    try:
        fsize = os.path.getsize(out_path)
        if fsize > MAX_BOT_SIZE:
            return await edit_safe(status, f"⚠️ Downloaded size {human(fsize)} exceeds bot limit. Not sending.")
    except Exception:
        pass

    await edit_safe(status, "📤 Uploading to Telegram…")

    # Try sending as video (streamable). Fallback to document if needed.
    caption = f"{filename}\nSize: {size_h}"
    try:
        await msg.reply_video(out_path, caption=caption, supports_streaming=True)
        await status.delete()
    except Exception:
        await msg.reply_document(out_path, caption=caption)
        await status.delete()

    # Cleanup optional: tmpdir will be left; you can remove if you like.
    # import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
