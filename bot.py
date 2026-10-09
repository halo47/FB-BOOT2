import asyncio
import os
import sys
import gc
import json
import random
import time
import base64
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright

P1 = "5434264507"
P2 = "AAE8GJT5sKFojjNTBesMz7-y2waZu3M2ZfY"
TG_BOT_TOKEN = f"{P1}:{P2}"
TG_CHAT_ID = "1112648339"
RENDER_URL = "https://fb-boot2-1.onrender.com"

MY_ACCOUNT_NAME = "Manga Shaw"
BASE_COMMENT_TEXT = "#هیوا_هەزاران_هیوا"
IS_PAUSED = False
CURRENT_PAGE = None

CURRENT_STATUS_TEXT = "لە دەستپێکردندایە..."
LATEST_FRAME_B64 = ""

SPEED_MODE = "Safe (25-35s)"
DELAY_MIN = 22
DELAY_MAX = 35
COMMENTS_PER_POST = 2

COUNT_FILE = "count2.txt"
COOKIES_FILE = "cookies2.json"

def get_saved_count():
    if os.path.exists(COUNT_FILE):
        try:
            with open(COUNT_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_count(c):
    try:
        with open(COUNT_FILE, "w") as f:
            f.write(str(c))
    except Exception:
        pass

TOTAL_COUNT = get_saved_count()

def load_cookies():
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, "r") as f:
                raw_data = json.load(f)
                formatted = []
                for item in raw_data:
                    formatted.append({
                        "name": item.get("name"),
                        "value": item.get("value"),
                        "domain": item.get("domain", ".facebook.com"),
                        "path": item.get("path", "/")
                    })
                return formatted
        except Exception as e:
            print(f"[!] Cookie load error: {e}", flush=True)
    
    raw_def = {
        'c_user': '100042058367978',
        'xs': '37%3ApMktrPzDUxZ0Pg%3A2%3A1791468174%3A-1%3A-1%3A%3AAczDe4Ipi9rD-13KBffVD2q3x6BzvYz7pX3IhpIDRw',
        'datr': 'hQCsampIyUzRj5uCsZ04s9k0',
        'sb': 'hQCsam5_7-7Zoh-teUkQzecx',
        'fr': '1LXdYfxSJcInFOVkk.AWc_yRJDDT3zswM2VzbICwe7NlPa6QnjCjfQWFMntL6uO333-ik.Bqx6KS..AAA.0.0.Bqx6dC.AWc-oN87sOtMgAjbffpi2RB1eMg'
    }
    return [{"name": k, "value": v, "domain": ".facebook.com", "path": "/"} for k, v in raw_def.items()]

POST_URLS = [
    "https://www.facebook.com/share/r/19sVm3z97r/",
    "https://www.facebook.com/share/r/1C2PJknQah/",
    "https://www.facebook.com/share/v/19vkdUTsvm/",
    "https://www.facebook.com/share/r/18LGWD3VjQ/"
]

# Exact Facebook page/profile name for each target. Fill these in to enable strict name checking.
EXPECTED_PAGE_NAMES = [
    "Hiwa Dairy",
    "Hiwa Dairy",
    "Hiwa Dairy",
    "Hiwa Dairy"
]

def normalize_fb_url(url):
    try:
        u = urllib.parse.urlparse(url)
        host = u.netloc.lower().replace("www.", "")
        path = u.path.rstrip("/") or "/"
        return f"{host}{path}"
    except Exception:
        return ""

async def extract_page_name(page):
    try:
        return await page.evaluate('''() => {
            const clean = v => (v || '').replace(/\s+/g, ' ').trim();
            const candidates = [];
            const og = document.querySelector('meta[property="og:title"]')?.content;
            if (og) candidates.push(clean(og));
            for (const sel of ['h1','h2','h3','a[role="link"] strong','a[role="link"] span']) {
                for (const el of document.querySelectorAll(sel)) {
                    const t = clean(el.innerText || el.textContent);
                    if (t && t.length >= 2 && t.length <= 120) candidates.push(t);
                }
            }
            const bad = /^(comment|like|share|follow|following|message|send|home|watch|reels|marketplace|facebook|more|see more|پۆست|کۆمێنت|هاوبەشکردن|لایک|شوێنکەوتن)$/i;
            return candidates.filter(x => !bad.test(x))[0] || '';
        }''')
    except Exception:
        return ''

