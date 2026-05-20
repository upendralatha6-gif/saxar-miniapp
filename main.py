import os
import hmac
import hashlib
import json
import urllib.parse
import logging
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
DEV_MODE = not TELEGRAM_BOT_TOKEN  # Если токен не задан — режим разработки

SERVICES = {
    "manicure": {"name": "💅 Маникюр", "price": "Бесплатно", "duration": 60},
    "pedicure": {"name": "🦶 Педикюр", "price": "50 000 руб", "duration": 90},
    "eyebrows": {"name": "🤨 Брови", "price": "500 000 руб", "duration": 45},
}

AVAILABLE_TIMES = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

SALON_INFO = {
    "name": "Салон красоты Sахар 💖",
    "address": "г. Махачкала",
    "phone": "+89681234567",
    "admin": "@coachgnv",
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


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
def api_create_booking(
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
def api_cancel_my_booking(
    booking_id: int,
    x_telegram_init_data: Optional[str] = Header(None),
):
    user = get_user(x_telegram_init_data)
    existing = db.get_booking(booking_id)
    if not existing or existing.get("chat_id") != user.get("id"):
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete_booking(booking_id)
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
def api_admin_cancel_booking(
    booking_id: int,
    x_telegram_init_data: Optional[str] = Header(None),
):
    require_admin(x_telegram_init_data)
    deleted = db.delete_booking(booking_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
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
