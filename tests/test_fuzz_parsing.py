"""
Fuzz-тесты для парсеров WB-ответа.

get_price_info() и passes_filters() получают на вход сырой словарь товара из
JSON Wildberries — данные, которые мы не контролируем. Цель фаззинга: убедиться,
что на любом мусоре (неполные/битые/подменённые поля) функции не падают
с необработанным исключением, а возвращают корректные типы.

Запуск:  pytest tests/test_fuzz_parsing.py -q
"""
import os
import re
import sys
import math

import pytest
from hypothesis import given, settings, example, strategies as st

# Импортируем тестируемый модуль из корня репозитория
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wb_monitor as wb  # noqa: E402


@pytest.fixture(autouse=True)
def fixed_thresholds(monkeypatch):
    """Фиксируем пороги фильтра, чтобы тесты не зависели от .env конкретной
    машины (там может быть MIN_DISCOUNT=70 и т.п.). Тест проверяет поведение
    функций, а не локальную конфигурацию."""
    monkeypatch.setattr(wb, "MIN_DISCOUNT", 0)
    monkeypatch.setattr(wb, "MIN_RATING", 0.0)
    monkeypatch.setattr(wb, "MAX_PRICE", 0)


# --- Стратегии генерации «товара» --------------------------------------------

# Скаляры, включая заведомо «ядовитые» значения
scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10**9, max_value=10**9),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=8),
)

# Словарь цены: продаваемая/базовая может отсутствовать, быть нулём, строкой, NaN
price_dict = st.dictionaries(
    keys=st.one_of(st.sampled_from(["product", "basic", "total", "logistic"]), st.text(max_size=4)),
    values=scalars,
    max_size=4,
)

# Элемент sizes: иногда корректный dict, иногда — мусор (строка/число/None)
size_entry = st.one_of(
    scalars,
    st.dictionaries(
        keys=st.one_of(st.sampled_from(["price", "name", "optionId"]), st.text(max_size=4)),
        values=st.one_of(scalars, price_dict),
        max_size=4,
    ),
)

# Сам товар: sizes может быть списком, мусором или отсутствовать;
# rating/price-поля — любого типа
product = st.dictionaries(
    keys=st.one_of(
        st.sampled_from(
            ["id", "name", "sizes", "reviewRating", "rating", "salePriceU", "priceU", "sale"]
        ),
        st.text(max_size=4),
    ),
    values=st.one_of(
        scalars,
        st.lists(size_entry, max_size=4),
    ),
    max_size=8,
)


# --- Свойства ----------------------------------------------------------------

# Пины конкретных входов, которые РАНЬШЕ роняли парсер (регресс-защита,
# чтобы случайный сид Hypothesis их не «потерял»)
@example({"salePriceU": None})          # None / 100
@example({"priceU": None})              # None / 100
@example({"sizes": [{"price": {"product": "0", "basic": None}}]})  # str / 100
@example({"sizes": [{"price": {"product": 1, "basic": "0"}}]})     # str / 100
@example({"sizes": "не-список"})        # итерирование по строке
@example({"sizes": ["мусор", 123, None]})  # не-dict элементы
@example(None)                          # сам товар — не dict
@example("вообще не словарь")
@settings(max_examples=500, deadline=None)
@given(product)
def test_get_price_info_never_crashes(p):
    out = wb.get_price_info(p)
    # Контракт: всегда кортеж из трёх чисел
    assert isinstance(out, tuple) and len(out) == 3, out
    sale, old, discount = out
    for v in (sale, old, discount):
        assert isinstance(v, (int, float)), out
        # NaN/inf не должны протекать в выходные данные
        assert not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))), out


@example(None)               # не-dict вход → False, без краша
@example(["мусор"])
@settings(max_examples=500, deadline=None)
@given(product)
def test_passes_filters_returns_bool(p):
    out = wb.passes_filters(p)
    assert isinstance(out, bool), out


# Прицельно: только валидная по форме структура sizes, но с «грязными» ценами —
# чтобы поймать деление на ноль и арифметику со строками в discount
well_formed = st.fixed_dictionaries({
    "id": st.integers(),
    "name": st.text(max_size=10),
    "reviewRating": st.one_of(st.floats(allow_nan=True), st.text(max_size=3), st.none()),
    "sizes": st.lists(
        st.fixed_dictionaries({
            "price": st.fixed_dictionaries({
                "product": st.one_of(st.integers(-5, 5), st.none(), st.text(max_size=3)),
                "basic": st.one_of(st.integers(-5, 5), st.none(), st.text(max_size=3)),
            })
        }),
        max_size=3,
    ),
})


@settings(max_examples=500, deadline=None)
@given(well_formed)
def test_realistic_shape_no_crash(p):
    sale, old, discount = wb.get_price_info(p)
    assert isinstance(wb.passes_filters(p), bool)


# --- build_message: защита от поломки Telegram HTML ---------------------------

# Разрешённая разметка, которую функция добавляет сама
_ALLOWED_TAGS = re.compile(r'</?b>|<a href="[^"<>]*">|</a>')


def _strip_allowed(text):
    """Убирает легальные теги-обёртки, чтобы проверить, что в пользовательских
    данных не осталось неэкранированных < > (которые сломают parse_mode=HTML)."""
    return _ALLOWED_TAGS.sub("", text)


@example({"name": 'Чехол <iPhone> "Pro" & стекло', "id": 123})  # реальный кейс с WB
@example({"name": None, "id": None})
@example({"name": "</b><script>", "id": "0; DROP"})
@example(None)               # не-dict вход не должен ронять сборку
@settings(max_examples=500, deadline=None)
@given(product)
def test_build_message_is_telegram_safe(p):
    text = wb.build_message(p)
    assert isinstance(text, str)

    # После удаления легальных тегов не должно остаться сырых < или >
    residual = _strip_allowed(text)
    assert "<" not in residual and ">" not in residual, residual

    # Каждый & должен быть частью HTML-сущности (&amp; &lt; &gt; &quot; &#..;),
    # иначе Telegram тоже отвергнет сообщение
    deentitized = re.sub(r"&(amp|lt|gt|quot|#x?[0-9a-fA-F]+);", "", residual)
    assert "&" not in deentitized, residual

    # В href не должно быть кавычек/угловых скобок (иначе атрибут «разорвётся»)
    for href in re.findall(r'<a href="([^"]*)"', text):
        assert "<" not in href and ">" not in href, href
