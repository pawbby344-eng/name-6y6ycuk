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
   - `WB_URL` — ссылка на `catalog`-API нужной категории (вкладка Network в браузере, запрос к `catalog.wb.ru`).
   - `MIN_DISCOUNT`, `MIN_RATING`, `MAX_PRICE` — фильтры.

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
