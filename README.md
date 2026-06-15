# name-6y6ycuk
gadget-webapp

## Wildberries Monitor (`wb_monitor.py`)

Монитор товаров на Wildberries с уведомлениями в Telegram. Два режима (`MODE` в `.env`):

- **`category`** — следит за категорией/поиском и шлёт алерт по новым товарам,
  прошедшим фильтры (скидка, рейтинг, цена).
- **`watchlist`** — следит за конкретными товарами по артикулу/ссылке и шлёт алерт
  при падении цены или достижении целевой цены.

### Настройка

1. Скопируй `.env.example` в `.env` и заполни общие поля:
   - `TELEGRAM_BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_CHAT_ID` — куда слать уведомления (узнать у [@userinfobot](https://t.me/userinfobot)).
   - `MODE` — `category` или `watchlist`.

2. Для `MODE=category`:
   - `MIN_DISCOUNT`, `MIN_RATING`, `MAX_PRICE` — фильтры по умолчанию (можно
     переопределить для каждой категории отдельно).
   - Настрой категории в `categories.json` (создаётся автоматически при первом
     запуске на основе `.env`/`WB_URL`, если файла нет). Можно добавить сколько
     угодно категорий — каждая мониторится параллельно со своим списком
     "уже виденных" товаров. Пример — `categories.example.json`:

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

     Ссылку `url` для каждой категории бери из DevTools (Network → XHR/Fetch).
     Поля `min_discount`/`min_rating`/`max_price` опциональны — если не указаны,
     берутся значения по умолчанию из `.env`.

3. Для `MODE=watchlist`:
   - Скопируй `watchlist.txt.example` в `watchlist.txt` и впиши товары —
     по одному на строку, формат `<ссылка-или-артикул> [= целевая_цена]`.

### Запуск локально

```bash
pip install -r requirements.txt
python wb_monitor.py
```

### Тесты

```bash
pip install -r requirements-dev.txt
pytest                      # fuzz-тесты парсеров и разбора watchlist
pytest --cov=wb_monitor     # с покрытием
```

### Запуск 24/7 на VPS (Docker)

```bash
docker compose up -d --build
```

Контейнер настроен с `restart: unless-stopped` — перезапустится сам после падения
или перезагрузки сервера.
