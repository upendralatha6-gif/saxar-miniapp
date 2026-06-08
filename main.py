import os
import hmac
import hashlib
import json
import urllib.parse
import logging
import httpx
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import db

logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = 941957416
DEV_MODE = not TELEGRAM_BOT_TOKEN

SERVICES = {

    # ========== ЖЕНСКИЙ ПРАЙС ==========

    # 🪒 ДЕПИЛЯЦИЯ — Дополнительно
    "w_dep_pudra": {"name": "Пудра энзимная", "price": "60 руб", "duration": 10, "category": "🪒 Депиляция (доп.)", "gender": "female"},
    "w_dep_maska": {"name": "Противовоспалительная маска", "price": "60 руб", "duration": 10, "category": "🪒 Депиляция (доп.)", "gender": "female"},
    "w_dep_gel": {"name": "Обезболивающий гель", "price": "650 руб", "duration": 10, "category": "🪒 Депиляция (доп.)", "gender": "female"},

    # 🪒 ВОСКОВАЯ ДЕПИЛЯЦИЯ
    "w_vosk_telo": {"name": "Всё тело (подмышки+бикини+ноги полностью)", "price": "2100 руб", "duration": 90, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_podm": {"name": "Подмышечные впадины", "price": "300 руб", "duration": 20, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_bikini_tr": {"name": "Бикини трусики", "price": "400 руб", "duration": 20, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_bikini_gl": {"name": "Бикини глубокое", "price": "700 руб", "duration": 30, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_nogi_do": {"name": "Ноги до колен", "price": "600 руб", "duration": 30, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_nogi_vyshe": {"name": "Ноги выше колен", "price": "600 руб", "duration": 30, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_nogi_pol": {"name": "Ноги полностью", "price": "1100 руб", "duration": 60, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_ruki_do": {"name": "Руки до локтя", "price": "350 руб", "duration": 20, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_ruki_34": {"name": "Руки 3/4", "price": "600 руб", "duration": 30, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_ruki_pol": {"name": "Руки полностью", "price": "700 руб", "duration": 40, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "400 руб", "duration": 20, "category": "🪒 Восковая депиляция", "gender": "female"},
    "w_vosk_liniya": {"name": "Линия живота/колени/плечи/кисти/пальцы/ареолы", "price": "100 руб", "duration": 10, "category": "🪒 Восковая депиляция", "gender": "female"},

    # 🪒 ПОЛИМЕРНЫЙ ВОСК
    "w_polvosk_telo": {"name": "Всё тело (подмышки+бикини+ноги полностью)", "price": "3900 руб", "duration": 120, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_lico_zona": {"name": "Область лица", "price": "250 руб", "duration": 15, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_lico_pol": {"name": "Лицо полностью", "price": "950 руб", "duration": 30, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_podm": {"name": "Подмышечные впадины", "price": "400 руб", "duration": 20, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_bikini_tr": {"name": "Бикини трусики", "price": "600 руб", "duration": 25, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_bikini_gl": {"name": "Бикини глубокое", "price": "1200 руб", "duration": 40, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_nogi_do": {"name": "Ноги до колен", "price": "1100 руб", "duration": 40, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_nogi_vyshe": {"name": "Ноги выше колен", "price": "1100 руб", "duration": 40, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_nogi_pol": {"name": "Ноги полностью", "price": "2200 руб", "duration": 60, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_ruki_do": {"name": "Руки до локтя", "price": "550 руб", "duration": 25, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_ruki_pol": {"name": "Руки полностью", "price": "1100 руб", "duration": 50, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "600 руб", "duration": 20, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_liniya": {"name": "Линия живота/колени/плечи (1 зона)", "price": "250 руб", "duration": 10, "category": "🪒 Полимерный воск", "gender": "female"},
    "w_polvosk_nos": {"name": "Нос/Уши (1 зона)", "price": "350 руб", "duration": 10, "category": "🪒 Полимерный воск", "gender": "female"},

    # 🪒 ДЕПИЛЯЦИЯ SKIN'S POSTAVKA #1
    "w_skins_telo": {"name": "Всё тело (подмышки+бикини+ноги полностью)", "price": "6300 руб", "duration": 120, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_lico": {"name": "Область лица", "price": "450 руб", "duration": 15, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_podm": {"name": "Подмышечные впадины", "price": "600 руб", "duration": 20, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_bikini_tr": {"name": "Бикини трусики", "price": "850 руб", "duration": 25, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_bikini_gl": {"name": "Бикини глубокое", "price": "1800 руб", "duration": 40, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_nogi_do": {"name": "Ноги до колен", "price": "1950 руб", "duration": 50, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_nogi_vyshe": {"name": "Ноги выше колен", "price": "1950 руб", "duration": 50, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_nogi_pol": {"name": "Ноги полностью", "price": "3900 руб", "duration": 90, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_ruki_do": {"name": "Руки до локтя", "price": "950 руб", "duration": 30, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_ruki_pol": {"name": "Руки полностью", "price": "1700 руб", "duration": 50, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "950 руб", "duration": 25, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_nos": {"name": "Нос/Уши (1 зона)", "price": "350 руб", "duration": 10, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},
    "w_skins_kisti": {"name": "Кисти/Пальцы/Ареолы/Линия живота", "price": "400 руб", "duration": 10, "category": "🪒 SKIN'S POSTAVKA #1", "gender": "female"},

    # 🪒 ГЕЛЕВАЯ ДЕПИЛЯЦИЯ
    "w_gel_bikini_podm": {"name": "Бикини + подмышечные впадины", "price": "1950 руб", "duration": 50, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_lico_zona": {"name": "Область лица", "price": "300 руб", "duration": 15, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_lico_pol": {"name": "Лицо полностью", "price": "1100 руб", "duration": 30, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_podm": {"name": "Подмышечные впадины", "price": "500 руб", "duration": 20, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_bikini_tr": {"name": "Бикини трусики", "price": "850 руб", "duration": 25, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_bikini_gl": {"name": "Бикини глубокое", "price": "1450 руб", "duration": 40, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "750 руб", "duration": 25, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_kisti": {"name": "Кисти/Пальцы/Ареолы/Линия живота", "price": "300 руб", "duration": 10, "category": "🪒 Гелевая депиляция", "gender": "female"},
    "w_gel_nos": {"name": "Нос/Уши (1 зона)", "price": "400 руб", "duration": 10, "category": "🪒 Гелевая депиляция", "gender": "female"},

    # 🍬 ШУГАРИНГ
    "w_sugar_telo": {"name": "Всё тело (подмышки+бикини+ноги полностью)", "price": "2550 руб", "duration": 120, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_lico_zona": {"name": "Область лица", "price": "250 руб", "duration": 15, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_lico_pol": {"name": "Лицо полностью", "price": "700 руб", "duration": 30, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_podm": {"name": "Подмышечные впадины", "price": "300 руб", "duration": 20, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_bikini_tr": {"name": "Бикини трусики", "price": "400 руб", "duration": 25, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_bikini_gl": {"name": "Бикини глубокое", "price": "1000 руб", "duration": 40, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_nogi_do": {"name": "Ноги до колен", "price": "650 руб", "duration": 30, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_nogi_vyshe": {"name": "Ноги выше колен", "price": "650 руб", "duration": 30, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_nogi_pol": {"name": "Ноги полностью", "price": "1300 руб", "duration": 60, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_ruki_do": {"name": "Руки до локтя", "price": "350 руб", "duration": 20, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_ruki_pol": {"name": "Руки полностью", "price": "650 руб", "duration": 40, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "500 руб", "duration": 20, "category": "🍬 Шугаринг", "gender": "female"},
    "w_sugar_kisti": {"name": "Кисти/Пальцы/Ареолы/Линия живота", "price": "150 руб", "duration": 10, "category": "🍬 Шугаринг", "gender": "female"},

    # 💧 AQUA ШУГАРИНГ
    "w_aqua_lico": {"name": "Область лица", "price": "300 руб", "duration": 15, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_lico_pol": {"name": "Лицо полностью", "price": "800 руб", "duration": 30, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_podm": {"name": "Подмышечные впадины", "price": "400 руб", "duration": 20, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_bikini_tr": {"name": "Бикини трусики", "price": "700 руб", "duration": 25, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_bikini_gl": {"name": "Бикини глубокое", "price": "1250 руб", "duration": 40, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_nogi_do": {"name": "Ноги до колен", "price": "700 руб", "duration": 30, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_nogi_vyshe": {"name": "Ноги выше колен", "price": "800 руб", "duration": 30, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_nogi_pol": {"name": "Ноги полностью", "price": "1400 руб", "duration": 60, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_plechi": {"name": "Плечи", "price": "300 руб", "duration": 15, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_poyasnica": {"name": "Поясница", "price": "350 руб", "duration": 15, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_spina": {"name": "Спина полностью", "price": "850 руб", "duration": 40, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_zona": {"name": "Ягодицы/Живот/Грудь (1 зона)", "price": "750 руб", "duration": 25, "category": "💧 Aqua шугаринг", "gender": "female"},
    "w_aqua_kisti": {"name": "Кисти/Пальцы/Ареолы (1 зона)", "price": "300 руб", "duration": 10, "category": "💧 Aqua шугаринг", "gender": "female"},

    # ⚡ ЛАЗЕРНАЯ ЭПИЛЯЦИЯ (женская)
    "w_lazer_podm_bikini": {"name": "Подмышки + бикини глубокое", "price": "2000 руб", "duration": 60, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_podm_bikini_nogi_do": {"name": "Подмышки + бикини + ноги до/выше колен", "price": "4000 руб", "duration": 90, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_podm_bikini_nogi_pol": {"name": "Подмышки + бикини + ноги полностью", "price": "6000 руб", "duration": 120, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_bikini_nogi_do": {"name": "Бикини + ноги до/выше колен", "price": "3400 руб", "duration": 80, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_bikini_nogi_pol": {"name": "Бикини + ноги полностью", "price": "5400 руб", "duration": 100, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_lico": {"name": "Область лица", "price": "500 руб", "duration": 20, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_podm": {"name": "Подмышечные впадины", "price": "600 руб", "duration": 20, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_bikini_gl": {"name": "Бикини глубокое", "price": "1400 руб", "duration": 40, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_bikini_tr": {"name": "Бикини трусики", "price": "1000 руб", "duration": 30, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_nogi_do": {"name": "Ноги до колен", "price": "2000 руб", "duration": 50, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_nogi_vyshe": {"name": "Ноги выше колен", "price": "2000 руб", "duration": 50, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_nogi_pol": {"name": "Ноги полностью", "price": "4000 руб", "duration": 90, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_ruki_do": {"name": "Руки до локтя", "price": "1500 руб", "duration": 40, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_ruki_pol": {"name": "Руки полностью", "price": "3000 руб", "duration": 70, "category": "⚡ Лазерная эпиляция", "gender": "female"},
    "w_lazer_zona": {"name": "Ягодицы/Живот/Спина/Грудь (1 зона)", "price": "1100 руб", "duration": 30, "category": "⚡ Лазерная эпиляция", "gender": "female"},

    # 🌿 GELING до/после депиляции
    "w_geling_lico": {"name": "Область лица", "price": "200 руб", "duration": 15, "category": "🌿 Geling", "gender": "female"},
    "w_geling_podm": {"name": "Подмышечные впадины", "price": "500 руб", "duration": 20, "category": "🌿 Geling", "gender": "female"},
    "w_geling_bikini_tr": {"name": "Бикини трусики", "price": "350 руб", "duration": 20, "category": "🌿 Geling", "gender": "female"},
    "w_geling_bikini_gl": {"name": "Бикини глубокое", "price": "700 руб", "duration": 35, "category": "🌿 Geling", "gender": "female"},
    "w_geling_nogi_do": {"name": "Ноги до колен", "price": "1200 руб", "duration": 40, "category": "🌿 Geling", "gender": "female"},
    "w_geling_nogi_vyshe": {"name": "Ноги выше колен", "price": "1200 руб", "duration": 40, "category": "🌿 Geling", "gender": "female"},
    "w_geling_nogi_pol": {"name": "Ноги полностью", "price": "2400 руб", "duration": 75, "category": "🌿 Geling", "gender": "female"},
    "w_geling_ruki_do": {"name": "Руки до локтя", "price": "700 руб", "duration": 30, "category": "🌿 Geling", "gender": "female"},
    "w_geling_liniya": {"name": "Линия живота", "price": "200 руб", "duration": 10, "category": "🌿 Geling", "gender": "female"},
    "w_geling_zona": {"name": "Спина/Живот/Плечи/Ягодицы (1 зона)", "price": "700 руб", "duration": 25, "category": "🌿 Geling", "gender": "female"},

    # 💅 МАНИКЮР
    "w_man_klass": {"name": "Маникюр на выбор (классический/комбинированный/аппаратный)", "price": "1000 руб", "duration": 60, "category": "💅 Маникюр", "gender": "female"},
    "w_man_kompl_gel": {"name": "Комплекс: маникюр + снятие + покрытие гель-лак", "price": "1750 руб", "duration": 90, "category": "💅 Маникюр", "gender": "female"},
    "w_man_kompl_spa": {"name": "Комплекс: маникюр + снятие + покрытие + СПА уход + масло + массаж", "price": "2500 руб", "duration": 120, "category": "💅 Маникюр", "gender": "female"},
    "w_man_detsky": {"name": "Маникюр детский (до 7 лет)", "price": "400 руб", "duration": 30, "category": "💅 Маникюр", "gender": "female"},
    "w_man_yapon": {"name": "Маникюр японский", "price": "1400 руб", "duration": 75, "category": "💅 Маникюр", "gender": "female"},
    "w_man_parafin": {"name": "Парафинотерапия рук", "price": "400 руб", "duration": 20, "category": "💅 Маникюр", "gender": "female"},
    "w_man_spa": {"name": "SPA-уход для рук", "price": "450 руб", "duration": 25, "category": "💅 Маникюр", "gender": "female"},
    "w_man_massage": {"name": "Массаж кистей 15 минут", "price": "400 руб", "duration": 15, "category": "💅 Маникюр", "gender": "female"},
    "w_man_polirovka": {"name": "Полировка ногтей", "price": "300 руб", "duration": 15, "category": "💅 Маникюр", "gender": "female"},

    # 💅 ПОКРЫТИЕ
    "w_pokr_lak": {"name": "Лак", "price": "550 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_lak_halal": {"name": "Лак HALAL", "price": "650 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_gel": {"name": "Гель-лак", "price": "750 руб", "duration": 30, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_gel_luxio": {"name": "Гель-лак LUXIO", "price": "1200 руб", "duration": 30, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_inki": {"name": "Экоглянцевание INKI (HALAL)", "price": "850 руб", "duration": 30, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_yapon_vtirka": {"name": "Японская втирка", "price": "600 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_snyatie_s": {"name": "Снятие гель-лака с последующим покрытием", "price": "250 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_snyatie_bez": {"name": "Снятие гель-лака без покрытия", "price": "400 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_hna": {"name": "Покрытие хной", "price": "550 руб", "duration": 25, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_tochki_hna": {"name": "Точки хной", "price": "250 руб", "duration": 15, "category": "💅 Покрытие", "gender": "female"},
    "w_pokr_snyatie_gel": {"name": "Снятие укрепления гелем", "price": "400 руб", "duration": 20, "category": "💅 Покрытие", "gender": "female"},

    # 💅 НАРАЩИВАНИЕ И ДИЗАЙН
    "w_nar_ukrp_gel": {"name": "Укрепление гелем под гель-лак", "price": "650 руб", "duration": 40, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_ukrp_kamuf": {"name": "Укрепление камуфлирующим гелем", "price": "1500 руб", "duration": 60, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_noghi": {"name": "Наращивание ногтей", "price": "2350 руб", "duration": 120, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_snyatie": {"name": "Снятие нарощенных ногтей", "price": "600 руб", "duration": 30, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_korrekciya": {"name": "Коррекция ногтей", "price": "70% от стоимости", "duration": 90, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_french": {"name": "Френч", "price": "400 руб", "duration": 20, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_lunki": {"name": "Лунки/Втирка", "price": "400 руб", "duration": 20, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_slider": {"name": "Слайдер/Втирка (1 ноготь)", "price": "60 руб", "duration": 5, "category": "💅 Наращивание и дизайн", "gender": "female"},
    "w_nar_rospis": {"name": "Художественная роспись (1 ноготь)", "price": "300 руб", "duration": 10, "category": "💅 Наращивание и дизайн", "gender": "female"},

    # 🦶 ПЕДИКЮР
    "w_ped_palchiki": {"name": "Обработка пальчиков", "price": "650 руб", "duration": 30, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_stopy": {"name": "Обработка стоп", "price": "750 руб", "duration": 30, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_klass": {"name": "Педикюр на выбор (классический/комбинированный/аппаратный)", "price": "1200 руб", "duration": 60, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_kompl_gel": {"name": "Комплекс: педикюр + снятие + покрытие гель-лак", "price": "1950 руб", "duration": 90, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_kompl_spa": {"name": "Комплекс: педикюр + снятие + покрытие + СПА уход + масло + массаж", "price": "2750 руб", "duration": 120, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_yapon": {"name": "Педикюр японский", "price": "1500 руб", "duration": 75, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_smart": {"name": "SMART-педикюр", "price": "1800 руб", "duration": 90, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_golden": {"name": "Педикюр Golden Trace", "price": "2200 руб", "duration": 90, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_parafin": {"name": "Парафинотерапия ног", "price": "450 руб", "duration": 20, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_spa": {"name": "SPA-уход для ног", "price": "500 руб", "duration": 25, "category": "🦶 Педикюр", "gender": "female"},
    "w_ped_massage": {"name": "Массаж стоп 15 минут", "price": "500 руб", "duration": 15, "category": "🦶 Педикюр", "gender": "female"},

    # 👁 БРОВИ
    "w_brov_oform_kraska": {"name": "Оформление бровей пинцет/воск + окрашивание краской", "price": "1200 руб", "duration": 45, "category": "👁 Брови", "gender": "female"},
    "w_brov_oform_hna": {"name": "Оформление бровей пинцет/воск + окрашивание хной", "price": "1200 руб", "duration": 45, "category": "👁 Брови", "gender": "female"},
    "w_brov_oform": {"name": "Оформление пинцетом/воском", "price": "700 руб", "duration": 30, "category": "👁 Брови", "gender": "female"},
    "w_brov_kraska": {"name": "Окрашивание бровей краской", "price": "700 руб", "duration": 20, "category": "👁 Брови", "gender": "female"},
    "w_brov_hna": {"name": "Окрашивание бровей хной", "price": "700 руб", "duration": 20, "category": "👁 Брови", "gender": "female"},
    "w_brov_kompl_full": {"name": "Комплекс: оформление + окрашивание + долговременная укладка + Счастье для бровей", "price": "3500 руб", "duration": 120, "category": "👁 Брови", "gender": "female"},
    "w_brov_kompl_ukl": {"name": "Комплекс: оформление + окрашивание + долговременная укладка", "price": "2700 руб", "duration": 90, "category": "👁 Брови", "gender": "female"},
    "w_brov_kompl_oform_ukl": {"name": "Комплекс: оформление бровей + долговременная укладка", "price": "2000 руб", "duration": 75, "category": "👁 Брови", "gender": "female"},
    "w_brov_lamin_sigma": {"name": "Ламинирование бровей SIGMA", "price": "1800 руб", "duration": 60, "category": "👁 Брови", "gender": "female"},
    "w_brov_lamin_lami": {"name": "Ламинирование бровей LAMI SMART", "price": "2000 руб", "duration": 60, "category": "👁 Брови", "gender": "female"},
    "w_brov_velvet": {"name": "Вельвет бровей", "price": "2600 руб", "duration": 75, "category": "👁 Брови", "gender": "female"},
    "w_brov_schaste": {"name": "Счастье для бровей", "price": "1000 руб", "duration": 30, "category": "👁 Брови", "gender": "female"},
    "w_brov_osvetlenie": {"name": "Деликатное осветление бровей", "price": "500 руб", "duration": 20, "category": "👁 Брови", "gender": "female"},

    # 👁 РЕСНИЦЫ
    "w_res_okrash": {"name": "Окрашивание ресниц", "price": "800 руб", "duration": 20, "category": "👁 Ресницы", "gender": "female"},
    "w_res_lamin_sigma": {"name": "Ламинирование ресниц SIGMA", "price": "2000 руб", "duration": 60, "category": "👁 Ресницы", "gender": "female"},
    "w_res_lamin_lami": {"name": "Ламинирование ресниц LAMI SMART", "price": "2400 руб", "duration": 60, "category": "👁 Ресницы", "gender": "female"},
    "w_res_velvet": {"name": "Вельвет ресниц", "price": "2700 руб", "duration": 75, "category": "👁 Ресницы", "gender": "female"},
    "w_res_schaste": {"name": "Счастье для ресниц", "price": "1200 руб", "duration": 30, "category": "👁 Ресницы", "gender": "female"},
    "w_res_kompl_ukl": {"name": "Комплекс: окрашивание ресниц + долговременная укладка", "price": "2500 руб", "duration": 90, "category": "👁 Ресницы", "gender": "female"},
    "w_res_kompl_full": {"name": "Комплекс: окрашивание ресниц + долговременная укладка + Счастье для ресниц", "price": "3500 руб", "duration": 120, "category": "👁 Ресницы", "gender": "female"},
    "w_res_express": {"name": "Экспресс-наращивание ресниц", "price": "1300 руб", "duration": 60, "category": "👁 Ресницы", "gender": "female"},
    "w_res_nar_1d": {"name": "Наращивание ресниц 1D", "price": "1750 руб", "duration": 90, "category": "👁 Ресницы", "gender": "female"},
    "w_res_nar_15d": {"name": "Наращивание ресниц 1.5D", "price": "2000 руб", "duration": 95, "category": "👁 Ресницы", "gender": "female"},
    "w_res_nar_2d": {"name": "Наращивание ресниц 2D", "price": "2300 руб", "duration": 100, "category": "👁 Ресницы", "gender": "female"},
    "w_res_nar_3d": {"name": "Наращивание ресниц 3D", "price": "2500 руб", "duration": 110, "category": "👁 Ресницы", "gender": "female"},
    "w_res_nar_45d": {"name": "Наращивание ресниц 4/5D", "price": "3000 руб", "duration": 120, "category": "👁 Ресницы", "gender": "female"},
    "w_res_effekt": {"name": "Эффект ресниц (мокрый/Кайли/цветные)", "price": "450 руб", "duration": 20, "category": "👁 Ресницы", "gender": "female"},
    "w_res_korrekciya": {"name": "Коррекция ресниц", "price": "70% от стоимости", "duration": 60, "category": "👁 Ресницы", "gender": "female"},
    "w_res_snyatie": {"name": "Снятие ресниц", "price": "350 руб", "duration": 20, "category": "👁 Ресницы", "gender": "female"},

    # 💄 ВИЗАЖ — МАКИЯЖ
    "w_mak_express": {"name": "Макияж «Экспресс»", "price": "1800 руб", "duration": 45, "category": "💄 Макияж", "gender": "female"},
    "w_mak_dnevnoy": {"name": "Дневной макияж", "price": "2800 руб", "duration": 60, "category": "💄 Макияж", "gender": "female"},
    "w_mak_vecherny": {"name": "Вечерний макияж", "price": "3700 руб", "duration": 75, "category": "💄 Макияж", "gender": "female"},
    "w_mak_slozhny": {"name": "Сложный макияж", "price": "5000 руб", "duration": 90, "category": "💄 Макияж", "gender": "female"},
    "w_mak_puchki_express": {"name": "Ресничные пучки — экспресс объём", "price": "400 руб", "duration": 20, "category": "💄 Макияж", "gender": "female"},
    "w_mak_puchki_pol": {"name": "Ресничные пучки — полный объём", "price": "600 руб", "duration": 30, "category": "💄 Макияж", "gender": "female"},

    # 💄 ВИЗАЖ — ОБРАЗ
    "w_obraz_dnevnoy": {"name": "Дневной образ", "price": "3800 руб", "duration": 120, "category": "💄 Образ", "gender": "female"},
    "w_obraz_vecherny": {"name": "Вечерний образ", "price": "4500 руб", "duration": 150, "category": "💄 Образ", "gender": "female"},
    "w_obraz_prazdnik": {"name": "Праздничный образ", "price": "6000 руб", "duration": 180, "category": "💄 Образ", "gender": "female"},

    # ✂️ ПАРИКМАХЕР — СТРИЖКА И УКЛАДКА
    "w_hair_striz": {"name": "Стрижка женская", "price": "2000 руб", "duration": 60, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_striz_det": {"name": "Стрижка детская (до 7 лет)", "price": "700 руб", "duration": 30, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_podravnivanie": {"name": "Подравнивание (одним срезом, без мытья)", "price": "1000 руб", "duration": 20, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_chelka": {"name": "Стрижка чёлки", "price": "700 руб", "duration": 15, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_ukladka": {"name": "Укладка лёгкая", "price": "1750 руб", "duration": 45, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_mytyo": {"name": "Мытьё головы (с сушкой)", "price": "1000 руб", "duration": 30, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_massage": {"name": "Массаж головы 15 минут", "price": "400 руб", "duration": 15, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_pricheska": {"name": "Причёска вечерняя", "price": "3000–4200 руб", "duration": 90, "category": "✂️ Стрижка и укладка", "gender": "female"},
    "w_hair_express_prich": {"name": "Экспресс-причёска", "price": "2000–3000 руб", "duration": 45, "category": "✂️ Стрижка и укладка", "gender": "female"},

    # ✂️ ЛОКОНЫ И КОСЫ
    "w_hair_gollivud": {"name": "Голливудские локоны", "price": "2200 руб", "duration": 60, "category": "✂️ Локоны и косы", "gender": "female"},
    "w_hair_brashinng": {"name": "Локоны на брашинг", "price": "2000 руб", "duration": 60, "category": "✂️ Локоны и косы", "gender": "female"},
    "w_hair_kosi": {"name": "Плетение кос", "price": "1500 руб", "duration": 60, "category": "✂️ Локоны и косы", "gender": "female"},

    # 💆 ЛЕЧЕНИЕ ВОЛОС
    "w_vol_revlon_okr": {"name": "Олаплекс при окрашивании", "price": "1500 руб", "duration": 20, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_uhod_golova": {"name": "Уход за кожей головы / пилинг", "price": "1750 руб", "duration": 30, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_abs_k": {"name": "Абсолютное счастье LEBEL — короткая", "price": "3600 руб", "duration": 60, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_abs_s": {"name": "Абсолютное счастье LEBEL — средняя", "price": "5500 руб", "duration": 75, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_abs_d": {"name": "Абсолютное счастье LEBEL — длинная", "price": "6500 руб", "duration": 90, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_abs_xl": {"name": "Абсолютное счастье LEBEL — очень длинная", "price": "8000 руб", "duration": 105, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_pros_k": {"name": "«Проснись голова» LEBEL — короткая", "price": "1750 руб", "duration": 40, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_pros_s": {"name": "«Проснись голова» LEBEL — средняя", "price": "2400 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_pros_d": {"name": "«Проснись голова» LEBEL — длинная", "price": "3000 руб", "duration": 60, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_blesk_k": {"name": "Блеск и сила LEBEL — короткая", "price": "1800 руб", "duration": 40, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_blesk_s": {"name": "Блеск и сила LEBEL — средняя", "price": "2600 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_blesk_d": {"name": "Блеск и сила LEBEL — длинная", "price": "3700 руб", "duration": 60, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_matrix_express": {"name": "Экспресс-уход Matrix", "price": "500 руб", "duration": 20, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_sila_k": {"name": "Жизненная сила LEBEL — короткая", "price": "2100 руб", "duration": 40, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_sila_s": {"name": "Жизненная сила LEBEL — средняя", "price": "2400 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_lebel_sila_d": {"name": "Жизненная сила LEBEL — длинная", "price": "3000 руб", "duration": 60, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_nanoplas_k": {"name": "Нанопластика — короткая", "price": "4000 руб", "duration": 90, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_nanoplas_s": {"name": "Нанопластика — средняя", "price": "7500 руб", "duration": 110, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_nanoplas_d": {"name": "Нанопластика — длинная", "price": "9000 руб", "duration": 130, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_botox_k": {"name": "Ботокс волос Honma Tokio — короткая", "price": "4000 руб", "duration": 90, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_botox_s": {"name": "Ботокс волос Honma Tokio — средняя", "price": "6000 руб", "duration": 110, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_botox_d": {"name": "Ботокс волос Honma Tokio — длинная", "price": "11600 руб", "duration": 130, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_zavivka": {"name": "Биозавивка волос (карвинг)", "price": "4800–8400 руб", "duration": 120, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_keratin_k": {"name": "Кератиновое выпрямление — короткая", "price": "5000 руб", "duration": 120, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_keratin_s": {"name": "Кератиновое выпрямление — средняя", "price": "7550 руб", "duration": 150, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_keratin_d": {"name": "Кератиновое выпрямление — длинная", "price": "13600 руб", "duration": 180, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_total": {"name": "Тотальная реконструкция волос LIMBA", "price": "5900/8000 руб", "duration": 120, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_pitanie": {"name": "Экспресс питание LIMBA", "price": "2450 руб", "duration": 40, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_uvl": {"name": "Экспресс увлажнение LIMBA", "price": "2000 руб", "duration": 40, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_detox": {"name": "Детокс и увлажнение в городских условиях LIMBA", "price": "3000 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_uplom": {"name": "Уплотнение и защита тонких волос LIMBA", "price": "3000 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},
    "w_vol_limba_shelk": {"name": "Шелковая терапия для жестких волос LIMBA", "price": "3000 руб", "duration": 50, "category": "💆 Лечение волос", "gender": "female"},

    # 🎨 ОКРАШИВАНИЕ ВОЛОС
    "w_okr_1ton_k": {"name": "Окрашивание/тонирование в 1 тон — короткая", "price": "3800/5400 руб", "duration": 90, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_1ton_s": {"name": "Окрашивание/тонирование в 1 тон — средняя", "price": "4900/7000 руб", "duration": 100, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_1ton_d": {"name": "Окрашивание/тонирование в 1 тон — длинная", "price": "5900/8300 руб", "duration": 110, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_slozh_k": {"name": "Сложное окрашивание — короткая", "price": "5450/6700 руб", "duration": 120, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_slozh_s": {"name": "Сложное окрашивание — средняя", "price": "8000/9900 руб", "duration": 150, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_slozh_d": {"name": "Сложное окрашивание — длинная", "price": "11900/13200 руб", "duration": 180, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_korni_ton": {"name": "Окрашивание корней + тонирование", "price": "3500 руб", "duration": 60, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_airtouch_k": {"name": "Airtouch — короткая", "price": "7500/8600 руб", "duration": 150, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_airtouch_s": {"name": "Airtouch — средняя", "price": "9800/11600 руб", "duration": 180, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_airtouch_d": {"name": "Airtouch — длинная", "price": "13200/15900 руб", "duration": 210, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_melir_k": {"name": "Мелирование без тонирования — короткая", "price": "4300/5600 руб", "duration": 90, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_melir_s": {"name": "Мелирование без тонирования — средняя", "price": "5400/6600 руб", "duration": 100, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_melir_d": {"name": "Мелирование без тонирования — длинная", "price": "6900/8000 руб", "duration": 110, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_total_blonde_k": {"name": "Total Blonde — короткая", "price": "7500 руб", "duration": 150, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_total_blonde_s": {"name": "Total Blonde — средняя", "price": "9300 руб", "duration": 180, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_total_blonde_d": {"name": "Total Blonde — длинная", "price": "14800 руб", "duration": 210, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_kontur_2pradi": {"name": "Контуринг 2 пряди", "price": "2000/2900 руб", "duration": 60, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_konturing": {"name": "Контуринг по всем волосам", "price": "2000/4000 руб", "duration": 90, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_korni": {"name": "Окрашивание/тонирование корней", "price": "2850/4400 руб", "duration": 60, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_smyvka_k": {"name": "Смывка Estel — короткая", "price": "3800 руб", "duration": 60, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_smyvka_s": {"name": "Смывка Estel — средняя", "price": "4900 руб", "duration": 75, "category": "🎨 Окрашивание", "gender": "female"},
    "w_okr_smyvka_d": {"name": "Смывка Estel — длинная", "price": "5900 руб", "duration": 90, "category": "🎨 Окрашивание", "gender": "female"},

    # 💆 МАССАЖ ТЕЛА
    "w_mass_antitsel_30": {"name": "Антицеллюлитный комплекс 3 зоны (бёдра, бока, ягодицы) 30 мин", "price": "1600 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_antitsel_60": {"name": "Антицеллюлитный комплекс 3 зоны (бёдра, бока, ягодицы) 60 мин", "price": "2500 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_antitsel_5zon": {"name": "Антицеллюлитный комплекс 5 зон (живот, бёдра, бока, ягодицы, руки) 90 мин", "price": "3200 руб", "duration": 90, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_limfodren_60": {"name": "Лимфодренажный массаж тело 60 мин", "price": "2500 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_limfodren_90": {"name": "Лимфодренажный массаж тело 90 мин", "price": "3200 руб", "duration": 90, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spina_30": {"name": "Массаж спины 30 мин", "price": "1000 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_sheya_30": {"name": "Шейно-воротниковая зона 30 мин", "price": "750 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_golova_30": {"name": "Голова 30 мин", "price": "750 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_nogi_30": {"name": "Ноги 30 мин", "price": "800 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_ruki_30": {"name": "Руки 30 мин", "price": "750 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_klass_60": {"name": "Классический общий массаж 60 мин", "price": "2300 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_klass_90": {"name": "Классический общий массаж 90 мин", "price": "2800 руб", "duration": 90, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_relax_60": {"name": "Расслабляющий массаж 60 мин", "price": "2500 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_relax_90": {"name": "Расслабляющий массаж 90 мин", "price": "3200 руб", "duration": 90, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_dop": {"name": "Доп. массаж в завершении СПА-процедуры 20 мин", "price": "750 руб", "duration": 20, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_stoun": {"name": "Стоун-терапия, массаж горячими камнями", "price": "2500 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_obert_antitsel": {"name": "Горячее антицеллюлитное обертывание", "price": "1300 руб", "duration": 40, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_bandaz": {"name": "Бандажное бинтование", "price": "1900 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_kontury": {"name": "СПА-уход «Контуры тела»", "price": "2500 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_vodorosl": {"name": "СПА-уход «Водорослевое обертывание»", "price": "3200 руб", "duration": 75, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_antitsel": {"name": "СПА-уход «Антицеллюлитный»", "price": "3200 руб", "duration": 75, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_bandaz": {"name": "СПА-уход бандажное бинтование «Контуры тела»", "price": "3500 руб", "duration": 90, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_spa_med": {"name": "СПА-уход «Медовое наслаждение»", "price": "3200 руб", "duration": 75, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_skrab": {"name": "Скрабирование", "price": "1100 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_inhibitor_30": {"name": "Массаж на ингибиторе жира, всё тело 30 мин", "price": "3500 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_inhibitor_60": {"name": "Массаж на ингибиторе жира, всё тело 60 мин", "price": "4200 руб", "duration": 60, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_inhibitor_yag": {"name": "Массаж на ингибиторе жира (ягодицы, ножки) 30 мин", "price": "2000 руб", "duration": 30, "category": "💆 Массаж тела", "gender": "female"},
    "w_mass_megaskulptor": {"name": "Липомоделирующий массаж МЕГАСКУЛЬПТОР 45 мин", "price": "2750 руб", "duration": 45, "category": "💆 Массаж тела", "gender": "female"},

    # 💆 МАССАЖ ЛИЦА
    "w_mass_lico_60": {"name": "Массаж лицо, шея, декольте 60 мин", "price": "2000 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_lico_30": {"name": "Массаж лицо, шея, декольте 30 мин", "price": "1300 руб", "duration": 30, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_bukal_60": {"name": "Буккальный массаж хиропластический 60 мин", "price": "2800 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_bukal_90": {"name": "Буккальный массаж хиропластический 90 мин", "price": "3500 руб", "duration": 90, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_facefit_60": {"name": "Массаж лица FACE FIT (миолифтинговый) 60 мин", "price": "2800 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_facefit_90": {"name": "Массаж лица FACE FIT (миолифтинговый) 90 мин", "price": "3500 руб", "duration": 90, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_ispanskiy_60": {"name": "Испанский массаж лицо, декольте 60 мин", "price": "2800 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_ispanskiy_90": {"name": "Испанский массаж реанимирующий (гемолимфодренажный) 90 мин", "price": "3500 руб", "duration": 90, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_yapon_60": {"name": "Японский массаж лица (Асахи, Зоган) 60 мин", "price": "2800 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_yapon_90": {"name": "Японский массаж лица (Асахи, Зоган) 90 мин", "price": "3500 руб", "duration": 90, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_spetsialiiz_15": {"name": "Специализированные массажные техники 15 мин", "price": "750 руб", "duration": 15, "category": "💆 Массаж лица", "gender": "female"},
    "w_mass_avtorskiy": {"name": "Авторский массаж по индивидуальным показаниям 60 мин", "price": "3000 руб", "duration": 60, "category": "💆 Массаж лица", "gender": "female"},

    # 🧴 ЭСТЕТИЧЕСКАЯ КОСМЕТОЛОГИЯ
    "w_kosm_ultrazvuk": {"name": "Ультразвуковая чистка лица", "price": "2400 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_atravmat": {"name": "Атравматическая чистка лица", "price": "2500 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_kombi_chistka": {"name": "Комбинированная чистка лица", "price": "2600 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_apparat_chistka": {"name": "Аппаратная чистка лица", "price": "3500 руб", "duration": 75, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_karbo": {"name": "Карбокситерапия", "price": "2000 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_vodorosl_maska": {"name": "Водорослевая маска", "price": "750 руб", "duration": 20, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_uvl_maska": {"name": "Увлажняющая маска", "price": "750 руб", "duration": 20, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_programmy": {"name": "Программы ухода", "price": "1500/3500 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_rf": {"name": "RF-лифтинг", "price": "1500 руб", "duration": 30, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_krio": {"name": "Криотерапия/Хромотерапия/OXYJET/Фонофорез", "price": "1000/1500 руб", "duration": 30, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_mikrotoki": {"name": "Микротоки (лицо / лицо+шея / лицо+шея+декольте)", "price": "2000/3000 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_galvanika": {"name": "Гальваника", "price": "1500 руб", "duration": 30, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_kombo_chistka": {"name": "КОМБО: Чистка лица + пилинг миндальный + альгинатная маска", "price": "4850 руб", "duration": 90, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_kombo_express": {"name": "КОМБО: Экспресс уход + пилинг миндальный + альгинатная маска", "price": "4500 руб", "duration": 75, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_kombo_piling": {"name": "КОМБО: Пилинг миндальный + альгинатная маска", "price": "2500 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_kombo_karbo": {"name": "КОМБО: Карбокситерапия + альгинатная маска", "price": "2600 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_biorep": {"name": "Пилинг BioRePeel CL3", "price": "4000 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_prx": {"name": "Пилинг PRX-T34", "price": "4000 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_yellow": {"name": "Желтый пилинг Medik Control Peel", "price": "4500 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_laser": {"name": "Жидкий лазер. Комплекс пилинга PRX T33 с микронидлингом", "price": "7500 руб", "duration": 90, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_tca": {"name": "Пилинг ТСА", "price": "3500 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_pov_sred": {"name": "Поверхностно-срединные пилинги", "price": "3500 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_pov": {"name": "Поверхностные пилинги", "price": "2600 руб", "duration": 45, "category": "🧴 Косметология", "gender": "female"},
    "w_kosm_piling_sred": {"name": "Срединные (зимние) пилинги Medik Peel", "price": "4000 руб", "duration": 60, "category": "🧴 Косметология", "gender": "female"},

}

AVAILABLE_TIMES = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

SALON_INFO = {
    "name": "Салон красоты Sахар",
    "address": "Республика Дагестан, ул. Магомеда Ярагского, 42А",
    "phone": "+89681234567",
    "admin": "@coachgnv",
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ===== ОТПРАВКА СООБЩЕНИЙ В TELEGRAM =====

async def send_telegram_message(chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN:
        logging.warning("Токен не задан — уведомление не отправлено")
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")


def verify_init_data(init_data: str) -> Optional[dict]:
    if DEV_MODE:
        return {"id": ADMIN_CHAT_ID, "first_name": "Dev", "username": "dev"}
    if not init_data:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
        received_hash = parsed.pop("hash", "")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        user_json = parsed.get("user")
        return json.loads(user_json) if user_json else {}
    except Exception as e:
        logging.error(f"Init data error: {e}")
        return None


def get_user(x_telegram_init_data: Optional[str]) -> dict:
    user = verify_init_data(x_telegram_init_data or "")
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def require_admin(x_telegram_init_data: Optional[str]) -> dict:
    user = get_user(x_telegram_init_data)
    if user.get("id") != ADMIN_CHAT_ID:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return user


app = FastAPI(title="Saxar Salon Mini App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


# ===== ОТКРЫТЫЕ МАРШРУТЫ =====

@app.get("/api/salon-info")
def api_salon_info():
    return SALON_INFO


@app.get("/api/services")
def api_services():
    return [{"id": k, **v} for k, v in SERVICES.items()]


@app.get("/api/available-times/{date}")
def api_available_times(date: str):
    booked = db.get_booked_times(date)
    return [{"time": t, "available": t not in booked} for t in AVAILABLE_TIMES]


# ===== МАРШРУТЫ КЛИЕНТА =====

class BookingCreate(BaseModel):
    service: str
    date: str
    time: str
    client_name: str
    phone: str


@app.post("/api/bookings")
async def api_create_booking(
    body: BookingCreate,
    x_telegram_init_data: Optional[str] = Header(None),
):
    user = get_user(x_telegram_init_data)
    if body.service not in SERVICES:
        raise HTTPException(status_code=400, detail="Недопустимая услуга")
    if body.time in db.get_booked_times(body.date):
        raise HTTPException(status_code=409, detail="Это время уже занято")
    booking_id = db.add_booking(
        body.service, body.date, body.time,
        body.client_name, body.phone, user.get("id"),
    )
    service = SERVICES[body.service]

    # Уведомление клиенту
    client_chat_id = user.get("id")
    if client_chat_id:
        await send_telegram_message(
            client_chat_id,
            f"🎉 *Запись подтверждена!*\n\n"
            f"{service['name']} — *{service['price']}*\n"
            f"📅 Дата: *{body.date}* в *{body.time}*\n"
            f"👤 Имя: *{body.client_name}*\n"
            f"📱 Телефон: *{body.phone}*\n\n"
            f"📍 Ждём вас по адресу:\n{SALON_INFO['address']}\n\n"
            f"Если нужно перенести — напишите нам: {SALON_INFO['admin']} 💖"
        )

    # Уведомление администратору
    await send_telegram_message(
        ADMIN_CHAT_ID,
        f"🔔 *Новая запись через Mini App!*\n\n"
        f"{service['name']} — *{service['price']}*\n"
        f"📅 Дата: *{body.date}* в *{body.time}*\n"
        f"👤 Клиент: *{body.client_name}*\n"
        f"📱 Телефон: *{body.phone}*"
    )

    return {"id": booking_id, "status": "confirmed"}


@app.get("/api/my-bookings")
def api_my_bookings(x_telegram_init_data: Optional[str] = Header(None)):
    user = get_user(x_telegram_init_data)
    rows = db.get_bookings_by_chat_id(user["id"])
    today = datetime.now().strftime("%Y%m%d")
    result = []
    for bid, b in rows:
        try:
            d, m, y = b["date"].split(".")
            sortable = y + m + d
        except Exception:
            sortable = ""
        if sortable >= today:
            svc = SERVICES.get(b["service"], {})
            result.append({"id": bid, "service_name": svc.get("name", b["service"]),
                           "service_price": svc.get("price", ""), **b})
    return result


@app.delete("/api/my-bookings/{booking_id}")
async def api_cancel_my_booking(
    booking_id: int,
    x_telegram_init_data: Optional[str] = Header(None),
):
    user = get_user(x_telegram_init_data)
    existing = db.get_booking(booking_id)
    if not existing or existing.get("chat_id") != user.get("id"):
        raise HTTPException(status_code=404, detail="Запись не найдена")

    service = SERVICES.get(existing["service"], {})
    db.delete_booking(booking_id)

    # Уведомление клиенту
    client_chat_id = user.get("id")
    if client_chat_id:
        await send_telegram_message(
            client_chat_id,
            f"❌ *Ваша запись отменена*\n\n"
            f"{service.get('name', '')}\n"
            f"📅 {existing['date']} в {existing['time']}\n\n"
            f"Если хотите записаться снова — мы всегда рады! 💖"
        )

    # Уведомление администратору
    await send_telegram_message(
        ADMIN_CHAT_ID,
        f"🚫 *Клиент отменил запись (Mini App)*\n\n"
        f"{service.get('name', '')}\n"
        f"📅 {existing['date']} в {existing['time']}\n"
        f"👤 {existing['client_name']} · 📱 {existing['phone']}"
    )

    return {"status": "cancelled"}


# ===== МАРШРУТЫ АДМИНИСТРАТОРА =====

@app.get("/api/admin/bookings")
def api_admin_bookings(x_telegram_init_data: Optional[str] = Header(None)):
    require_admin(x_telegram_init_data)
    rows = db.get_all_bookings()
    result = []
    for bid, b in sorted(rows, key=lambda x: (x[1]["date"].split(".")[::-1], x[1]["time"])):
        svc = SERVICES.get(b["service"], {})
        result.append({"id": bid, "service_name": svc.get("name", b["service"]),
                       "service_price": svc.get("price", ""), **b})
    return result


@app.delete("/api/admin/bookings/{booking_id}")
async def api_admin_cancel_booking(
    booking_id: int,
    x_telegram_init_data: Optional[str] = Header(None),
):
    require_admin(x_telegram_init_data)
    existing = db.get_booking(booking_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    service = SERVICES.get(existing["service"], {})
    db.delete_booking(booking_id)

    # Уведомление клиенту
    client_chat_id = existing.get("chat_id")
    if client_chat_id:
        await send_telegram_message(
            client_chat_id,
            f"❌ *Ваша запись отменена администратором*\n\n"
            f"{service.get('name', '')}\n"
            f"📅 {existing['date']} в {existing['time']}\n\n"
            f"Для уточнения деталей: {SALON_INFO['admin']} 💖"
        )

    # Уведомление администратору
    await send_telegram_message(
        ADMIN_CHAT_ID,
        f"🚫 *Запись отменена администратором*\n\n"
        f"{service.get('name', '')}\n"
        f"📅 {existing['date']} в {existing['time']}\n"
        f"👤 {existing['client_name']} · 📱 {existing['phone']}"
    )

    return {"status": "cancelled"}


@app.get("/api/admin/stats")
def api_admin_stats(x_telegram_init_data: Optional[str] = Header(None)):
    require_admin(x_telegram_init_data)
    all_bookings = db.get_all_bookings()
    all_reviews = db.get_all_reviews()
    total = len(all_bookings)
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    service_count, day_count, hour_count = {}, {}, {}

    for _, b in all_bookings:
        s = b["service"]
        service_count[s] = service_count.get(s, 0) + 1
        try:
            dt = datetime.strptime(b["date"], "%d.%m.%Y")
            day = day_names[dt.weekday()]
            day_count[day] = day_count.get(day, 0) + 1
        except ValueError:
            pass
        h = b.get("time", "?")
        hour_count[h] = hour_count.get(h, 0) + 1

    total_reviews = len(all_reviews)
    avg_rating = sum(r["stars"] for r in all_reviews) / total_reviews if total_reviews else 0

    return {
        "total_bookings": total,
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 1),
        "service_breakdown": [
            {"service_id": k, "service_name": SERVICES.get(k, {}).get("name", k),
             "count": v, "pct": round(v / total * 100) if total else 0}
            for k, v in sorted(service_count.items(), key=lambda x: -x[1])
        ],
        "day_breakdown": sorted(
            [{"day": k, "count": v} for k, v in day_count.items()],
            key=lambda x: -x["count"],
        ),
        "top_hours": sorted(
            [{"hour": k, "count": v} for k, v in hour_count.items()],
            key=lambda x: -x["count"],
        )[:5],
    }


@app.get("/api/admin/reviews")
def api_admin_reviews(x_telegram_init_data: Optional[str] = Header(None)):
    require_admin(x_telegram_init_data)
    return [
        {**r, "service_name": SERVICES.get(r["service"], {}).get("name", r["service"])}
        for r in db.get_all_reviews()
    ]


# ===== ОТДАЧА СТАТИЧЕСКИХ ФАЙЛОВ =====

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    target = os.path.join(STATIC_DIR, full_path)
    if full_path and os.path.isfile(target):
        return FileResponse(target)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))