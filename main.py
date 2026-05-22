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
    # ===== ЖЕНСКИЙ ПРАЙС =====

    # 🪒 ДЕПИЛЯЦИЯ ДОПОЛНИТЕЛЬНО
    "dep_pudra": {"name": "🪒 Пудра энзимная", "price": "60 руб", "duration": 10, "category": "💆 Депиляция (доп.)"},
    "dep_maska": {"name": "🪒 Противовоспалительная маска", "price": "60 руб", "duration": 10, "category": "💆 Депиляция (доп.)"},
    "dep_gel": {"name": "🪒 Обезболивающий гель", "price": "650 руб", "duration": 10, "category": "💆 Депиляция (доп.)"},

    # 🪒 ВОСКОВАЯ ДЕПИЛЯЦИЯ
    "vosk_telo": {"name": "🪒 Воск: Всё тело", "price": "1800–2100 руб", "duration": 90, "category": "🪒 Восковая депиляция"},
    "vosk_podm": {"name": "🪒 Воск: Подмышки", "price": "250–300 руб", "duration": 20, "category": "🪒 Восковая депиляция"},
    "vosk_bikini_tr": {"name": "🪒 Воск: Бикини трусики", "price": "350–400 руб", "duration": 20, "category": "🪒 Восковая депиляция"},
    "vosk_bikini_gl": {"name": "🪒 Воск: Бикини глубокое", "price": "550–700 руб", "duration": 30, "category": "🪒 Восковая депиляция"},
    "vosk_nogi_do": {"name": "🪒 Воск: Ноги до колен", "price": "500–550 руб", "duration": 30, "category": "🪒 Восковая депиляция"},
    "vosk_nogi_vyshe": {"name": "🪒 Воск: Ноги выше колен", "price": "500–550 руб", "duration": 30, "category": "🪒 Восковая депиляция"},
    "vosk_nogi_pol": {"name": "🪒 Воск: Ноги полностью", "price": "1000–1100 руб", "duration": 60, "category": "🪒 Восковая депиляция"},
    "vosk_ruki_do": {"name": "🪒 Воск: Руки до локтя", "price": "300–350 руб", "duration": 20, "category": "🪒 Восковая депиляция"},
    "vosk_ruki_pol": {"name": "🪒 Воск: Руки полностью", "price": "600–700 руб", "duration": 40, "category": "🪒 Восковая депиляция"},

    # 🪒 ПОЛИМЕРНЫЙ ВОСК
    "polvosk_telo": {"name": "🪒 Пол.воск: Всё тело", "price": "3250–3900 руб", "duration": 120, "category": "🪒 Полимерный воск"},
    "polvosk_lico": {"name": "🪒 Пол.воск: Область лица", "price": "200–250 руб", "duration": 15, "category": "🪒 Полимерный воск"},
    "polvosk_podm": {"name": "🪒 Пол.воск: Подмышки", "price": "350–400 руб", "duration": 20, "category": "🪒 Полимерный воск"},
    "polvosk_bikini_tr": {"name": "🪒 Пол.воск: Бикини трусики", "price": "500–600 руб", "duration": 25, "category": "🪒 Полимерный воск"},
    "polvosk_bikini_gl": {"name": "🪒 Пол.воск: Бикини глубокое", "price": "1100–1300 руб", "duration": 40, "category": "🪒 Полимерный воск"},
    "polvosk_nogi_pol": {"name": "🪒 Пол.воск: Ноги полностью", "price": "1800–2200 руб", "duration": 60, "category": "🪒 Полимерный воск"},

    # 🍬 ШУГАРИНГ
    "sugar_telo": {"name": "🍬 Шугаринг: Всё тело", "price": "2100–2550 руб", "duration": 120, "category": "🍬 Шугаринг"},
    "sugar_lico": {"name": "🍬 Шугаринг: Область лица", "price": "200–250 руб", "duration": 15, "category": "🍬 Шугаринг"},
    "sugar_podm": {"name": "🍬 Шугаринг: Подмышки", "price": "250–300 руб", "duration": 20, "category": "🍬 Шугаринг"},
    "sugar_bikini_tr": {"name": "🍬 Шугаринг: Бикини трусики", "price": "300–400 руб", "duration": 25, "category": "🍬 Шугаринг"},
    "sugar_bikini_gl": {"name": "🍬 Шугаринг: Бикини глубокое", "price": "850–950 руб", "duration": 40, "category": "🍬 Шугаринг"},
    "sugar_nogi_do": {"name": "🍬 Шугаринг: Ноги до колен", "price": "500–650 руб", "duration": 30, "category": "🍬 Шугаринг"},
    "sugar_nogi_pol": {"name": "🍬 Шугаринг: Ноги полностью", "price": "1000–1300 руб", "duration": 60, "category": "🍬 Шугаринг"},

    # 💧 AQUA ШУГАРИНГ
    "aqua_podm": {"name": "💧 Aqua шугаринг: Подмышки", "price": "350–400 руб", "duration": 20, "category": "💧 Aqua шугаринг"},
    "aqua_bikini_tr": {"name": "💧 Aqua шугаринг: Бикини трусики", "price": "600–700 руб", "duration": 25, "category": "💧 Aqua шугаринг"},
    "aqua_bikini_gl": {"name": "💧 Aqua шугаринг: Бикини глубокое", "price": "900–1250 руб", "duration": 40, "category": "💧 Aqua шугаринг"},
    "aqua_nogi_pol": {"name": "💧 Aqua шугаринг: Ноги полностью", "price": "1200–1400 руб", "duration": 60, "category": "💧 Aqua шугаринг"},

    # ⚡ ЛАЗЕРНАЯ ЭПИЛЯЦИЯ
    "lazer_podm_bikini": {"name": "⚡ Лазер: Подмышки + бикини глубокое", "price": "1700–2000 руб", "duration": 60, "category": "⚡ Лазерная эпиляция"},
    "lazer_telo": {"name": "⚡ Лазер: Подмышки + бикини + ноги полностью", "price": "5300–6000 руб", "duration": 120, "category": "⚡ Лазерная эпиляция"},
    "lazer_podm": {"name": "⚡ Лазер: Подмышки", "price": "500–600 руб", "duration": 20, "category": "⚡ Лазерная эпиляция"},
    "lazer_bikini_gl": {"name": "⚡ Лазер: Бикини глубокое", "price": "1200–1400 руб", "duration": 40, "category": "⚡ Лазерная эпиляция"},
    "lazer_nogi_pol": {"name": "⚡ Лазер: Ноги полностью", "price": "3600–4000 руб", "duration": 90, "category": "⚡ Лазерная эпиляция"},

    # 💅 МАНИКЮР
    "man_klass": {"name": "💅 Маникюр классический", "price": "700–800 руб", "duration": 60, "category": "💅 Маникюр"},
    "man_kombi": {"name": "💅 Маникюр комбинированный", "price": "800–900 руб", "duration": 60, "category": "💅 Маникюр"},
    "man_apparat": {"name": "💅 Маникюр аппаратный", "price": "850–950 руб", "duration": 60, "category": "💅 Маникюр"},
    "man_detsky": {"name": "💅 Маникюр детский (до 7 лет)", "price": "300–400 руб", "duration": 30, "category": "💅 Маникюр"},
    "man_yapon": {"name": "💅 Маникюр японский", "price": "1200–1400 руб", "duration": 75, "category": "💅 Маникюр"},
    "man_parafin": {"name": "💅 Парафинотерапия рук", "price": "400 руб", "duration": 20, "category": "💅 Маникюр"},

    # 💅 ПОКРЫТИЕ
    "pokr_lak": {"name": "💅 Покрытие лаком", "price": "300 руб", "duration": 20, "category": "💅 Покрытие"},
    "pokr_gel": {"name": "💅 Гель-лак", "price": "700–850 руб", "duration": 30, "category": "💅 Покрытие"},
    "pokr_gel_luxio": {"name": "💅 Гель-лак LUXIO", "price": "950–1050 руб", "duration": 30, "category": "💅 Покрытие"},
    "pokr_snyatie": {"name": "💅 Снятие гель-лака", "price": "400 руб", "duration": 20, "category": "💅 Покрытие"},

    # 💅 НАРАЩИВАНИЕ НОГТЕЙ
    "nar_ukrp": {"name": "💅 Укрепление гелем под гель-лак", "price": "500–600 руб", "duration": 40, "category": "💅 Наращивание"},
    "nar_noghi": {"name": "💅 Наращивание ногтей (любой дизайн)", "price": "2100–2250 руб", "duration": 120, "category": "💅 Наращивание"},
    "nar_snyatie": {"name": "💅 Снятие нарощенных ногтей", "price": "600 руб", "duration": 30, "category": "💅 Наращивание"},

    # 🦶 ПЕДИКЮР
    "ped_klass": {"name": "🦶 Педикюр классический", "price": "900–1000 руб", "duration": 60, "category": "🦶 Педикюр"},
    "ped_kombi": {"name": "🦶 Педикюр комбинированный", "price": "1000–1100 руб", "duration": 60, "category": "🦶 Педикюр"},
    "ped_apparat": {"name": "🦶 Педикюр аппаратный", "price": "1100–1200 руб", "duration": 60, "category": "🦶 Педикюр"},
    "ped_smart": {"name": "🦶 SMART-педикюр", "price": "1900–2300 руб", "duration": 90, "category": "🦶 Педикюр"},
    "ped_golden": {"name": "🦶 Педикюр Golden Trace", "price": "1800–2200 руб", "duration": 90, "category": "🦶 Педикюр"},

    # 👁 БРОВИ
    "brov_oform": {"name": "👁 Оформление бровей (пинцет/воск)", "price": "400–500 руб", "duration": 30, "category": "👁 Брови"},
    "brov_oform_kraska": {"name": "👁 Брови оформление + краска", "price": "800–1000 руб", "duration": 45, "category": "👁 Брови"},
    "brov_oform_hna": {"name": "👁 Брови оформление + хна", "price": "900–1100 руб", "duration": 45, "category": "👁 Брови"},
    "brov_lamin_sigma": {"name": "👁 Ламинирование бровей SIGMA", "price": "1400–1600 руб", "duration": 60, "category": "👁 Брови"},
    "brov_lamin_lami": {"name": "👁 Ламинирование бровей LAMI SMART", "price": "1800–2000 руб", "duration": 60, "category": "👁 Брови"},
    "brov_velvet": {"name": "👁 Вельвет бровей", "price": "2600–3000 руб", "duration": 75, "category": "👁 Брови"},

    # 👁 РЕСНИЦЫ
    "res_okrash": {"name": "👁 Окрашивание ресниц", "price": "300–400 руб", "duration": 20, "category": "👁 Ресницы"},
    "res_lamin_sigma": {"name": "👁 Ламинирование ресниц SIGMA", "price": "1700–1900 руб", "duration": 60, "category": "👁 Ресницы"},
    "res_lamin_lami": {"name": "👁 Ламинирование ресниц LAMI SMART", "price": "2000–2200 руб", "duration": 60, "category": "👁 Ресницы"},
    "res_nar_1d": {"name": "👁 Наращивание ресниц 1D", "price": "1500–1700 руб", "duration": 90, "category": "👁 Ресницы"},
    "res_nar_2d": {"name": "👁 Наращивание ресниц 2D", "price": "2100–2300 руб", "duration": 100, "category": "👁 Ресницы"},
    "res_nar_3d": {"name": "👁 Наращивание ресниц 3D", "price": "2300–2500 руб", "duration": 110, "category": "👁 Ресницы"},
    "res_snyatie": {"name": "👁 Снятие ресниц", "price": "350 руб", "duration": 20, "category": "👁 Ресницы"},

    # 💄 МАКИЯЖ
    "mak_express": {"name": "💄 Макияж Экспресс", "price": "1350–1450 руб", "duration": 45, "category": "💄 Макияж"},
    "mak_dnevnoy": {"name": "💄 Дневной макияж", "price": "1700–1800 руб", "duration": 60, "category": "💄 Макияж"},
    "mak_vecherny": {"name": "💄 Вечерний макияж", "price": "2300–2400 руб", "duration": 75, "category": "💄 Макияж"},
    "mak_slozhny": {"name": "💄 Сложный макияж", "price": "2550–2650 руб", "duration": 90, "category": "💄 Макияж"},
    "obraz_dnevnoy": {"name": "💄 Дневной образ", "price": "4200–4300 руб", "duration": 120, "category": "💄 Образ"},
    "obraz_vecherny": {"name": "💄 Вечерний образ", "price": "4800–4900 руб", "duration": 150, "category": "💄 Образ"},
    "obraz_prazdnik": {"name": "💄 Праздничный образ", "price": "5500–5600 руб", "duration": 180, "category": "💄 Образ"},

    # ✂️ ПАРИКМАХЕР
    "hair_striz_zhen": {"name": "✂️ Стрижка женская", "price": "1500–2000 руб", "duration": 60, "category": "✂️ Парикмахер"},
    "hair_striz_det": {"name": "✂️ Стрижка детская (до 7 лет)", "price": "700–1000 руб", "duration": 30, "category": "✂️ Парикмахер"},
    "hair_ukladka": {"name": "✂️ Укладка лёгкая", "price": "1000–1500 руб", "duration": 45, "category": "✂️ Парикмахер"},
    "hair_pricheska": {"name": "✂️ Причёска вечерняя", "price": "2000–4200 руб", "duration": 90, "category": "✂️ Парикмахер"},
    "hair_lokony": {"name": "✂️ Голливудские локоны", "price": "1800–2150 руб", "duration": 60, "category": "✂️ Парикмахер"},

    # 💆 ЛЕЧЕНИЕ ВОЛОС
    "vol_lebel_abs": {"name": "💆 Абсолютное счастье LEBEL (короткие)", "price": "3600–4000 руб", "duration": 60, "category": "💆 Лечение волос"},
    "vol_nanoplastika": {"name": "💆 Нанопластика (короткие)", "price": "3500–3900 руб", "duration": 90, "category": "💆 Лечение волос"},
    "vol_keratin": {"name": "💆 Кератиновое выпрямление (короткие)", "price": "3300–4500 руб", "duration": 120, "category": "💆 Лечение волос"},
    "vol_botox": {"name": "💆 Ботокс волос Honma Tokio (короткие)", "price": "3400–3900 руб", "duration": 90, "category": "💆 Лечение волос"},

    # 🎨 ОКРАШИВАНИЕ
    "okr_1ton": {"name": "🎨 Окрашивание в 1 тон (короткие)", "price": "3150–3800 руб", "duration": 90, "category": "🎨 Окрашивание"},
    "okr_slozh": {"name": "🎨 Сложное окрашивание (короткие)", "price": "4700–5450 руб", "duration": 120, "category": "🎨 Окрашивание"},
    "okr_airtouch": {"name": "🎨 Airtouch (короткие)", "price": "5800–7500 руб", "duration": 150, "category": "🎨 Окрашивание"},
    "okr_melir": {"name": "🎨 Мелирование (короткие)", "price": "2950–4300 руб", "duration": 90, "category": "🎨 Окрашивание"},

    # ===== МУЖСКОЙ ПРАЙС =====
    "muz_striz": {"name": "✂️ Стрижка мужская", "price": "1000–1300 руб", "duration": 45, "category": "👨 Мужской прайс"},
    "muz_striz_feyd": {"name": "✂️ Стрижка мужская + фейд", "price": "1300–1600 руб", "duration": 60, "category": "👨 Мужской прайс"},
    "muz_boroda": {"name": "✂️ Борода", "price": "500–700 руб", "duration": 30, "category": "👨 Мужской прайс"},
    "muz_brov": {"name": "👁 Оформление бровей (мужской)", "price": "450–550 руб", "duration": 20, "category": "👨 Мужской прайс"},
    "muz_manik": {"name": "💅 Маникюр мужской", "price": "1000–1100 руб", "duration": 45, "category": "👨 Мужской прайс"},
    "muz_pedik": {"name": "🦶 Педикюр мужской", "price": "1650–1800 руб", "duration": 60, "category": "👨 Мужской прайс"},
    "muz_lazer_podm": {"name": "⚡ Лазер (муж): Подмышки", "price": "800–1000 руб", "duration": 20, "category": "👨 Мужской прайс"},
    "muz_lazer_nogi": {"name": "⚡ Лазер (муж): Ноги полностью", "price": "4000–4400 руб", "duration": 90, "category": "👨 Мужской прайс"},
}

AVAILABLE_TIMES = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

SALON_INFO = {
    "name": "Салон красоты Sахар",
    "address": "г. Махачкала, ул. Ваххабитова 2к3",
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
