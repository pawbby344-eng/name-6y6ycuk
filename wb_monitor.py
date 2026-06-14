import os
import json
import asyncio
import time
from collections import deque
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Глобальные фильтры по умолчанию — используются, если категория их не переопределяет
DEFAULT_MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "0"))
DEFAULT_MIN_RATING = float(os.getenv("MIN_RATING", "0"))
DEFAULT_MAX_PRICE = int(os.getenv("MAX_PRICE", "0"))

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "120"))
RATE_LIMIT_BACKOFF = int(os.getenv("RATE_LIMIT_BACKOFF", "120"))

IMPERSONATE = os.getenv("IMPERSONATE", "chrome")

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
    "x-requested-with": "XMLHttpRequest",
}

CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "categories.json")

DEFAULT_WB_URL = (
    "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"
    "?ab_testing=false&appType=1&curr=rub&dest=-1690242&hide_dtype=15&hide_vflags=4294967296"
    "&lang=ru&locale=ru&query=menu_v3_9463+смартфон&resultset=catalog&sort=popular&spp=30"
    "&suppressSpellcheck=false&uclusters=0"
)


def load_categories():
    """Загружает список категорий для мониторинга из CATEGORIES_FILE.

    Если файла нет — создаёт его с одной категорией на основе старых
    переменных окружения (WB_URL/MIN_DISCOUNT/...), чтобы не потерять
    текущую настройку при переходе на мультикатегорийный режим.
    """
    if not os.path.exists(CATEGORIES_FILE):
        default = [
            {
                "name": "default",
                "url": os.getenv("WB_URL", DEFAULT_WB_URL),
                "min_discount": DEFAULT_MIN_DISCOUNT,
                "min_rating": DEFAULT_MIN_RATING,
                "max_price": DEFAULT_MAX_PRICE,
            }
        ]
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        print(f"Файл {CATEGORIES_FILE} не найден — создан с одной категорией по умолчанию.")
        return default

    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        categories = json.load(f)

    for cat in categories:
        cat.setdefault("min_discount", DEFAULT_MIN_DISCOUNT)
        cat.setdefault("min_rating", DEFAULT_MIN_RATING)
        cat.setdefault("max_price", DEFAULT_MAX_PRICE)

    return categories


def get_price_info(p):
    """Возвращает (цена, старая_цена, скидка_%) с учётом старого и нового формата API."""
    for size in p.get("sizes", []) or []:
        price = size.get("price") or {}
        product = price.get("product")
        if product:
            basic = price.get("basic") or product  # если basic нет — скидки нет
            sale_price = product / 100
            old_price = basic / 100
            discount = round((1 - product / basic) * 100) if basic and basic != product else 0
            return sale_price, old_price, discount

    sale_price = p.get("salePriceU", 0) / 100
    old_price = p.get("priceU", 0) / 100
    discount = p.get("sale", 0)
    return sale_price, old_price, discount


def passes_filters(p, min_discount, min_rating, max_price):
    price, _, discount = get_price_info(p)
    rating = p.get("reviewRating") or p.get("rating") or 0

    if discount < min_discount:
        return False
    if rating < min_rating:
        return False
    if max_price and price > max_price:
        return False
    return True


async def send_telegram(session, p, category_name):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — пропускаем отправку")
        return

    price, old_price, discount = get_price_info(p)
    rating = p.get("reviewRating") or p.get("rating") or "—"
    pid = p.get("id", "")
    link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

    text = (
        f"🆕 <b>{p.get('name', 'Без названия')}</b>\n"
        f"📂 Категория: {category_name}\n\n"
        f"💰 Цена: {price:.0f} ₽"
        + (f" (было {old_price:.0f} ₽, -{discount}%)\n" if discount else "\n")
        + f"⭐ Рейтинг: {rating}\n"
        f"🔗 <a href=\"{link}\">Открыть на WB</a>"
    )

    try:
        resp = await session.post(
            TELEGRAM_API,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"Telegram вернул ошибку {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"Не удалось отправить в Telegram: {e}")


async def monitor_category(session, category):
    name = category["name"]
    url = category["url"]
    min_discount = category["min_discount"]
    min_rating = category["min_rating"]
    max_price = category["max_price"]

    seen_ids = deque(maxlen=5000)
    seen_ids_set = set()
    is_first_run = True

    while True:
        try:
            response = await session.get(url, timeout=15, headers=HEADERS)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    print(f"[{name}] WB вернул не JSON (возможно капча): {response.text[:200]}")
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue

                products = data.get("products", [])

                if is_first_run:
                    for p in products:
                        pid = p.get("id")
                        if pid and pid not in seen_ids_set:
                            seen_ids.append(pid)
                            seen_ids_set.add(pid)
                    print(f"[{name}] Холодный старт: запомнили {len(seen_ids_set)} товаров, ждём новых...")
                    is_first_run = False
                else:
                    for p in products:
                        pid = p.get("id")
                        if not pid:
                            continue
                        if pid in seen_ids_set:
                            continue

                        # Добавляем в seen ТОЛЬКО если прошёл фильтр
                        # Товар без скидки сейчас — может появиться со скидкой позже
                        if passes_filters(p, min_discount, min_rating, max_price):
                            seen_ids.append(pid)
                            seen_ids_set.add(pid)

                            if len(seen_ids_set) > 5000:
                                seen_ids_set.clear()
                                seen_ids_set.update(seen_ids)

                            price, _, _ = get_price_info(p)
                            print(
                                f"[{name}][{time.strftime('%H:%M:%S')}] Подходит! "
                                f"{p.get('name', '???')} | {price:.0f} руб."
                            )
                            await send_telegram(session, p, name)

            elif response.status_code == 429:
                print(f"[{name}] Ошибка 429 (rate limit), ждём {RATE_LIMIT_BACKOFF} сек...")
                await asyncio.sleep(RATE_LIMIT_BACKOFF)
                continue

            else:
                print(f"[{name}] Ошибка {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"[{name}] Ошибка соединения: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def monitor():
    categories = load_categories()
    print(f"Запуск мониторинга: {len(categories)} категория(й)...")

    async with AsyncSession(impersonate=IMPERSONATE) as session:
        tasks = []
        for i, category in enumerate(categories):
            tasks.append(asyncio.create_task(monitor_category(session, category)))
            if i < len(categories) - 1:
                # Небольшой сдвиг старта, чтобы не бить WB всеми категориями одновременно
                await asyncio.sleep(2)

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(monitor())
