import httpx
import asyncio
import time

# Ссылка на категорию (это пример, нужно подставить свою из запроса)
# Чтобы получить свою: открой WB, выбери категорию, открой сеть (F12 -> Network),
# найди запрос к catalog.json, скопируй URL.
URL = "https://catalog.wb.ru/catalog/new/catalog.json?appType=1&sort=newly&cat=11893"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def monitor():
    seen_ids = set()
    print("Запуск мониторинга...")

    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(URL, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    products = data.get('data', {}).get('products', [])

                    for p in products:
                        pid = p['id']
                        if pid not in seen_ids:
                            print(f"[{time.strftime('%H:%M:%S')}] Новый товар! ID: {pid} | {p['name']} | {p['salePriceU'] / 100} руб.")
                            seen_ids.add(pid)

                    # Чистим память, если накопилось слишком много
                    if len(seen_ids) > 5000:
                        seen_ids.clear()

                else:
                    print(f"Ошибка {response.status_code}, ждем...")

            except Exception as e:
                print(f"Ошибка соединения: {e}")

            # Задержка 15 секунд, чтобы не словить бан
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(monitor())
