# NSE Notifier Setup

## 1. Telegram bot
- Telegram → `@BotFather` → `/newbot` → get TOKEN
- Send bot any msg → visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → grab `chat.id`

## 2. Repo
- Create new **GitHub repo** (private is fine)
- Upload these files, keeping folder structure:
  - `nse_bot.py`
  - `requirements.txt`
  - `.github/workflows/nse_poll.yml`

## 3. Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `TELEGRAM_TOKEN` = your bot token
- `TELEGRAM_CHAT_ID` = your chat id

## 4. Enable + test
- Go to Actions tab → enable workflows
- Run "NSE Poll" manually once (workflow_dispatch button) → check Telegram gets msgs
- After that it runs automatically every 30 min

## Notes
- First run will notify EVERYTHING currently listed (backlog dump) — expected, ignore it.
- `state.json` auto-commits after each run to remember what's already sent.
- NSE occasionally tweaks API paths/anti-bot checks → if it goes quiet, endpoints in `nse_bot.py` (`ENDPOINTS` dict) may need URL update. Ping me, I'll patch.
- Covers: corp announcements/filings, corp actions, board meetings, bulk deals, block deals. M&A shows up inside corp announcements (no separate NSE feed for it).
