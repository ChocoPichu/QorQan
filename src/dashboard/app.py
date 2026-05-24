from functools import wraps

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from flask import Flask, jsonify, render_template, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.bot import keyboards, texts
from src.config import BOT_TOKEN, FLASK_SECRET
from src.database import db

app = Flask(__name__)
app.secret_key = FLASK_SECRET

limiter = Limiter(
    app=app,
    key_func=lambda: str(session.get("operator_id", get_remote_address())),
    default_limits=["200 per day", "60 per hour"],
)


def operator_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "operator_id" not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return wrapper


async def _notify_user(telegram_id: int, text: str, reply_markup=None):
    async with Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML")) as bot:
        await bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_markup)


def _get_user_lang(session_id: int) -> str:
    return db.get_user_lang(db.get_session_by_id(session_id)["telegram_id"])


@app.route("/")
def index():
    return render_template("index.html")


# --- AUTHENTICATION ROUTES ---
@app.route("/api/auth/me", methods=["GET"])
@limiter.limit("30 per minute")
def get_me():
    if "operator_id" in session:
        return jsonify({"status": "success", "operator_name": session["display_name"]})
    return jsonify({"status": "error", "message": "Not logged in"}), 401


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("10 per minute", key_func=get_remote_address)
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    operator = db.verify_operator(username, password)
    if operator:
        session["operator_id"] = operator["id"]
        session["display_name"] = operator["display_name"]
        return jsonify({"status": "success", "operator_name": operator["display_name"]})

    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route("/api/auth/logout", methods=["POST"])
@limiter.limit("10 per minute")
def logout():
    session.clear()
    return jsonify({"status": "success"})


# --- DASHBOARD ROUTES (Protected) ---
@app.route("/api/tickets", methods=["GET"])
@limiter.limit("30 per minute")
@operator_required
def get_tickets():
    operator_id = session["operator_id"]

    # --- PHASE 6 HEARTBEAT ---
    # This tells the DB the operator is still active every 3 seconds, you could tweak this if you need to.
    db.update_operator_presence(operator_id)

    tickets = db.get_dashboard_tickets(operator_id)
    return jsonify({"status": "success", "tickets": tickets})


@app.route("/api/ticket/accept", methods=["POST"])
@limiter.limit("10 per minute")
@operator_required
async def accept_ticket():
    data = request.json
    session_id = data.get("session_id")
    operator_id = session["operator_id"]

    if not session_id:
        return jsonify({"status": "error", "message": "Missing ID"}), 400

    db.update_session_status(session_id, status="active", operator_id=operator_id)
    lang = _get_user_lang(session_id)

    try:
        await _notify_user(
            db.get_session_by_id(session_id)["telegram_id"],
            texts.LANGUAGES[lang]["chat_accepted"],
            reply_markup=keyboards.get_kid_close_menu(lang),
        )
        return jsonify({"status": "success", "message": "Ticket accepted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/ticket/close", methods=["POST"])
@limiter.limit("10 per minute")
@operator_required
async def close_ticket():
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"status": "error"}), 400

    db.update_session_status(session_id, status="closed")
    lang = _get_user_lang(session_id)

    try:
        await _notify_user(
            db.get_session_by_id(session_id)["telegram_id"],
            texts.LANGUAGES[lang]["chat_closed_op"],
            reply_markup=keyboards.get_main_menu(lang),
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/messages/<int:session_id>", methods=["GET"])
@limiter.limit("30 per minute")
@operator_required
def get_messages(session_id):
    messages = db.get_session_messages(session_id)
    return jsonify({"status": "success", "messages": messages})


@app.route("/api/messages/mark_read", methods=["POST"])
@limiter.limit("30 per minute")
@operator_required
def mark_messages_read():
    data = request.json
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"status": "error", "message": "Missing session_id"}), 400

    db.mark_messages_read(session_id)
    return jsonify({"status": "success"})


@app.route("/api/messages/send", methods=["POST"])
@limiter.limit("20 per minute")
@operator_required
async def send_message():
    data = request.json
    session_id = data.get("session_id")
    text = data.get("text")

    if not session_id or not text:
        return jsonify({"status": "error"}), 400

    db.add_message(session_id=session_id, sender_type="operator", text=text)

    try:
        await _notify_user(
            db.get_session_by_id(session_id)["telegram_id"],
            text,
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- PHASE 3: BLACKLIST / BAN HAMMER ---
@app.route("/api/blacklist", methods=["GET"])
@limiter.limit("20 per minute")
@operator_required
def get_blacklist():
    banned = db.get_blacklist()
    return jsonify({"status": "success", "blacklist": banned})


@app.route("/api/user/ban", methods=["POST"])
@limiter.limit("5 per minute")
@operator_required
def ban_user():
    data = request.json
    session_id = data.get("session_id")
    reason = data.get("reason", "No reason provided").strip() or "No reason provided"

    if not session_id:
        return jsonify({"status": "error", "message": "Missing session_id"}), 400

    session_data = db.get_session_by_id(session_id)
    if not session_data:
        return jsonify({"status": "error", "message": "Session not found"}), 404

    with db._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (session_data["telegram_id"],))
        user = cursor.fetchone()

    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    db.ban_user(
        telegram_id=user["telegram_id"],
        full_name=user["full_name"],
        username=user["username"],
        reason=reason,
        banned_by=session["display_name"],
    )
    db.update_session_status(session_id, status="closed")
    return jsonify({"status": "success", "message": f"{user['full_name']} has been banned."})


@app.route("/api/user/unban", methods=["POST"])
@limiter.limit("5 per minute")
@operator_required
def unban_user():
    data = request.json
    telegram_id = data.get("telegram_id")
    if not telegram_id:
        return jsonify({"status": "error", "message": "Missing telegram_id"}), 400

    db.unban_user(telegram_id)
    return jsonify({"status": "success", "message": "User unbanned."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
