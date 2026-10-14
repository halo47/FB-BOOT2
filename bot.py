import asyncio
import os
import sys
import gc
import json
import random
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright

# ==================== ڕێکخستنە سەرەکییەکان بۆتی دووەم ====================
P1 = "5434264507"
P2 = "AAE8GJT5sKFojjNTBesMz7-y2waZu3M2ZfY"
TG_BOT_TOKEN = f"{P1}:{P2}"
TG_CHAT_ID = "1112648339"
RENDER_URL = "https://fb-boot2-1.onrender.com"

MY_ACCOUNT_NAME = "Manga Shaw"
BASE_COMMENT_TEXT = "#هیوا_هەزاران_هیوا"
IS_PAUSED = False
CURRENT_PAGE = None

# سیستەمی 90 چرکە بۆ پاراستنی ئەکاونت و گەیشتن بە 960 کۆمێنت
SPEED_MODE = "Exact 960 Comments (90s)"
DELAY_MIN = 40
DELAY_MAX = 40
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
        print(f"[!] Telegram Msg Error: {e}", flush=True)

def send_telegram_file(file_path, caption=""):
    try:
        if not os.path.exists(file_path):
            return
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = bytearray()
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{TG_CHAT_ID}\r\n'.encode('utf-8'))
        if caption:
            body.extend(f'--{boundary}\r\n'.encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode('utf-8'))
            body.extend(f'--{boundary}\r\n'.encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode('utf-8'))
        
        filename = os.path.basename(file_path)
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
        with open(file_path, 'rb') as f:
            body.extend(f.read())
        body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

        req = urllib.request.Request(url, data=bytes(body))
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print(f"[!] File Upload Error: {e}", flush=True)

class LiveStreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/screen.jpg":
            if os.path.exists("live2.jpg"):
                try:
                    with open("live2.jpg", "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
                    self.end_headers()
                    self.wfile.write(content)
                except Exception:
                    self.send_response(500)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
            return

        if path == "/" or path == "":
            html = f"""<!DOCTYPE html>
            <html lang="ku" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>لایڤی بۆتی دووەم</title>
                <style>
                    * {{ box-sizing: border-box; }}
                    body {{ background: #0f172a; color: #fff; font-family: system-ui, sans-serif; text-align: center; margin: 0; padding: 10px; }}
                    .card {{ max-width: 420px; margin: auto; background: #1e293b; border-radius: 16px; padding: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
                    .img-container {{ width: 100%; min-height: 480px; background: #0b0f19; border-radius: 12px; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative; }}
                    img {{ width: 100%; height: auto; display: block; border-radius: 12px; }}
                    .badge {{ display: inline-block; padding: 5px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; margin-bottom: 8px; background: #38bdf8; color: #082f49; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="badge">🔴 لایڤی بۆتی ٢</div>
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">کۆمێنتەکان: #{TOTAL_COUNT}</div>
                    <div class="img-container">
                        <img id="liveImg" src="/screen.jpg" alt="چاوەڕوان بە...">
                    </div>
                </div>
                <script>
                    const img = document.getElementById('liveImg');
                    function refreshImage() {{
                        const newImg = new Image();
                        newImg.onload = () => {{
                            img.src = newImg.src;
                        }};
                        newImg.src = '/screen.jpg?t=' + Date.now();
                    }}
                    setInterval(refreshImage, 1200);
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
    server = HTTPServer(('0.0.0.0', 10000), LiveStreamHandler)
    server.serve_forever()

def send_control_panel():
    global IS_PAUSED, BASE_COMMENT_TEXT, TOTAL_COUNT, SPEED_MODE, COMMENTS_PER_POST
    pause_label = "▶️ دەستپێکردنەوە" if IS_PAUSED else "⏸ ڕاگرتنی بۆت"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔴 شاشەی لایڤ (Web App)", "web_app": {"url": RENDER_URL}}
            ],
            [
                {"text": pause_label, "callback_data": "cmd_toggle_pause"},
                {"text": "📸 وێنەی ئێستا", "callback_data": "cmd_screenshot"}
            ],
            [
                {"text": f"⏱️ خێرایی: {SPEED_MODE}", "callback_data": "cycle_speed"},
                {"text": f"🔢 ڕێژە: {COMMENTS_PER_POST} بۆ پۆست", "callback_data": "cycle_limit"}
            ],
            [
                {"text": "📊 دۆخی گشتی", "callback_data": "cmd_status"}
            ]
        ]
    }
    msg = (
        "🎛️ <b>کۆنتڕۆڵی بۆتی دووەم (سیستەمی ٩٦٠ کۆمێنت)</b>\n\n"
        f"• ئەکاونت: <b>{MY_ACCOUNT_NAME}</b>\n"
        f"• کۆی گشتیی کۆمێنت: <b>#{TOTAL_COUNT}</b>\n"
        f"• دۆخ: <b>{'وەستاوە ⏸' if IS_PAUSED else 'چالاکە 🟢'}</b>\n"
        f"• خێرایی ئێستا: <b>{SPEED_MODE}</b>\n"
        f"• ڕێژە بۆ پۆست: <b>{COMMENTS_PER_POST} کۆمێنت</b>\n"
        f"• دەق: <code>{BASE_COMMENT_TEXT}</code>\n\n"
        "💡 <i>بۆ گۆڕینی کووکیز، فایلی</i> <code>cookies2.json</code> <i>بینێرە. بۆ گۆڕینی دەق بنووسە text2:دەق</i>"
    )
    send_telegram_msg(msg, keyboard)

async def handle_update(update):
    global BASE_COMMENT_TEXT, IS_PAUSED, CURRENT_PAGE, TOTAL_COUNT, SPEED_MODE, DELAY_MIN, DELAY_MAX, COMMENTS_PER_POST
    if "callback_query" in update:
        cb = update["callback_query"]
        if str(cb["from"]["id"]) != TG_CHAT_ID:
            return
        data = cb.get("data")
        
        if data == "cmd_screenshot":
            if os.path.exists("live2.jpg"):
                threading.Thread(target=send_telegram_file, args=("live2.jpg", f"📸 وێنەی ساتی بۆتی ٢ | #{TOTAL_COUNT}")).start()
            elif CURRENT_PAGE:
                try:
                    await CURRENT_PAGE.screenshot(path="live2.jpg", quality=60, type="jpeg")
                    threading.Thread(target=send_telegram_file, args=("live2.jpg", f"📸 وێنەی ساتی بۆتی ٢ | #{TOTAL_COUNT}")).start()
                except Exception as e:
                    send_telegram_msg(f"⚠️ هەڵە: {e}")
            else:
                send_telegram_msg("⚠️ براوزەر لەم چرکەیەدا ئامادە نییە.")
        elif data == "cmd_status":
            send_telegram_msg(f"📊 کۆی گشتیی کۆمێنتەکانی بۆتی ٢: #{TOTAL_COUNT}")
        elif data == "cmd_toggle_pause":
            IS_PAUSED = not IS_PAUSED
            send_control_panel()
        elif data == "cycle_speed":
            if "960" in SPEED_MODE:
                SPEED_MODE = "Balanced (60s)"
                DELAY_MIN, DELAY_MAX = 60, 60
            elif "Balanced" in SPEED_MODE:
                SPEED_MODE = "Safe (120s)"
                DELAY_MIN, DELAY_MAX = 120, 120
            else:
                SPEED_MODE = "Exact 960 Comments (90s)"
                DELAY_MIN, DELAY_MAX = 90, 90
            send_control_panel()
        elif data == "cycle_limit":
            COMMENTS_PER_POST = 1 if COMMENTS_PER_POST >= 4 else COMMENTS_PER_POST + 1
            send_control_panel()
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
                        send_control_panel()
                        return
                except Exception as e:
                    send_telegram_msg(f"❌ هەڵە: {e}")
                    return

        text = msg.get("text", "").strip()
        if text.lower().startswith("text2:"):
            new_txt = text.split(":", 1)[1].strip()
            if new_txt:
                BASE_COMMENT_TEXT = new_txt
                send_telegram_msg(f"✅ دەقی بۆتی دووەم نوێکرایەوە بۆ:\n<b>{BASE_COMMENT_TEXT}</b>")
                send_control_panel()
        else:
            send_control_panel()

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

async def comment_loop():
    global CURRENT_PAGE, TOTAL_COUNT, IS_PAUSED, BASE_COMMENT_TEXT, DELAY_MIN, DELAY_MAX

    send_control_panel()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--js-flags="--max-old-space-size=256"']
        )

        while True:
            gc.collect()

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                viewport={"width": 390, "height": 844}
            )
            await context.route("**/*.{mp4,mp3,avi,webm,woff,woff2,ttf,otf}", lambda route: route.abort())
            
            cookies_list = load_cookies()
            await context.add_cookies(cookies_list)
            
            page = await context.new_page()
            CURRENT_PAGE = page

            try:
                for p_index, url in enumerate(POST_URLS):
                    while IS_PAUSED:
                        await asyncio.sleep(1)

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(1.5)
                        await page.screenshot(path="live2.jpg", quality=40, type="jpeg")
                    except Exception:
                        continue

                    for i in range(COMMENTS_PER_POST):
                        while IS_PAUSED:
                            await asyncio.sleep(1)

                        try:
                            clicked = await page.evaluate('''() => {
                                let btns = Array.from(document.querySelectorAll('div[role="button"], span, a'));
                                for (let b of btns) {
                                    let t = b.innerText ? b.innerText.trim().toLowerCase() : "";
                                    let aria = b.getAttribute('aria-label') ? b.getAttribute('aria-label').toLowerCase() : "";
                                    if (aria.includes('comment') || t === 'comment' || t === 'کۆمێنت') {
                                        b.click();
                                        return true;
                                    }
                                }
                                return false;
                            }''')

                            if not clicked:
                                cmt_btn = await page.query_selector('div[aria-label*="Comment" i], div[role="button"]:has-text("Comment")')
                                if cmt_btn:
                                    await cmt_btn.click()

                            await asyncio.sleep(0.5)

                            box = await page.wait_for_selector('textarea, input[type="text"], div[role="textbox"], [contenteditable="true"]', timeout=3000)
                            if box:
                                await box.fill(BASE_COMMENT_TEXT)
                                await asyncio.sleep(0.3)

                                await box.press("Enter")
                                
                                await page.evaluate('''() => {
                                    let btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                                    for (let b of btns) {
                                        let l = (b.getAttribute('aria-label') || '').toLowerCase();
                                        let t = (b.innerText || '').toLowerCase();
                                        if (l.includes('send') || l.includes('post') || l.includes('comment') || t.includes('ناردن') || t.includes('پۆست')) {
                                            b.click();
                                        }
                                    }
                                }''')

                                await asyncio.sleep(2)

                                TOTAL_COUNT += 1
                                save_count(TOTAL_COUNT)

                                try:
                                    await page.screenshot(path="live2.jpg", quality=40, type="jpeg")
                                except:
                                    pass

                                send_telegram_msg(f"⚡ <b>بۆتی ٢: کۆمێنتی #{TOTAL_COUNT} بڵاوکرایەوە!</b>\nپۆست: {p_index + 1}/4")

                                await asyncio.sleep(DELAY_MIN)
                            else:
                                break
                        except Exception as e:
                            print(f"[!] Error: {e}", flush=True)
                            break

                    await asyncio.sleep(1.5)
            finally:
                try:
                    await page.close()
                    await context.close()
                except Exception:
                    pass

            await asyncio.sleep(2)

async def main():
    await asyncio.gather(
        comment_loop(),
        telegram_poller()
    )

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    asyncio.run(main())
