# ==============================================================================
# === autologin_async_smart_v2.py - Smart, Resumable Async Bot ===
# This script works with api_server.py to solve the wplace.live CAPTCHA,
# then uses Tor (optional) to log into Google and fetch the 'j_cookie'.
# It saves its progress and can be restarted to continue where it left off.
# ==============================================================================

import asyncio
import httpx
import time
import sys
import pathlib
import os
import json
import itertools
import random

# Attempt to import required libraries and provide helpful error messages
try:
    from camoufox.async_api import AsyncCamoufox
    from playwright.async_api import TimeoutError as PWTimeout
    from browserforge.fingerprints import Screen
    from stem import Signal
    from stem.control import Controller
except ImportError:
    print("[ERROR] Required libraries not found.")
    print("        Please run: pip install -r requirements.txt")
    sys.exit(1)


# === Constants ===
STATE_FILE = "data.json"
EMAILS_FILE = "emails.txt"
PROXIES_FILE = "proxies.txt"

# === ⚙️ CONFIGURATION ⚙️ ===
# Set to True to route the Google login process through the Tor network.
# Requires Tor Browser to be installed and running.
USE_TOR = True

# Set to True to run the bot in the background without a visible browser.
# Set to False to watch the bot work and manually solve Google CAPTCHAs.
HEADLESS_MODE = True

# (Do not edit below this line)
CTRL_HOST, CTRL_PORT = "127.0.0.1", 9051
SOCKS_HOST, SOCKS_PORT = "127.0.0.1", 9050

# ===================== PROXY HANDLING =====================
def load_proxies(path=PROXIES_FILE):
    """Loads a list of proxies from the specified file."""
    p = pathlib.Path(path)
    if not p.exists():
        print(f"[ERROR] Proxies file not found: {path}")
        sys.exit(1)
    
    proxies = [
        f"http://{line.strip()}" for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    
    if not proxies:
        print("[ERROR] No valid proxies found in proxies.txt")
        sys.exit(1)
    
    # Create an infinite iterator that cycles through the proxy list
    return itertools.cycle(proxies)

proxy_pool = load_proxies()

# ===================== GOOGLE LOGIN HELPERS (Async) =====================
async def find_login_frame(page, selector_type: str, timeout_sec: int = 180):
    """
    Polls all frames on a page to find one containing a specific element.
    This is necessary for handling Google's iframe-based login forms.
    Raises a custom TimeoutError if a reCAPTCHA challenge is detected.
    """
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        for frame in page.frames:
            try:
                # Check if Google is presenting a reCAPTCHA challenge
                if "v3/signin/challenge/recaptcha" in str(frame.url).lower():
                    raise PWTimeout("Captcha shown")

                # Check if the desired element exists in the frame
                if await frame.locator(selector_type).count() > 0:
                    return frame
            except PWTimeout as e:
                # Propagate the "Captcha shown" error immediately
                raise e
            except Exception:
                # Ignore other errors (e.g., frame detached) and continue polling
                pass
        await asyncio.sleep(0.25)
    
    raise PWTimeout(f"Google login frame not found for selector '{selector_type}'")

async def poll_cookie_any_context(browser, name: str = "j", timeout_sec: int = 180):
    """Polls all browser contexts to find a specific cookie by name."""
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            for context in browser.contexts:
                cookies = await context.cookies()
                for cookie in cookies:
                    if cookie.get("name") == name:
                        return cookie
        except Exception:
            pass
        await asyncio.sleep(0.05)
    return None

# ===================== TURNSTILE SOLVER (Async) =====================
async def get_solved_token(api_url="http://localhost:8080/turnstile", target_url="https://backend.wplace.live", sitekey="0x4AAAAAABpHqZ-6i7uL0nmG"):
    """
    Communicates with the local api_server.py to solve the Cloudflare Turnstile CAPTCHA.
    """
    proxy = next(proxy_pool)
    try:
        async with httpx.AsyncClient() as client:
            # Request a solution from the API server
            response = await client.get(api_url, params={"url": target_url, "sitekey": sitekey, "proxy": proxy}, timeout=30)
            if response.status_code != 202:
                raise RuntimeError(f"Bad status {response.status_code}: {response.text}")
            
            task_id = response.json().get("task_id")
            if not task_id:
                raise RuntimeError("API server did not return a task_id")
            
            # Poll for the result
            for _ in range(60):
                await asyncio.sleep(2)
                result_response = await client.get(f"http://localhost:8080/result", params={"id": task_id}, timeout=20)
                result_data = result_response.json()

                if result_data.get("status") == "success":
                    return result_data.get("value")
                if result_data.get("status") == "error":
                    raise RuntimeError(f"Solver error: {result_data.get('value')}")
            
            raise RuntimeError("Captcha solving timed out")
    except Exception as e:
        raise RuntimeError(f"Captcha solver communication failed: {e}")

# ===================== LOGIN PROCESS (Async with Delays) =====================
async def login_once(email: str, password: str):
    """Handles the full login flow for a single account."""
    print(f"[{email}] Step 1: Solving CAPTCHA...")
    token = await get_solved_token()
    await asyncio.sleep(random.uniform(1, 3))

    print(f"[{email}] Step 2: Getting Google login URL...")
    backend_url = f"https://backend.wplace.live/auth/google?token={token}"
    proxy_http = next(proxy_pool)
    proxies = {"http://": proxy_http, "https://": proxy_http}
    try:
        async with httpx.AsyncClient(proxies=proxies) as client:
            response = await client.get(backend_url, follow_redirects=True, timeout=15)
            google_login_url = str(response.url)
    except Exception as e:
        raise RuntimeError(f"Failed to get Google login URL via proxy {proxy_http}: {e}")

    proxy_settings = {"server": f"socks5://{SOCKS_HOST}:{SOCKS_PORT}"} if USE_TOR else None
    
    async with AsyncCamoufox(headless=HEADLESS_MODE, humanize=True, proxy=proxy_settings) as camoufox:
        browser = await camoufox.start()
        page = await browser.new_page()
        
        print(f"[{email}] Step 3: Navigating to Google login page...")
        await page.goto(google_login_url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 5))

        print(f"[{email}] Step 4: Filling email...")
        email_frame = await find_login_frame(page, 'input[type="email"]')
        await email_frame.fill('input[type="email"]', email, timeout=20000)
        await asyncio.sleep(random.uniform(1, 2.5))
        await email_frame.locator('#identifierNext').click()
        
        await asyncio.sleep(random.uniform(3, 6))
        
        print(f"[{email}] Step 5: Filling password...")
        # If HEADLESS_MODE is False, this is where the user can solve a CAPTCHA
        password_frame = await find_login_frame(page, 'input[type="password"]')
        await password_frame.fill('input[type="password"]', password, timeout=20000)
        await asyncio.sleep(random.uniform(1.5, 3))
        await password_frame.locator('#passwordNext').click()
        
        print(f"[{email}] Step 6: Login submitted. Waiting for cookie...")
        cookie = await poll_cookie_any_context(browser, name="j")
        await browser.close()
        return cookie

