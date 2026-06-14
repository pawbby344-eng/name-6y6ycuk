import os
import asyncio
import time
from collections import deque
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv

load_dotenv()

WB_URL = os.getenv(
    "WB_URL",
    "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search?ab_testing=false&appType=1&curr=rub&dest=-1690242&hide_dtype=15&hide_vflags=4294967296&lang=ru&locale=ru&query=menu_v3_9463+смартфон&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false&uclusters=0",
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "0"))
MIN_RATING = float(os.getenv("MIN_RATING", "0"))
MAX_PRICE = int(os.getenv("MAX_PRICE", "0"))

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))       # было 15 — слишком агрессивно
RATE_LIMIT_BACKOFF = int(os.getenv("RATE_LIMIT_BACKOFF", "120"))  # было 60

IMPERSONATE = os.getenv("IMPERSONATE", "chrome")


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
        print("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — пропускаем отправку")
        return

    price, old_price, discount = get_price_info(p)
    rating = p.get("reviewRating") or p.get("rating") or "—"
    pid = p.get("id", "")
    link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

    text = (
        f"🆕 <b>{p.get('name', 'Без названия')}</b>\n\n"
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


async def monitor():
    # deque с maxlen — автоматически выбрасывает старые ID, не надо делать clear()
    seen_ids = deque(maxlen=5000)
    seen_ids_set = set()  # для быстрого поиска O(1)

    print("Запуск мониторинга...")
    is_first_run = True  # первый прогон — «холодный», только наполняем seen_ids

    async with AsyncSession(impersonate=IMPERSONATE) as session:
        while True:
            try:
                response = await session.get(WB_URL, timeout=15)

                if response.status_code == 200:
                    # Защита от HTML-ответа (капча, редирект)
                    try:
                        data = response.json()
                    except Exception:
                        print(f"WB вернул не JSON (возможно капча): {response.text[:200]}")
                        await asyncio.sleep(RATE_LIMIT_BACKOFF)
                        continue

                    products = data.get("products", [])

                    if is_first_run:
                        # Первый запуск — просто запоминаем все ID, ничего не шлём
                        for p in products:
                            pid = p.get("id")
                            if pid and pid not in seen_ids_set:
                                seen_ids.append(pid)
                                seen_ids_set.add(pid)
                        print(f"Холодный старт: запомнили {len(seen_ids_set)} товаров, ждём новых...")
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
                            if passes_filters(p):
                                seen_ids.append(pid)
                                seen_ids_set.add(pid)

                                # Синхронизируем set с deque при переполнении
                                if len(seen_ids_set) > 5000:
                                    seen_ids_set.clear()
                                    seen_ids_set.update(seen_ids)

                                price, _, _ = get_price_info(p)
                                print(
                                    f"[{time.strftime('%H:%M:%S')}] Подходит! "
                                    f"{p.get('name', '???')} | {price:.0f} руб."
                                )
                                await send_telegram(session, p)

                elif response.status_code == 429:
                    print(f"Ошибка 429 (rate limit), ждём {RATE_LIMIT_BACKOFF} сек...")
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue

                else:
                    print(f"Ошибка {response.status_code}: {response.text[:200]}")

            except Exception as e:
                print(f"Ошибка соединения: {e}")

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor())
