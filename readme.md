Of course. This is an excellent idea. Creating a clear, professional `README.md` file is the best way to document a complex project. I will write a complete, hand-holding tutorial in English, following the exact structure and style of the example you provided.

This guide will cover the final, most advanced version of the bot we built together (`api_server.py` + the smart, asynchronous `autologin` script).

---

### **WPlace.live Autologin & J-Cookie Fetcher — README**

This is a powerful, two-part automation framework designed to log into `wplace.live` via Google accounts to fetch the `j_cookie` session token. It uses a local API server to solve the Cloudflare Turnstile CAPTCHA automatically and a main client script to handle the browser-based login flow.

The system is designed to be resilient, remembering its progress and prioritizing accounts that previously failed due to solvable issues.

### Files
-   `autologin.py` — The main client script that orchestrates the login process.
-   `api_server.py` — A local API server that solves the Cloudflare Turnstile CAPTCHA on demand.
-   `emails.txt` — The list of Google accounts. Format: `email|password`.
-   `proxies.txt` — The list of HTTP proxies. Format: `host:port`.
-   `data.json` — The progress/state file. It's created and updated automatically.
-   `requirements.txt` — A list of all required Python packages for easy installation.

### Requirements
-   Python 3.10+
-   Pip packages from `requirements.txt`.
-   **Playwright & Camoufox Browsers:** Specialized browsers required by the automation libraries.
-   **(Optional) Tor Browser:** Required only if you enable the `USE_TOR` setting. Must be installed and running.

### Installation

1.  **Prepare a requirements file.**
    Create a new file named `requirements.txt` in your project folder and paste the following content into it:
    ```
    fastapi[all]
    uvicorn
    loguru
    playwright
    stem
    camoufox[geoip]
    browserforge
    httpx
    ```

2.  **Open a terminal with Administrator privileges.**
    Navigate to your project folder (e.g., `cd C:\TorBotFinal`).

3.  **Install Python packages.**
    Run the following command to install all necessary libraries from the file you just created:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install automation browsers.**
    This step will download special browser versions required by Playwright and Camoufox. It may take a few minutes. Run these two commands:
    ```bash
    python -m playwright install
    camoufox fetch
    ```

### Start the local API

The system requires two terminals running simultaneously.

1.  **Open your first terminal** (as Administrator).
2.  Navigate to your project directory.
3.  Run the API server:
    ```bash
    python api_server.py
    ```
4.  The server is ready when you see: `Uvicorn running on http://0.0.0.0:8080`.
5.  **Leave this terminal running.** This is the CAPTCHA-solving engine.

### Prepare Input Files

Create these two text files in the same directory as the Python scripts.

**`emails.txt`**
*   **Format:** `email|password` (separated by a pipe `|` character)
*   **Example:**
    ```
    **********@gmail.com|********
    *********@gmail.com|*******
    ```

**`proxies.txt`**
*   **Format:** `host:port`
*   **Example:**
    ```
    156.***.112.13:****
    156.****.76.68:****
    ```

### Configure (OPTIONAL)

Open `autologin.py` to adjust key settings at the top of the file:

-   `USE_TOR = True` or `False`:
    -   Set to `True` to route the Google login process through the Tor network for maximum privacy. **Requires Tor Browser to be running.**
    -   Set to `False` to use your regular internet connection for the login process.
-   `HEADLESS_MODE = True` or `False`:
    -   Set to `True` to run the bot in the background without any visible browser windows. Use this for fully automated runs.
    -   Set to `False` to watch the bot work in a real browser window. **Recommended for the first run** so you can manually solve any Google CAPTCHAs that appear.

### Run

1.  **Open your second terminal** (as Administrator).
2.  Navigate to your project directory.
3.  Run the main autologin script:
    ```bash
    python autologin.py
    ```

### What Happens

1.  The script reads `data.json` to check for previously completed or failed accounts. It builds a to-do list, prioritizing accounts that failed because of a solvable Google CAPTCHA.
2.  For each account, it asks the local `api_server.py` for a Cloudflare Turnstile token.
3.  The `api_server.py` uses a proxy from `proxies.txt` to solve the CAPTCHA in the background and returns a token.
4.  The script uses the token to get the final Google login URL.
5.  It launches a Camoufox browser (routed through Tor if `USE_TOR=True`).
6.  It navigates to the Google login page and fills in the email and password.
7.  If Google presents a CAPTCHA, the script will wait, allowing you (if `HEADLESS_MODE=False`) to solve it manually.
8.  Once logged in, it finds and extracts the `j_cookie`.
9.  The result (success or failure) is saved to `data.json`.
10. The script waits for a random delay and moves to the next account.

### Outputs

-   **`data.json`**: This is the most important file. It keeps a detailed record of the status (`ok`, `error`, `pending`), attempt count, last error, and the final `j_cookie` value for every account. The script reads this file on startup to resume work.

### Troubleshooting

-   **API not reachable**: Make sure `api_server.py` is running in the first terminal and you see the "Uvicorn running" message.
-   **`ConnectionRefusedError` from Tor**: Check that Tor Browser is installed and running if you have `USE_TOR = True`. If you don't want to use Tor, set `USE_TOR = False`.
-   **`TimeoutError: Captcha shown`**: This is not a bug! It's a signal that Google is asking for human verification.
    1.  Set `HEADLESS_MODE = False` in the script.
    2.  Run the script again.
    3.  When the browser opens and gets to the Google CAPTCHA, solve it manually. The bot will detect when you're done and continue automatically.
-   **Proxy errors**: Ensure your `proxies.txt` file contains valid, working HTTP proxies.

### Notes
-   The `data.json` file contains sensitive information (email, password, results). Keep it private.
-   To restart the entire process from scratch, simply delete the `data.json` file. The script will generate a new one.
