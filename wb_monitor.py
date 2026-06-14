import os
import html
import math
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


def _num(x):
    """Безопасно приводит значение к конечному float или возвращает None.

    WB обычно шлёт числа, но ответ может быть неполным/битым (None, строка,
    NaN, inf) — такие значения не должны ломать арифметику ниже.
    """
    if isinstance(x, bool):  # bool — подкласс int, но как цену не трактуем
        return None
    if isinstance(x, (int, float)):
        f = float(x)
    elif isinstance(x, str):
        try:
            f = float(x.strip())
        except ValueError:
            return None
    else:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def get_price_info(p):
    """Возвращает (цена, старая_цена, скидка_%) с учётом старого и нового формата API.

    Устойчива к мусору в ответе: всегда возвращает кортеж из трёх конечных чисел.
    """
    if not isinstance(p, dict):
        return 0.0, 0.0, 0

    sizes = p.get("sizes")
    if isinstance(sizes, list):
        for size in sizes:
            if not isinstance(size, dict):
                continue
            price = size.get("price")
            if not isinstance(price, dict):
                continue

            product = _num(price.get("product"))
            if product is None or product <= 0:
                continue

            basic = _num(price.get("basic"))
            if basic is None or basic <= 0:  # нет валидной базовой цены — скидки нет
                basic = product

            sale_price = product / 100
            old_price = basic / 100
            discount = round((1 - product / basic) * 100) if basic != product else 0
            if discount < 0:  # текущая цена выше «базовой» — это не скидка
                discount = 0
            return sale_price, old_price, discount

    # Fallback на старый формат (salePriceU/priceU/sale)
    sale_price = (_num(p.get("salePriceU")) or 0.0) / 100
    old_price = (_num(p.get("priceU")) or 0.0) / 100
    discount = _num(p.get("sale")) or 0
    discount = int(discount) if discount > 0 else 0
    return sale_price, old_price, discount


def passes_filters(p):
    if not isinstance(p, dict):
        return False

    price, _, discount = get_price_info(p)
    rating = _num(p.get("reviewRating")) or _num(p.get("rating")) or 0.0

    if discount < MIN_DISCOUNT:
        return False
    if rating < MIN_RATING:
        return False
    if MAX_PRICE and price > MAX_PRICE:
        return False
    return True


def _safe_pid(pid):
    """Артикул для подстановки в URL: только если это положительное целое
    (или строка из цифр), иначе пустая строка — чтобы не утащить мусор/инъекцию
    в href."""
    if isinstance(pid, bool):
        return ""
    if isinstance(pid, int) and pid > 0:
        return str(pid)
    if isinstance(pid, str) and pid.isdigit():
        return pid
    return ""


def build_message(p):
    """Собирает HTML-текст уведомления.

    ВСЕ значения из ответа WB экранируются через html.escape. Без этого символы
    & < > " ' в названии товара ломают parse_mode=HTML, Telegram отвечает
    400 Bad Request, и уведомление молча теряется. Названия на WB регулярно
    содержат такие символы, так что это не край, а норма.
    """
    if not isinstance(p, dict):
        p = {}

    price, old_price, discount = get_price_info(p)

    name = html.escape(str(p.get("name") or "Без названия"))
    rating = html.escape(str(p.get("reviewRating") or p.get("rating") or "—"))
    link = f"https://www.wildberries.ru/catalog/{_safe_pid(p.get('id'))}/detail.aspx"

    return (
        f"🆕 <b>{name}</b>\n\n"
        f"💰 Цена: {price:.0f} ₽"
        + (f" (было {old_price:.0f} ₽, -{discount}%)\n" if discount else "\n")
        + f"⭐ Рейтинг: {rating}\n"
        f"🔗 <a href=\"{link}\">Открыть на WB</a>"
    )


async def send_telegram(session, p):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — пропускаем отправку")
        return

    text = build_message(p)

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
