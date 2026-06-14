import os
import asyncio
import time
from collections import deque
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv

ENV_TEMPLATE = """WB_URL=https://catalog.wb.ru/catalog/new/catalog.json?appType=1&sort=newly&cat=11893
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MIN_DISCOUNT=0
MIN_RATING=0
MAX_PRICE=0
POLL_INTERVAL=15
RATE_LIMIT_BACKOFF=60
"""

if not os.path.exists(".env"):
    with open(".env", "w", encoding="utf-8") as f:
        f.write(ENV_TEMPLATE)
    print("Файл .env не найден — создан новый с пустыми значениями. Заполни TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.")

load_dotenv()

# Ссылка на API-запрос WB (берётся из DevTools -> Network на странице поиска/категории).
WB_URL = os.getenv(
    "WB_URL",
    "https://catalog.wb.ru/catalog/new/catalog.json?appType=1&sort=newly&cat=11893",
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ВНИМАНИЕ: TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы в .env — уведомления отправляться не будут.")

# Максимум запомненных ID товаров (для отсева повторных уведомлений)
SEEN_LIMIT = 5000

# Фильтры — товар должен пройти все условия, чтобы попасть в уведомление
MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "0"))   # минимальная скидка, %
MIN_RATING = float(os.getenv("MIN_RATING", "0"))     # минимальный рейтинг товара
MAX_PRICE = int(os.getenv("MAX_PRICE", "0"))         # максимальная цена, руб. (0 = без ограничения)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))      # задержка между запросами, сек.
RATE_LIMIT_BACKOFF = int(os.getenv("RATE_LIMIT_BACKOFF", "60"))  # пауза после ошибки 429, сек.

# Под каким браузером "притворяемся" (нужно, чтобы WB не блокировал бота).
IMPERSONATE = os.getenv("IMPERSONATE", "chrome")


def get_price_info(p):
    """Возвращает (цена, старая_цена, скидка_%) с учётом старого и нового формата API."""
    # Новый формат (v18): цена лежит в sizes[].price
    for size in p.get("sizes", []) or []:
        price = size.get("price") or {}
        product = price.get("product")
        if product:
            basic = price.get("basic", product)
            sale_price = product / 100
            old_price = basic / 100
            discount = round((1 - product / basic) * 100) if basic else 0
            return sale_price, old_price, discount

    # Старый формат: salePriceU / priceU / sale
    sale_price = p.get("salePriceU", 0) / 100
    old_price = p.get("priceU", 0) / 100
    discount = p.get("sale", 0)
    return sale_price, old_price, discount


def passes_filters(p):
    price, _, discount = get_price_info(p)
    rating = p.get("reviewRating") or p.get("rating") or 0

    if discount < MIN_DISCOUNT:
        return False
    if rating < MIN_RATING:
        return False
    if MAX_PRICE and price > MAX_PRICE:
        return False
    return True


async def send_telegram(session, p):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    price, old_price, discount = get_price_info(p)
    rating = p.get("reviewRating") or p.get("rating") or "—"
    link = f"https://www.wildberries.ru/catalog/{p['id']}/detail.aspx"

    text = (
        f"🆕 <b>{p['name']}</b>\n\n"
        f"💰 Цена: {price:.0f} ₽"
        + (f" (было {old_price:.0f} ₽, -{discount}%)\n" if discount else "\n")
        + f"⭐ Рейтинг: {rating}\n"
        f"🔗 <a href=\"{link}\">Открыть на WB</a>"
    )

    try:
        await session.post(
            TELEGRAM_API,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"Не удалось отправить в Telegram: {e}")


def mark_seen(pid, seen_ids, seen_ids_set):
    """Запоминает ID товара, не теряя старые записи при превышении лимита."""
    if pid in seen_ids_set:
        return
    seen_ids.append(pid)
    seen_ids_set.add(pid)
    if len(seen_ids_set) > SEEN_LIMIT:
        oldest = seen_ids.popleft()
        seen_ids_set.discard(oldest)


async def monitor():
    seen_ids = deque()
    seen_ids_set = set()
    cold_start = True
    print("Запуск мониторинга...")

    async with AsyncSession(impersonate=IMPERSONATE) as session:
        while True:
            try:
                response = await session.get(WB_URL, timeout=15)

                if response.status_code == 429:
                    print(f"Ошибка 429 (слишком много запросов), ждём {RATE_LIMIT_BACKOFF} сек...")
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue

                if response.status_code != 200:
                    print(f"Ошибка {response.status_code}, ждем...")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                try:
                    data = response.json()
                except ValueError:
                    print(
                        f"WB вернул не JSON (возможна капча/блокировка), "
                        f"ждём {RATE_LIMIT_BACKOFF} сек..."
                    )
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue

                products = data.get("data", {}).get("products", [])

                if cold_start:
                    for p in products:
                        mark_seen(p["id"], seen_ids, seen_ids_set)
                    print(f"Холодный старт: запомнили {len(seen_ids_set)} товаров")
                    cold_start = False
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                for p in products:
                    pid = p["id"]
                    if pid in seen_ids_set:
                        continue
                    mark_seen(pid, seen_ids, seen_ids_set)

                    if passes_filters(p):
                        price, _, _ = get_price_info(p)
                        print(
                            f"[{time.strftime('%H:%M:%S')}] Подходит! "
                            f"{p['name']} | {price:.0f} руб."
                        )
                        await send_telegram(session, p)

            except Exception as e:
                print(f"Ошибка соединения: {e}")

            # Задержка, чтобы не словить бан
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor())
