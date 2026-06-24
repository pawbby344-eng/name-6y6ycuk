# ИНЖЕНЕРНЫЙ ПЛАН (черно-белый, с размерами)
scale = 100
width_m = 7.0
depth_m = 9.0
width_px = width_m * scale
depth_px = depth_m * scale

# Координаты (метры)
door_x, door_w = 0.0, 1.0
win_x, win_w = 1.0, 4.8
wall_x = 5.8  # (1.0 + 4.8) -> до правого простенка
wall_w = 1.2  # правый простенок

col_x, col_y, col_s = 2.5, 4.5, 0.9

# Ресепшн
desk_x, desk_y = 7.0 - 0.6, 4.0  # прижат к правой стене
desk_w, desk_h = 0.6, 2.8

# Задняя стена (справа налево)
right_gap = 0.8
door_tech_x = width_m - right_gap - 0.9
door_tech_w = 0.9
display_x = door_tech_x - 1.3
display_w = 1.3
door_stock_x = display_x - 0.9
door_stock_w = 0.9

# --- ГЕНЕРАЦИЯ SVG ---
svg = f'''<svg width="{width_px + 200}" height="{depth_px + 200}" xmlns="http://www.w3.org/2000/svg" style="background-color: white; font-family: sans-serif;">
    <g transform="translate(100, 100)">
        <!-- СТЕНЫ (Толстый контур) -->
        <rect x="0" y="0" width="{width_px}" height="{depth_px}" fill="none" stroke="black" stroke-width="3"/>

        <!-- РАЗМЕРНЫЕ ЛИНИИ СНАРУЖИ -->
        <!-- Общая ширина 7м -->
        <line x1="0" y1="-70" x2="{width_px}" y2="-70" stroke="black" stroke-width="1"/>
        <line x1="0" y1="-60" x2="0" y2="-80" stroke="black" stroke-width="1"/>
        <line x1="{width_px}" y1="-60" x2="{width_px}" y2="-80" stroke="black" stroke-width="1"/>
        <text x="{width_px/2}" y="-85" font-size="16" text-anchor="middle" fill="black">7 000 мм</text>

        <!-- Общая глубина 9м -->
        <line x1="{width_px + 30}" y1="0" x2="{width_px + 30}" y2="{depth_px}" stroke="black" stroke-width="1"/>
        <line x1="{width_px + 20}" y1="0" x2="{width_px + 40}" y2="0" stroke="black" stroke-width="1"/>
        <line x1="{width_px + 20}" y1="{depth_px}" x2="{width_px + 40}" y2="{depth_px}" stroke="black" stroke-width="1"/>
        <text x="{width_px + 45}" y="{depth_px/2}" font-size="16" transform="rotate(90, {width_px + 45}, {depth_px/2})" fill="black">9 000 мм</text>

        <!-- ПРОЕМЫ -->
        <!-- Вход (1м) -->
        <rect x="{door_x*scale}" y="{depth_px}" width="{door_w*scale}" height="8" fill="none" stroke="black" stroke-width="2"/>
        <line x1="{door_x*scale}" y1="{depth_px + 5}" x2="{door_x*scale + door_w*scale}" y2="{depth_px + 5}" stroke="black" stroke-width="1" stroke-dasharray="3,3"/>
        <text x="{door_x*scale + 20}" y="{depth_px + 35}" font-size="14" fill="black">Вход (1000)</text>

        <!-- Окно (4.8м) -->
        <rect x="{win_x*scale}" y="{depth_px - 4}" width="{win_w*scale}" height="8" fill="none" stroke="black" stroke-width="2"/>
        <text x="{win_x*scale + 100}" y="{depth_px + 35}" font-size="14" fill="black">Окно (4800)</text>

        <!-- Простенок (1.2м) -->
        <text x="{wall_x*scale + 30}" y="{depth_px + 35}" font-size="14" fill="black">Простенок (1200)</text>

        <!-- КОЛОННА -->
        <rect x="{col_x*scale}" y="{col_y*scale}" width="{col_s*scale}" height="{col_s*scale}" fill="none" stroke="black" stroke-width="2"/>
        <text x="{col_x*scale + col_s*scale/2}" y="{col_y*scale + 20}" font-size="12" text-anchor="middle" fill="black">Колонна</text>
        <text x="{col_x*scale + col_s*scale/2}" y="{col_y*scale + 40}" font-size="12" text-anchor="middle" fill="black">900х900</text>

        <!-- РЕСЕПШН -->
        <rect x="{desk_x*scale}" y="{desk_y*scale}" width="{desk_w*scale}" height="{desk_h*scale}" fill="none" stroke="black" stroke-width="2"/>
        <text x="{desk_x*scale - 15}" y="{desk_y*scale + 40}" font-size="14" font-weight="bold" text-anchor="end" fill="black">Ресепшн</text>

        <!-- ЗАДНЯЯ СТЕНА (Черные линии) -->
        <!-- Белая дверь -->
        <rect x="{door_tech_x*scale}" y="0" width="{door_tech_w*scale}" height="8" fill="none" stroke="black" stroke-width="2"/>
        <text x="{door_tech_x*scale + door_tech_w*scale/2}" y="-20" font-size="12" text-anchor="middle" fill="black">Тех. кабинет</text>

        <!-- Витрина -->
        <rect x="{display_x*scale}" y="0" width="{display_w*scale}" height="8" fill="none" stroke="black" stroke-width="2"/>
        <text x="{display_x*scale + display_w*scale/2}" y="-20" font-size="12" text-anchor="middle" fill="black">Витрина (1300)</text>

        <!-- Фиолетовая дверь -->
        <rect x="{door_stock_x*scale}" y="0" width="{door_stock_w*scale}" height="8" fill="none" stroke="black" stroke-width="2"/>
        <text x="{door_stock_x*scale + door_stock_w*scale/2}" y="-20" font-size="12" text-anchor="middle" fill="black">Склад</text>
    </g>
</svg>'''

print(svg)
