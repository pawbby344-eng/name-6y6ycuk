# ЧИСТЫЙ КОНСТРУКТИВ МАГАЗИНА (7х9 м)
# Без стеллажей. Только стены, проемы и Ресепшн.

scale = 100
width_m = 7.0
depth_m = 9.0
width_px = width_m * scale
depth_px = depth_m * scale

# --- КООРДИНАТЫ (X - от левой стены, Y - от входа) ---

# Вход (начинается от левого угла, ширина 1м)
door_x = 0.0
door_width = 1.0

# Окно и правый простенок (1.2м)
window_x = door_x + door_width
window_width = 4.8  # (7м - 1м дверь - 1.2м простенок)
wall_x = window_x + window_width

# Колонна (0.9x0.9 м, центр зала)
col_x = 2.5
col_y = 4.5
col_size = 0.9

# Ресепшн (отступ 4м от входа, вдоль правой стены)
desk_y = 4.0
desk_len = 2.8
desk_width = 0.6
desk_x = width_m - desk_width  # У правой стены

# Задняя стена (справа налево)
# 0.8м простенок + 0.9м белая дверь + 1.3м витрина + 0.9м фиолетовая дверь
wall_right_gap = 0.8
door_white_w = 0.9
display_w = 1.3
door_purple_w = 0.9

door_white_x = width_m - wall_right_gap - door_white_w
display_x = door_white_x - display_w
door_purple_x = display_x - door_purple_w

# --- ГЕНЕРАЦИЯ SVG ---

svg = f'''<svg width="{width_px + 150}" height="{depth_px + 140}" xmlns="http://www.w3.org/2000/svg" style="background-color: #f4f4f4; font-family: Arial, sans-serif;">

    <!-- Контур зала -->
    <rect x="40" y="40" width="{width_px}" height="{depth_px}" fill="#ffffff" stroke="#2c3e50" stroke-width="4"/>

    <!-- Колонна -->
    <rect x="{40 + col_x*scale}" y="{40 + col_y*scale}" width="{col_size*scale}" height="{col_size*scale}" fill="#95a5a6" stroke="#2c3e50" stroke-width="2"/>
    <text x="{40 + col_x*scale + 15}" y="{40 + col_y*scale + 50}" font-size="16" font-weight="bold" fill="#fff">Колонна</text>
    <text x="{40 + col_x*scale + 20}" y="{40 + col_y*scale + 70}" font-size="12" fill="#fff">90x90</text>

    <!-- Входная дверь -->
    <rect x="{40 + door_x*scale}" y="{40 + depth_px}" width="{door_width*scale}" height="12" fill="#2ecc71" stroke="#27ae60" stroke-width="2"/>
    <line x1="{40 + door_x*scale + door_width*scale/2}" y1="{40 + depth_px}" x2="{40 + door_x*scale + door_width*scale/2}" y2="{40 + depth_px + 12}" stroke="#27ae60" stroke-width="2" stroke-dasharray="4,2"/>
    <text x="{40 + door_x*scale + 20}" y="{40 + depth_px + 40}" font-size="18" font-weight="bold" fill="#2c3e50">ВХОД (1м)</text>

    <!-- Окно -->
    <rect x="{40 + window_x*scale}" y="{40 + depth_px - 4}" width="{window_width*scale}" height="8" fill="#e0f7fa" stroke="#00838f" stroke-width="2" stroke-dasharray="5,3"/>
    <text x="{40 + window_x*scale + 100}" y="{40 + depth_px + 40}" font-size="16" font-weight="bold" fill="#2c3e50">ОКНО (4.8м)</text>

    <!-- Правый простенок -->
    <rect x="{40 + wall_x*scale}" y="{40 + depth_px - 8}" width="{(width_m - wall_x)*scale}" height="16" fill="#bdc3c7" stroke="#2c3e50" stroke-width="2"/>
    <text x="{40 + wall_x*scale + 20}" y="{40 + depth_px + 40}" font-size="14" fill="#2c3e50">ПРОСТЕНОК (1.2м)</text>

    <!-- Ресепшн -->
    <rect x="{40 + desk_x*scale}" y="{40 + desk_y*scale}" width="{desk_width*scale}" height="{desk_len*scale}" fill="#f8c471" stroke="#d35400" stroke-width="2"/>
    <text x="{40 + desk_x*scale - 80}" y="{40 + desk_y*scale + 40}" font-size="16" font-weight="bold" fill="#2c3e50">Ресепшн (Касса)</text>
    <text x="{40 + desk_x*scale - 60}" y="{40 + desk_y*scale + 60}" font-size="12" fill="#2c3e50">(Начало от входа 4м)</text>

    <!-- Задняя стена -->
    <!-- Простенок справа -->
    <rect x="{40 + (width_m - wall_right_gap)*scale}" y="{40}" width="{wall_right_gap*scale}" height="12" fill="#bdc3c7" stroke="#2c3e50" stroke-width="2"/>
    <text x="{40 + (width_m - wall_right_gap)*scale + 10}" y="{40 + 30}" font-size="12" fill="#2c3e50">Простенок 0.8м</text>

    <!-- Белая дверь (Тех. кабинет) -->
    <rect x="{40 + door_white_x*scale}" y="{40}" width="{door_white_w*scale}" height="12" fill="#ecf0f1" stroke="#95a5a6" stroke-width="2"/>
    <text x="{40 + door_white_x*scale - 10}" y="{40 + 30}" font-size="14" font-weight="bold" fill="#2c3e50">Тех. кабинет</text>

    <!-- Витрина между дверьми -->
    <rect x="{40 + display_x*scale}" y="{40}" width="{display_w*scale}" height="12" fill="#d5f5e3" stroke="#27ae60" stroke-width="2"/>
    <text x="{40 + display_x*scale + 10}" y="{40 + 30}" font-size="12" fill="#2c3e50">Витрина 1.3м</text>

    <!-- Фиолетовая дверь (Склад) -->
    <rect x="{40 + door_purple_x*scale}" y="{40}" width="{door_purple_w*scale}" height="12" fill="#d2b4de" stroke="#8e44ad" stroke-width="2"/>
    <text x="{40 + door_purple_x*scale - 10}" y="{40 + 30}" font-size="14" font-weight="bold" fill="#2c3e50">Склад</text>

    <!-- Размеры стен -->
    <text x="{40 + width_px//2 - 20}" y="{40 + depth_px + 80}" font-size="18" font-weight="bold" fill="#2c3e50">7 м</text>
    <text x="{40 + width_px + 50}" y="{40 + depth_px//2 + 5}" font-size="18" font-weight="bold" fill="#2c3e50" transform="rotate(90, {40 + width_px + 50}, {40 + depth_px//2 + 5})">9 м</text>
</svg>'''

print(svg)
