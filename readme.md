# autologin + api_server — README

> Use this only on websites and systems you own or have written permission to test.

## Purpose
`autologin.py` shows a simple, local demo of an automated login flow for your own site.  
It asks a local API for a challenge token, runs a browser, and can send a session value to a local URL you control.

## Files
- `autologin.py` — main script.
- `api_server.py` — small local API that returns a token.
- `emails.txt` — account list. One per line: `email|password`.
- `proxies.txt` — proxies list. One per line: `host:port`.
- `data.json` — progress file. Created automatically.

## Requirements
- Python 3.10+
- Pip packages from `requirements.txt`
- Playwright browsers installed: `python -m playwright install`
- Optional: Tor running locally if you want to route traffic through it

## Install
```bash
pip install -r requirements.txt
python -m playwright install
```

## Start the local API
Open a terminal and run:
```bash
python api_server.py
```
Default address: `http://localhost:8080`

### API endpoints (for your own testing only)
- `GET /turnstile?url=...&sitekey=...` → returns a `task_id`
- `GET /result?id=<task_id>` → returns the token status or value

## Prepare input files
Create these next to `autologin.py`:

**emails.txt**
```
test1@example.com|example-pass-1
test2@example.com|example-pass-2
```

**proxies.txt**
```
127.0.0.1:3128
203.0.113.10:8080
```

## Configure (OPTIONAL)
Open `autologin.py` and adjust:
- `POST_URL` — where to send the session value (default: `http://127.0.0.1:80/user`).
- Proxy and (optional) Tor settings if you use them.
- Any site‑specific selectors you added for your own test site.

## Run
```bash
python autologin.py
```

## What happens
- The script reads `emails.txt` and `proxies.txt`.
- It asks the local API for a token.
- It launches a browser and attempts a login on your **own** test site.
- It looks for a session cookie or value you configured.
- It posts that value to `POST_URL` and writes results to `data.json`.

## Outputs
- `data.json` keeps run status and results.
- Your local receiver at `POST_URL` gets a small JSON payload with the session value you configured.

## Troubleshooting
- **API not reachable**: Check `api_server.py` is running on port 8080.
- **Timeouts**: Verify your test URL and `sitekey` are correct for your own setup.
- **Proxy errors**: Make sure entries in `proxies.txt` are valid and live.

## Notes
- Keep `data.json` private because it contains account information.