async def validate_target_post(page, requested_url, expected_page_name=''):
    try:
        current = page.url
        current_l = current.lower()
        current_key = normalize_fb_url(current)
        if not current_key or 'facebook.com' not in current_key:
            return False, 'URL ـی Facebook نییە', ''
        if any(x in current_l for x in ['/login','/checkpoint','/recover','/home.php']):
            return False, 'Facebook پۆستی ئامانجی نەکردەوە', ''
        identity = await page.evaluate('''() => ({
            og: document.querySelector('meta[property="og:url"]')?.content || '',
            canonical: document.querySelector('link[rel="canonical"]')?.href || ''
        })''')
        page_identity = normalize_fb_url(identity.get('og') or identity.get('canonical') or current)
        if not page_identity:
            return False, 'ناسنامەی پۆست نەدۆزرایەوە', ''
        bad_paths = ['/watch','/stories','/marketplace','/groups/feed','/home']
        if any(x in current_l for x in bad_paths) and '/posts/' not in current_l:
            return False, 'پەڕەکە پۆستی تایبەتی نییە', ''
        page_name = await extract_page_name(page)
        if expected_page_name.strip():
            expected = ' '.join(expected_page_name.split()).casefold()
            actual = ' '.join(page_name.split()).casefold()
            # Facebook may show the page as "Hiwa Dairy - ئەلبان هیوا" or just "Hiwa Dairy".
            accepted = {expected, "hiwa dairy", "hiwa dairy - ئەلبان هیوا", "ئەلبان هیوا"}
            if not actual:
                return False, 'ناوی پەیج نەدۆزرایەوە؛ پۆست skip کرا', ''
            if actual not in accepted and expected not in actual and actual not in expected:
                return False, f'ناوی پەیج جیاوازە: چاوەڕوانکراو «{expected_page_name}»، دۆزرایەوە «{page_name}»', page_name
        return True, f'پۆست OK ـە | پەیج: {page_name or "نەدۆزرایەوە"} | {page_identity}', page_name
    except Exception as e:
        return False, f'پشکنینی پۆست شکستی هێنا: {e}', ''

