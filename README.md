# name-6y6ycuk
gadget-webapp

## Wildberries Monitor (`wb_monitor.py`)

Скрипт следит за категорией/поиском на Wildberries и присылает уведомления в Telegram
только по товарам, прошедшим фильтры (скидка, рейтинг, цена).

### Настройка

1. Скопируй `.env.example` в `.env` и заполни:
   - `WB_URL` — ссылка на `catalog.json` нужной категории (берётся из вкладки Network в браузере).
   - `TELEGRAM_BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_CHAT_ID` — куда слать уведомления (узнать у [@userinfobot](https://t.me/userinfobot)).
   - `MIN_DISCOUNT`, `MIN_RATING`, `MAX_PRICE` — фильтры, чтобы в чат падали только
     действительно интересные находки.

### Запуск локально

```bash
pip install -r requirements.txt
python wb_monitor.py
```

### Запуск 24/7 на VPS (Docker)

```bash
docker compose up -d --build
```

Контейнер настроен с `restart: unless-stopped` — перезапустится сам после падения
или перезагрузки сервера.
