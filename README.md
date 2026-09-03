# Shub DMs Telegram Bot

This is the Railway/local version of the uploaded bot. The Telegram menus and
bot flows are kept in `bot.py`; MongoDB was replaced with SQLite storage in
`storage.py`.

## Local run

Install the dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
python telegram_bot/bot.py
```

The bot needs these environment variables:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_BOT_TOKEN`
- `GMAIL_USER`
- `GMAIL_PASS`

Optional:

- `ADMINS` — comma-separated Telegram user IDs
- `SQLITE_PATH` — defaults to `data/shub_dms.sqlite3`

## Railway run

Railway can deploy this repository with the included `railway.json` or
`Procfile`. Add the required variables in the Railway Variables tab, then
deploy.

Attach a Railway Volume mounted at `/data` if the SQLite database must survive
restarts and redeploys. Set `SQLITE_PATH=/data/shub_dms.sqlite3`.