# ===================== STATE & EMAIL FILE HANDLING =====================
def parse_emails_file(path=EMAILS_FILE):
    """Parses the email|password file."""
    p = pathlib.Path(path)
    if not p.exists():
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)
    
    pairs = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "|" not in s:
            continue
        email, password = s.split("|", 1)
        email, password = email.strip(), password.strip()
        if email and password:
            pairs.append((email, password))
    
    if not pairs:
        print(f"[ERROR] No valid credentials found in {path}")
        sys.exit(1)
    
    return pairs

def load_state():
    """Loads the progress from data.json or creates a new state."""
    if pathlib.Path(STATE_FILE).exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Create a new state if data.json doesn't exist
    pairs = parse_emails_file()
    return {
        "version": 1,
        "accounts": [
            {"email": e, "password": p, "status": "pending", "tries": 0, "last_error": "", "result": None}
            for e, p in pairs
        ]
    }

def save_state(state):
    """Safely saves the current progress to data.json."""
    temp_file = STATE_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, STATE_FILE)

# ===================== TOR HELPER =====================
def tor_newnym_cookie(host=CTRL_HOST, port=CTRL_PORT):
    """Requests a new IP address from the Tor network."""
    try:
        with Controller.from_port(address=host, port=port) as controller:
            controller.authenticate()
            if not controller.is_newnym_available():
                time.sleep(controller.get_newnym_wait())
            controller.signal(Signal.NEWNYM)
            print("[TOR] Switched to new IP.")
    except Exception as e:
        print(f"[WARN] Could not switch Tor IP: {e}")

# ===================== ACCOUNT PROCESSING =====================
async def process_account(state, index: int):
    """Processes a single account and updates its state."""
    account = state["accounts"][index]
    account["tries"] += 1
    
    try:
        print(f"\n--- [START] Processing: {account['email']} (Attempt: {account['tries']}) ---")
        cookie = await login_once(account["email"], account["password"])
        if not cookie:
            raise RuntimeError("cookie_not_found")
        
        account["status"] = "ok"
        account["last_error"] = ""
        account["result"] = {"domain": cookie.get("domain", ""), "value": cookie.get("value", "")}
        print(f"✅ [OK] {account['email']}")
        
    except Exception as e:
        account["status"] = "error"
        error_message = f"{type(e).__name__}: {e}"
        account["last_error"] = error_message.strip()
        print(f"❌ [ERR] {account['email']} | {error_message.strip()}")
    finally:
        save_state(state)
        if USE_TOR:
            tor_newnym_cookie()
        
        delay = random.randint(15, 45)
        print(f"⏱️  Pausing for {delay} seconds before next account...")
        await asyncio.sleep(delay)

# ===================== MAIN APPLICATION LOGIC =====================
async def main():
    state = load_state()
    
    print("🔎 Analyzing account statuses and building to-do list...")
    accounts_to_process_indices = []
    
    for i, account in enumerate(state["accounts"]):
        status = account.get("status", "pending")
        last_error = account.get("last_error", "")

        if status == "ok":
            print(f"✔️  Skipping completed account: {account['email']}")
            continue
        
        # Prioritize accounts that are new or failed with a solvable CAPTCHA error
        if status == "pending" or (status == "error" and "Captcha shown" in last_error):
            accounts_to_process_indices.append(i)
        else:
            print(f"❌ Skipping account with other error: {account['email']} (Error: {last_error[:70]}...)")

    if not accounts_to_process_indices:
        print("\n🎉 [DONE] No accounts need processing in this run.")
        return

    print(f"\n📋 Found {len(accounts_to_process_indices)} accounts to process in this run.")
    
    for index in accounts_to_process_indices:
        await process_account(state, index)

    print("\n🎉 [FINISHED] All tasks for this run are completed.")
    save_state(state)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED BY USER]")
    except Exception as e:
        print(f"\n[FATAL ERROR] A critical error occurred: {e}")
    finally:
        print("Exiting application.")
