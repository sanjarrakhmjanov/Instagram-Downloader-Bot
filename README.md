# Instagram Downloader Telegram Bot

Production-ready Telegram bot (`aiogram 3.x`) for Instagram links only:
- Reels (video)
- Posts (video/photo)
- MP3 extraction from video posts/reels

## Features

- Instagram link detection
- Output options: `VIDEO` or `MP3`
- Auto-processing for image posts (no format picker)
- Redis queue + async worker
- PostgreSQL history/favorites
- Multi-language UI (`uz/ru/en`)
- Docker-ready deployment

## Commands

- `/start`
- `/help`
- `/settings`
- `/history`
- `/favorites`
- `/privacy`
- `/cancel`
- `/admin` (admins only)

## Run (Docker)

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f bot worker
```

## Run (Local)

1. Start PostgreSQL + Redis.
2. Fill `.env`.
3. Run bot:
```bash
python -m bot.main
```
4. Run worker in another terminal:
```bash
python -m bot.worker
```

## Notes

- Bot supports only public Instagram content.
- Private/restricted posts may fail due to source-side access limits.
