"""
NSE update notifier -> Telegram.
Polls NSE JSON endpoints, diffs vs last-seen state, sends new items to Telegram.
Run every 30 min via GitHub Actions (see .github/workflows/nse_poll.yml).
"""

import json
import os
import time
import requests

STATE_FILE = "state.json"
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}

# endpoint -> (label, id_fn, msg_fn)
ENDPOINTS = {
    "corporate-announcements": {
        "url": f"{BASE}/api/corporate-announcements?index=equities",
        "label": "\U0001F4E2 Corporate Announcement",
        "id_fn": lambda x: f"{x.get('symbol')}|{x.get('desc')}|{x.get('an_dt')}",
        "msg_fn": lambda x: (
            f"<b>\U0001F4E2 Corporate Announcement</b>\n"
            f"<b>{x.get('sm_name') or x.get('symbol')}</b> ({x.get('symbol')})\n"
            f"Subject: {x.get('desc') or x.get('subject','N/A')}\n"
            f"Details: {(x.get('attchmntText') or 'N/A')[:300]}\n"
            f"Date: {x.get('an_dt')}\n"
            f"Doc: {x.get('attchmntFile') or 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'}"
        ),
    },
    "corporate-actions": {
        "url": f"{BASE}/api/corporates-corporateActions?index=equities",
        "label": "\u2699\uFE0F Corporate Action",
        "id_fn": lambda x: f"{x.get('symbol')}|{x.get('subject')}|{x.get('exDate')}",
        "msg_fn": lambda x: (
            f"<b>\u2699\uFE0F Corporate Action</b>\n"
            f"<b>{x.get('comp') or x.get('symbol')}</b> ({x.get('symbol')})\n"
            f"Action: {x.get('subject')}\n"
            f"Series: {x.get('series','N/A')}   Face Value: {x.get('faceVal','N/A')}\n"
            f"Ex-Date: {x.get('exDate','N/A')}   Record Date: {x.get('recDate','N/A')}\n"
            f"Doc: https://www.nseindia.com/companies-listing/corporate-filings-actions"
        ),
    },
    "board-meetings": {
        "url": f"{BASE}/api/corporate-board-meetings?index=equities",
        "label": "\U0001F4C5 Board Meeting",
        "id_fn": lambda x: f"{x.get('bm_symbol')}|{x.get('bm_purpose')}|{x.get('bm_date')}|{x.get('bm_desc')}",
        "msg_fn": lambda x: (
            f"<b>\U0001F4C5 Board Meeting</b>\n"
            f"<b>{x.get('sm_name') or x.get('bm_symbol')}</b> ({x.get('bm_symbol')})\n"
            f"Purpose: {x.get('bm_purpose')}\n"
            f"Details: {(x.get('bm_desc') or 'N/A')[:300]}\n"
            f"Meeting Date: {x.get('bm_date')}\n"
            f"Doc: {x.get('attachment') or 'https://www.nseindia.com/companies-listing/corporate-filings-board-meetings'}"
        ),
    },
    "bulk-deals": {
        "url": f"{BASE}/api/historicalOR/bulk-deals",
        "label": "\U0001F4CA Bulk Deal",
        "id_fn": lambda x: f"{x.get('BD_SYMBOL')}|{x.get('BD_CLIENT_NAME')}|{x.get('BD_DT_DATE')}|{x.get('BD_QTY_TRD')}",
        "msg_fn": lambda x: (
            f"<b>\U0001F4CA Bulk Deal</b>\n"
            f"Symbol: <b>{x.get('BD_SYMBOL')}</b>\n"
            f"Client: {x.get('BD_CLIENT_NAME')}\n"
            f"Side: {x.get('BD_BUY_SELL')}   Qty: {x.get('BD_QTY_TRD')}   Price: {x.get('BD_TP_WATP')}\n"
            f"Date: {x.get('BD_DT_DATE')}\n"
            f"Doc: https://www.nseindia.com/report-detail/display-bulk-and-block-deals"
        ),
    },
    "block-deals": {
        "url": f"{BASE}/api/historicalOR/block-deals",
        "label": "\U0001F4CA Block Deal",
        "id_fn": lambda x: f"{x.get('BD_SYMBOL')}|{x.get('BD_CLIENT_NAME')}|{x.get('BD_DT_DATE')}|{x.get('BD_QTY_TRD')}",
        "msg_fn": lambda x: (
            f"<b>\U0001F4CA Block Deal</b>\n"
            f"Symbol: <b>{x.get('BD_SYMBOL')}</b>\n"
            f"Client: {x.get('BD_CLIENT_NAME')}\n"
            f"Qty: {x.get('BD_QTY_TRD')}   Price: {x.get('BD_TP_WATP')}\n"
            f"Date: {x.get('BD_DT_DATE')}\n"
            f"Doc: https://www.nseindia.com/report-detail/display-bulk-and-block-deals"
        ),
    },
}


def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    # NSE requires a warm-up hit to set cookies before API calls work
    s.get(BASE, timeout=10)
    time.sleep(1)
    s.get(f"{BASE}/companies-listing/corporate-filings-announcements", timeout=10)
    return s


def fetch_items(session, url):
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            data = data.get("data", data.get("rows", []))
        return data or []
    except Exception as e:
        print(f"WARN fetch failed {url}: {e}")
        return []


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=10)
    if resp.status_code != 200:
        print(f"WARN telegram send failed: {resp.text}")


def main():
    state = load_state()
    session = get_session()
    new_count = 0

    for key, cfg in ENDPOINTS.items():
        seen_ids = set(state.get(key, []))
        items = fetch_items(session, cfg["url"])
        current_ids = []

        for item in items:
            try:
                iid = cfg["id_fn"](item)
            except Exception:
                continue
            if iid in current_ids:
                continue  # dupe within same fetch, skip
            current_ids.append(iid)
            if iid not in seen_ids:
                msg = cfg["msg_fn"](item)
                send_telegram(msg)
                seen_ids.add(iid)  # mark sent NOW, not after loop
                new_count += 1
                time.sleep(0.5)  # avoid telegram rate limit

        # keep last 500 ids per endpoint so file doesn't grow forever
        state[key] = current_ids[:500] if current_ids else list(seen_ids)

    save_state(state)
    print(f"Done. {new_count} new item(s) sent.")


if __name__ == "__main__":
    main()
