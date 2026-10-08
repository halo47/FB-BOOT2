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

# زانیارییە نوێیەکانی بۆتی تلیگرام
P1 = "5434264507"
P2 = "AAE8GJT5sKFojjNTBesMz7-y2waZu3M2ZfY"
TG_BOT_TOKEN = f"{P1}:{P2}"
TG_CHAT_ID = "1112648339"
RENDER_URL = "https://fb-boot-2.onrender.com"

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

# لینکی پۆستە نوێیەکان
POST_URLS = [
    "https://www.facebook.com/share/r/19sVm3z97r/",
    "https://www.facebook.com/share/r/1C2PJknQah/",
    "https://www.facebook.com/share/v/19vkdUTsvm/",
    "https://www.facebook.com/share/r/18LGWD3VjQ/"
]

# کووکیزە ڕێکخراوەکانی ئەکاونتی دووەم
COOKIES = [
    {"domain": ".facebook.com", "name": "c_user", "value": "100042058367978", "path": "/", "secure": True, "sameSite": "None"},
    {"domain": ".facebook.com", "name": "datr", "value": "hQCsampIyUzRj5uCsZ04s9k0", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
    {"domain": ".facebook.com", "name": "fr", "value": "18afc39V6gfdiOLO0.AWfFGevKxMbaKFMaybw9bAyUre6mkLD4eVxGYw0att78lyZKdds.Bqx4ZL..AAA.0.0.Bqx4ah.AWc3DAhcXfB2tHzPYnW1VjkldHA", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
    {"domain": ".facebook.com", "name": "sb", "value": "hQCsam5_7-7Zoh-teUkQzecx", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
    {"domain": ".facebook.com", "name": "xs", "value": "1%3AW_y6zezPOsSGPg%3A2%3A1791460934%3A-1%3A-1%3A%3AAcx-EZ8KIhxA3jcObS1aUSsBjNjaxy7ybAMxZ2NrdQ", "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"}
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
        print(f"[!] Telegram Error: {e}", flush=True)

class UnifiedLiveHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        global CURRENT_STATUS_TEXT, TOTAL_COUNT, LATEST_FRAME_B64

        if self.path == "/api/status":
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
            </style>
        </head>
        <body>
            <div class="box">
                <div class="tag">🤖 بۆتی ئەکاونتی دووەم</div>
                <div class="num" id="total">#{TOTAL_COUNT}</div>
                <div style="font-size: 13px; color: #64748b;">کۆی کۆمێنتەکان</div>
                <div class="status" id="st">{CURRENT_STATUS_TEXT}</div>
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

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), UnifiedLiveHandler)
    server.serve_forever()

def get_control_keyboard():
    pause_btn = "▶️ دەستپێکردنەوە" if IS_PAUSED else "⏸ ڕاگرتن"
    return {
        "inline_keyboard": [
            [{"text": "⚡ لایڤی دەق", "web_app": {"url": RENDER_URL}}],
            [{"text": pause_btn, "callback_data": "toggle_pause"}],
            [{"text": "🔄 سفرکردنەوەی ژمێرەر", "callback_data": "reset_counter"}]
        ]
    }

def send_control_panel():
    msg = (
        "🎛️ <b>پانێڵی بۆتی دووەم (ئەکاونتی تر):</b>\n\n"
        f"• دۆخی کارکردن: <b>{'وەستاوە ⏸' if IS_PAUSED else 'چالاکە 🟢'}</b>\n"
        f"• کۆی کۆمێنتەکان: <b>#{TOTAL_COUNT}</b>\n"
        f"• دەقی چالاک: <code>{BASE_COMMENT_TEXT}</code>\n"
        f"• دوایین بارودۆخ: <i>{CURRENT_STATUS_TEXT}</i>"
    )
    send_telegram_msg(msg, get_control_keyboard())

async def handle_update(update):
    global IS_PAUSED, TOTAL_COUNT
    if "callback_query" in update:
        cb = update["callback_query"]
        if str(cb["from"]["id"]) != TG_CHAT_ID:
            return
        data = cb.get("data")
        if data == "toggle_pause":
            IS_PAUSED = not IS_PAUSED
            send_control_panel()
        elif data == "reset_counter":
            TOTAL_COUNT = 0
            save_count(0)
            send_telegram_msg("🔄 ژمێرەری بۆتی دووەم سفربووەوە.")
            send_control_panel()
        return

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
    global TOTAL_COUNT, IS_PAUSED, CURRENT_STATUS_TEXT, CURRENT_PAGE

    send_control_panel()

    while True:
        if IS_PAUSED:
            CURRENT_STATUS_TEXT = "بۆتەکە وەستێنراوە ⏸"
            await asyncio.sleep(2)
            continue

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

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
                    viewport={"width": 390, "height": 844}
                )
                await context.route("**/*.{mp4,mp3,avi,webm,woff,woff2,ttf,otf,png,svg}", lambda route: route.abort())
                await context.add_cookies(COOKIES)
                page = await context.new_page()
                CURRENT_PAGE = page

                for p_index, url in enumerate(POST_URLS):
                    while IS_PAUSED:
                        CURRENT_STATUS_TEXT = "بۆتەکە وەستێنراوە ⏸"
                        await asyncio.sleep(2)

                    CURRENT_STATUS_TEXT = f"پشکنینی پۆستی {p_index + 1}/4..."

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)

                        cur_url = page.url
                        if "login" in cur_url or "checkpoint" in cur_url:
                            send_telegram_msg("⚠️ <b>هۆشداری بۆتی دووەم:</b> کۆوکی ئەکاونتی دووەم بەسەرچوو!")
                            IS_PAUSED = True
                            break
                    except Exception:
                        continue

                    for i in range(COMMENTS_PER_POST):
                        while IS_PAUSED:
                            await asyncio.sleep(2)

                        CURRENT_STATUS_TEXT = f"ناردنی کۆمێنت ({i+1}/{COMMENTS_PER_POST})..."
                        try:
                            cmt_btn = await page.query_selector('div[aria-label*="Comment" i], div[role="button"]:has-text("Comment")')
                            if cmt_btn:
                                await cmt_btn.click()
                                await asyncio.sleep(1)

                            box = await page.wait_for_selector('textarea, input[type="text"], div[role="textbox"], [contenteditable="true"]', timeout=3000)
                            if box:
                                await box.fill(BASE_COMMENT_TEXT)
                                await asyncio.sleep(0.4)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(2)

                                TOTAL_COUNT += 1
                                save_count(TOTAL_COUNT)
                                send_telegram_msg(f"⚡ <b>بۆتی ٢: کۆمێنتی #{TOTAL_COUNT} بڵاوکرایەوە!</b>")

                                sleep_time = random.randint(DELAY_MIN, DELAY_MAX)
                                await asyncio.sleep(sleep_time)
                            else:
                                break
                        except Exception:
                            break

                    await asyncio.sleep(random.randint(5, 8))

                await browser.close()
        except Exception as outer_err:
            print(f"[!] Error: {outer_err}", flush=True)

        await asyncio.sleep(10)

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
