# name-6y6ycuk
gadget-webapp

## Wildberries Monitor (`wb_monitor.py`)

Скрипт следит за категорией/поиском на Wildberries и присылает уведомления в Telegram
только по товарам, прошедшим фильтры (скидка, рейтинг, цена).

### Настройка

1. Скопируй `.env.example` в `.env` и заполни:
   - `TELEGRAM_BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_CHAT_ID` — куда слать уведомления (узнать у [@userinfobot](https://t.me/userinfobot)).
   - `MIN_DISCOUNT`, `MIN_RATING`, `MAX_PRICE` — фильтры по умолчанию (можно переопределить
     для каждой категории отдельно).

2. Настрой категории в `categories.json` (создаётся автоматически при первом запуске
   на основе `.env`, если файла нет). Можно добавить сколько угодно категорий —
   каждая мониторится параллельно со своим списком "уже виденных" товаров:

   ```json
   [
     {
       "name": "Смартфоны",
       "url": "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search?...",
       "min_discount": 70,
       "min_rating": 4.5,
       "max_price": 0
     },
     {
       "name": "Конструкторы LEGO",
       "url": "https://search.wb.ru/exactmatch/ru/common/v18/search?...",
       "min_discount": 50,
       "min_rating": 4.0,
       "max_price": 5000
     }
   ]
   ```

   Ссылку `url` для каждой категории бери из DevTools (Network → XHR/Fetch),
   как описано выше. Поля `min_discount`/`min_rating`/`max_price` опциональны —
   если не указаны, берутся значения по умолчанию из `.env`.

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