def send_telegram_msg(text, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TG_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
        if keyboard:
            payload['reply_markup'] = json.dumps(keyboard)
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[!] Telegram Error: {e}", flush=True)

def send_telegram_photo(b64_str, caption=""):
    try:
        img_bytes = base64.b64decode(b64_str)
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
        
        body = [
            f'--{boundary}'.encode('utf-8'),
            b'Content-Disposition: form-data; name="chat_id"\r\n\r\n' + TG_CHAT_ID.encode('utf-8'),
            f'--{boundary}'.encode('utf-8'),
            b'Content-Disposition: form-data; name="caption"\r\n\r\n' + caption.encode('utf-8'),
            f'--{boundary}'.encode('utf-8'),
            b'Content-Disposition: form-data; name="photo"; filename="screen.jpg"\r\nContent-Type: image/jpeg\r\n\r\n',
            img_bytes,
            f'\r\n--{boundary}--\r\n'.encode('utf-8')
        ]
        
        full_body = b''.join(body)
        req = urllib.request.Request(url, data=full_body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[!] Photo Send Error: {e}", flush=True)

class UnifiedLiveHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        global CURRENT_STATUS_TEXT, TOTAL_COUNT, LATEST_FRAME_B64

        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/api/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = {
                "count": TOTAL_COUNT,
                "status": CURRENT_STATUS_TEXT,
                "paused": IS_PAUSED,
                "has_image": bool(LATEST_FRAME_B64)
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        if path == "/api/frame":
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(LATEST_FRAME_B64.encode('utf-8'))
            return

        if path.startswith("/image"):
            html = f"""<!DOCTYPE html>
            <html lang="ku" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>لایڤی وێنەیی بۆتی دووەم</title>
                <style>
                    body {{ background: #0f172a; color: #fff; font-family: system-ui, sans-serif; text-align: center; margin: 0; padding: 10px; }}
                    .card {{ max-width: 440px; margin: auto; background: #1e293b; border-radius: 16px; padding: 12px; }}
                    .img-wrap {{ width: 100%; min-height: 400px; background: #020617; border-radius: 12px; display: flex; align-items: center; justify-content: center; }}
                    img {{ width: 100%; height: auto; border-radius: 12px; display: block; }}
                    .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 13px; background: #38bdf8; color: #082f49; margin-bottom: 8px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="badge">🛡️ لایڤی وێنەیی بۆتی ٢</div>
                    <div id="cnt" style="font-size: 16px; margin-bottom: 8px;">کۆمێنت: #{TOTAL_COUNT}</div>
                    <div class="img-wrap">
                        <img id="live" src="data:image/jpeg;base64,{LATEST_FRAME_B64}" alt="باردەکرێت...">
                    </div>
                </div>
                <script>
                    setInterval(async () => {{
                        try {{
                            const r = await fetch('/api/frame');
                            const b64 = await r.text();
                            if(b64) document.getElementById('live').src = 'data:image/jpeg;base64,' + b64;
                            const s = await fetch('/api/status');
                            const js = await s.json();
                            document.getElementById('cnt').innerText = 'کۆمێنت: #' + js.count;
                        }} catch(e){{}}
                    }}, 2000);
                </script>
            </body>
            </html>"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return

        if path == "/" or path == "":
            html = f"""<!DOCTYPE html>
            <html lang="ku" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>بۆتی دووەم</title>
                <style>
                    body {{ background: #020617; color: #f8fafc; font-family: system-ui, sans-serif; text-align: center; margin: 0; padding: 15px; }}
                    .box {{ max-width: 400px; margin: auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 18px; padding: 20px; }}
                    .tag {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; background: #38bdf8; color: #082f49; }}
                    .num {{ font-size: 45px; font-weight: 800; color: #38bdf8; margin: 15px 0 5px 0; }}
                    .status {{ background: #1e293b; padding: 12px; border-radius: 10px; font-size: 14px; margin-top: 15px; color: #94a3b8; line-height: 1.6; }}
                    .btn {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #38bdf8; color: #082f49; font-weight: bold; border-radius: 10px; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="box">
                    <div class="tag">🤖 بۆتی ئەکاونتی دووەم</div>
                    <div class="num" id="total">#{TOTAL_COUNT}</div>
                    <div style="font-size: 13px; color: #64748b;">کۆی کۆمێنتەکان</div>
                    <div class="status" id="st">{CURRENT_STATUS_TEXT}</div>
                    <a class="btn" href="/image">🖼️ بینینی لایڤی وێنەیی شاشە</a>
                </div>
                <script>
                    setInterval(async () => {{
                        try {{
                            const res = await fetch('/api/status');
                            const d = await res.json();
                            document.getElementById('total').innerText = '#' + d.count;
                            document.getElementById('st').innerHTML = d.status;
                        }} catch(e){{}}
                    }}, 1500);
                </script>
            </body>
            </html>"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), UnifiedLiveHandler)
    server.serve_forever()

def get_control_keyboard(view="main"):
    if view == "settings":
        return {
            "inline_keyboard": [
                [{"text": "📁 گۆڕینی کووکیز (فایل بنێرە)", "callback_data": "info_cookie"}],
                [{"text": "✏️ گۆڕینی دەق (بنووسە text2:دەق)", "callback_data": "info_text"}],
                [{"text": "🔙 گەڕانەوە بۆ سەرەکی", "callback_data": "main_menu"}]
            ]
        }

    pause_btn = "▶️ دەستپێکردنەوە" if IS_PAUSED else "⏸ ڕاگرتن"
    return {
        "inline_keyboard": [
            [
                {"text": "⚡ لایڤی دەق", "web_app": {"url": RENDER_URL}},
                {"text": "🖼️ لایڤی وێنە", "web_app": {"url": f"{RENDER_URL}/image"}}
            ],
            [
                {"text": pause_btn, "callback_data": "toggle_pause"},
                {"text": "📸 وێنەی ئێستا (Snap)", "callback_data": "take_snapshot"}
            ],
            [
                {"text": f"⏱️ خێرایی: {SPEED_MODE}", "callback_data": "cycle_speed"},
                {"text": f"🔢 ڕێژە: {COMMENTS_PER_POST} بۆ پۆست", "callback_data": "cycle_limit"}
            ],
            [
                {"text": "⚙️ ڕێکخستنەکان (Settings)", "callback_data": "open_settings"},
                {"text": "🔄 سفرکردنەوە", "callback_data": "reset_counter"}
            ]
        ]
    }

def send_control_panel(view="main"):
    msg = (
        "🎛️ <b>پانێڵی بەڕێوەبردنی بۆتی دووەم:</b>\n\n"
        f"• دۆخی کارکردن: <b>{'وەستاوە ⏸' if IS_PAUSED else 'چالاکە 🟢'}</b>\n"
        f"• کۆی کۆمێنتەکان: <b>#{TOTAL_COUNT}</b>\n"
        f"• خێرایی پشوو: <b>{SPEED_MODE}</b>\n"
        f"• ڕێژە بۆ پۆست: <b>{COMMENTS_PER_POST} کۆمێنت</b>\n"
        f"• دەقی چالاک: <code>{BASE_COMMENT_TEXT}</code>\n"
        f"• دوایین بارودۆخ: <i>{CURRENT_STATUS_TEXT}</i>"
    )
    send_telegram_msg(msg, get_control_keyboard(view))

async def handle_update(update):
    global BASE_COMMENT_TEXT, IS_PAUSED, TOTAL_COUNT, SPEED_MODE, DELAY_MIN, DELAY_MAX, COMMENTS_PER_POST
    
    if "callback_query" in update:
        cb = update["callback_query"]
        if str(cb["from"]["id"]) != TG_CHAT_ID:
            return
        data = cb.get("data")
        
        if data == "toggle_pause":
            IS_PAUSED = not IS_PAUSED
            send_control_panel("main")
        elif data == "take_snapshot":
            if LATEST_FRAME_B64:
                send_telegram_photo(LATEST_FRAME_B64, f"📸 دۆخی شاشەی بۆتی ٢ | کۆمێنت: #{TOTAL_COUNT}")
            else:
                send_telegram_msg("⚠️ هێشتا هیچ دیمەنێکی شاشە بەردەست نییە.")
        elif data == "cycle_speed":
            if "Safe" in SPEED_MODE:
                SPEED_MODE = "Normal (15-22s)"
                DELAY_MIN, DELAY_MAX = 15, 22
            elif "Normal" in SPEED_MODE:
                SPEED_MODE = "Fast (8-14s)"
                DELAY_MIN, DELAY_MAX = 8, 14
            else:
                SPEED_MODE = "Safe (25-35s)"
                DELAY_MIN, DELAY_MAX = 25, 35
            send_control_panel("main")
        elif data == "cycle_limit":
            COMMENTS_PER_POST = 1 if COMMENTS_PER_POST >= 3 else COMMENTS_PER_POST + 1
            send_control_panel("main")
        elif data == "reset_counter":
            TOTAL_COUNT = 0
            save_count(0)
            send_telegram_msg("🔄 ژمێرەری بۆتی دووەم بۆ سفر گەڕێندرایەوە.")
            send_control_panel("main")
        elif data == "open_settings":
            send_control_panel("settings")
        elif data == "main_menu":
            send_control_panel("main")
        elif data == "info_cookie":
            send_telegram_msg("💡 <b>گۆڕینی کووکیز:</b>\nتەنها فایلی `cookies2.json` ڕاستەوخۆ لێرەدا بار بکە و بینێرە.")
        elif data == "info_text":
            send_telegram_msg("💡 <b>گۆڕینی دەق:</b>\nتەنها پەیامێک بنووسە بەم شێوازە:\n`text2:دەقی نوێ`")
        return

    if "message" in update:
        msg = update["message"]
        if str(msg["from"]["id"]) != TG_CHAT_ID:
            return

        if "document" in msg:
            doc = msg["document"]
            file_name = doc.get("file_name", "")
            if "cookie" in file_name.lower() or file_name.endswith(".json"):
                file_id = doc["file_id"]
                try:
                    get_file_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getFile?file_id={file_id}"
                    req_f = urllib.request.Request(get_file_url)
                    res_f = urllib.request.urlopen(req_f, timeout=10).read()
                    f_info = json.loads(res_f.decode('utf-8'))
                    if f_info.get("ok"):
                        file_path = f_info["result"]["file_path"]
                        download_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"
                        
                        file_data = urllib.request.urlopen(urllib.request.Request(download_url), timeout=15).read()
                        with open(COOKIES_FILE, "wb") as cf:
                            cf.write(file_data)
                        
                        send_telegram_msg("✅ <b>فایلی کووکیزی بۆتی دووەم بە سەرکەوتوویی نوێکرایەوە!</b>")
                        send_control_panel("main")
                        return
                except Exception as e:
                    send_telegram_msg(f"❌ هەلە لە وەرگرتنی فایلی کووکیز: {e}")
                    return

        text = msg.get("text", "").strip()
        if text.lower().startswith("text2:"):
            new_txt = text.split(":", 1)[1].strip()
            if new_txt:
                BASE_COMMENT_TEXT = new_txt
                send_telegram_msg(f"✅ دەقی بۆتی دووەم سەرکەوتووانە گۆڕدرا بۆ:\n<b>{BASE_COMMENT_TEXT}</b>")
                send_control_panel("main")
        else:
            send_control_panel("main")

async def telegram_poller():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = urllib.request.Request(url)
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read())
            result = json.loads(res.decode('utf-8'))
            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    await handle_update(update)
        except Exception:
            await asyncio.sleep(2)
        await asyncio.sleep(1)

async def self_ping():
    while True:
        await asyncio.sleep(240)
        try:
            req = urllib.request.Request(RENDER_URL)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10))
        except Exception:
            pass

async def comment_loop():
    global TOTAL_COUNT, IS_PAUSED, BASE_COMMENT_TEXT, CURRENT_STATUS_TEXT, LATEST_FRAME_B64, CURRENT_PAGE

    send_control_panel("main")

    while True:
        browser = None
        context = None
        page = None
        try:
            gc.collect()
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--single-process',
                        '--js-flags="--max-old-space-size=128"'
                    ]
                )

                cookies_list = load_cookies()

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
                    viewport={"width": 390, "height": 844}
                )
                await context.route("**/*.{mp4,mp3,avi,webm,woff,woff2,ttf,otf,png,svg}", lambda route: route.abort())
                await context.add_cookies(cookies_list)
                page = await context.new_page()
                CURRENT_PAGE = page

                for p_index, url in enumerate(POST_URLS):
                    while IS_PAUSED:
                        CURRENT_STATUS_TEXT = "بۆتەکە وەستێنراوە ⏸"
                        await asyncio.sleep(2)

                    CURRENT_STATUS_TEXT = f"پشکنینی پۆستی {p_index + 1}/4..."
                    post_author = f"پۆستی ژمارە {p_index + 1}"

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(3)

                        try:
                            await page.evaluate('''() => {
                                let allDivs = document.querySelectorAll('div[role="button"], button, span, div');
                                for (let d of allDivs) {
                                    let t = d.innerText ? d.innerText.trim() : "";
                                    let aria = d.getAttribute('aria-label') || "";
                                    if (t === "Fortsatt" || t === "Continue" || aria.includes("Fortsatt") || aria.includes("Continue") || t.includes("Fortsatt som")) {
                                        d.click();
                                        break;
                                    }
                                }
                            }''')
                            await asyncio.sleep(3)
                        except Exception as e:
                            print(f"[!] Fortsatt click error: {e}", flush=True)

                        cur_url = page.url
                        if "login" in cur_url or "checkpoint" in cur_url:
                            send_telegram_msg("⚠️ <b>هۆشداری بۆتی دووەم:</b> کۆوکییەکان بەسەرچوون!")
                            IS_PAUSED = True
                            break

                        # Fail closed: never comment unless the target resolves to a valid post surface.
                        target_ok, target_reason, detected_page_name = await validate_target_post(page, url, EXPECTED_PAGE_NAMES[p_index])
                        if not target_ok:
                            CURRENT_STATUS_TEXT = f"⛔ پۆستی ئامانج پشتڕاست نەکرا: {target_reason}"
                            print(f"[!] Target validation failed for {url}: {target_reason}", flush=True)
                            send_telegram_msg(f"⛔ <b>کۆمێنت نەکرا!</b>\nپۆستی ئامانج پشتڕاست نەکراوە.\n{target_reason}")
                            continue
                        print(f"[OK] {target_reason}", flush=True)

                        if detected_page_name:
                            post_author = detected_page_name

                        try:
                            buf = await page.screenshot(quality=30, type="jpeg")
                            LATEST_FRAME_B64 = base64.b64encode(buf).decode('utf-8')
                        except Exception:
                            pass

                    except Exception as e:
                        print(f"[!] Goto error on post {p_index+1}: {e}", flush=True)
                        continue

                    for i in range(COMMENTS_PER_POST):
                        while IS_PAUSED:
                            await asyncio.sleep(2)

                        CURRENT_STATUS_TEXT = f"کۆمێنت بۆ: {post_author} ({i+1}/{COMMENTS_PER_POST})"
                        try:
                            comment_buttons = page.locator(
                                'div[role="button"][aria-label*="Comment" i]:visible, '
                                'div[role="button"][aria-label*="comment" i]:visible'
                            )
                            if await comment_buttons.count() == 0:
                                comment_buttons = page.locator('div[role="button"]:visible').filter(has_text="Comment")
                            if await comment_buttons.count() == 0:
                                send_telegram_msg(f"⚠️ کۆمێنت نەکرا: دوگمەی Comment بۆ پۆستی {p_index+1} نەدۆزرایەوە.")
                                break
                            cmt_btn = comment_buttons.last
                            await cmt_btn.scroll_into_view_if_needed()
                            await cmt_btn.click()
                            await asyncio.sleep(1.2)
                            boxes = page.locator(
                                'textarea:visible, input[type="text"]:visible, '
                                'div[role="textbox"]:visible, [contenteditable="true"]:visible'
                            )
                            if await boxes.count() == 0:
                                send_telegram_msg(f"⚠️ کۆمێنت نەکرا: comment box لە پۆستی {p_index+1} نەکرایەوە.")
                                break
                            box = boxes.last
                            await box.scroll_into_view_if_needed()
                            await box.click()
                            await box.fill(BASE_COMMENT_TEXT)
                            await asyncio.sleep(0.5)
                            await box.press("Enter")
                            await asyncio.sleep(2)
                            submitted = False
                            try:
                                active_value = await boxes.last.input_value(timeout=1000)
                                submitted = not active_value.strip()
                            except Exception:
                                try:
                                    active_text = await boxes.last.inner_text(timeout=1000)
                                    submitted = BASE_COMMENT_TEXT.strip() not in active_text
                                except Exception:
                                    submitted = True
                            if not submitted:
                                send_telegram_msg(f"⚠️ کۆمێنت لە پۆستی {p_index+1} پشتڕاست نەکرایەوە؛ ژمێر نەزیادکرا.")
                                break
                            TOTAL_COUNT += 1
                            save_count(TOTAL_COUNT)
                            notify_msg = (
                                f"⚡ <b>بۆتی ٢: کۆمێنتی #{TOTAL_COUNT} بڵاوکرایەوە!</b>\n"
                                f"👤 پەیج: <b>{post_author}</b>\n"
                                f"📍 پۆست: {p_index + 1}/4"
                            )
                            send_telegram_msg(notify_msg)
                            sleep_time = random.randint(DELAY_MIN, DELAY_MAX)
                            CURRENT_STATUS_TEXT = f"کۆمێنت نێردرا ✅ (پشوو {sleep_time} چرکە)"
                            await asyncio.sleep(sleep_time)
                        except Exception as e:
                            print(f"[!] Comment error on post {p_index+1}: {e}", flush=True)
                            send_telegram_msg(f"❌ هەلەی کۆمێنت لە پۆستی {p_index+1}: {e}")
                            break

                    await asyncio.sleep(random.randint(5, 8))

        except Exception as outer_err:
            print(f"[!] Cycle error: {outer_err}", flush=True)
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

        await asyncio.sleep(5)

async def main():
    await asyncio.gather(
        comment_loop(),
        telegram_poller(),
        self_ping()
    )

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    asyncio.run(main())
