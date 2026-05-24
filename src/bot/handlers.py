from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot import keyboards, texts
from src.bot.states import UserState
from src.database import db

router = Router()


def _format_user(user):
    return f"@{user.username}" if user.username else "No Username"


async def get_lang(state: FSMContext):
    data = await state.get_data()
    return data.get("lang", "ru")


# --- 1. SELECT LANGUAGE ---


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[1]
    await state.update_data(lang=lang_code)
    user = callback.from_user
    db.upsert_user(telegram_id=user.id, full_name=user.full_name, username=_format_user(user), lang=lang_code)
    t = texts.LANGUAGES[lang_code]
    await callback.message.answer(t["start"], reply_markup=keyboards.get_main_menu(lang_code))
    await callback.answer()


# --- 2. MAIN MENU ---

_INFO_REPLIES = {}
_LANG_BUTTONS = set()
for _lc in ("ru", "kz", "en"):
    _t = texts.LANGUAGES[_lc]
    _INFO_REPLIES[_t["btn_about"]] = _t["about"]
    _INFO_REPLIES[_t["btn_tips"]] = _t["tips"]
    _INFO_REPLIES[_t["btn_lang"]] = _t["lang_select"]
    _LANG_BUTTONS.add(_t["btn_lang"])


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang")
    if not lang:
        await message.answer(
            "👋 Привет / Сәлем / Hello!\n\nПожалуйста, выберите язык:\nТілді таңдаңыз:\nPlease choose your language:",
            reply_markup=keyboards.get_lang_menu(),
        )
        return
    await state.set_state(None)
    await state.update_data(lang=lang)
    await message.answer(texts.LANGUAGES[lang]["start"], reply_markup=keyboards.get_main_menu(lang))


@router.message(F.text.in_(list(_INFO_REPLIES)))
async def info_handler(message: Message, state: FSMContext):
    kwargs = {"reply_markup": keyboards.get_lang_menu()} if message.text in _LANG_BUTTONS else {}
    await message.answer(_INFO_REPLIES[message.text], **kwargs)


# --- 3. CONTACTING THE OPERATOR ---

_CHAT_BUTTONS = {texts.LANGUAGES[lc]["btn_chat"] for lc in ("ru", "kz", "en")}


@router.message(F.text.in_(list(_CHAT_BUTTONS)))
async def support_handler(message: Message, state: FSMContext):
    lang = await get_lang(state)
    t = texts.LANGUAGES[lang]

    if db.is_banned(message.from_user.id):
        await message.answer(t["banned"])
        return

    active_session = db.get_active_session(message.from_user.id)
    if active_session:
        status = active_session["status"]
        if status == "waiting":
            await message.answer(t["already_waiting"])
            return
        elif status == "active":
            await message.answer(t["already_active"])
            return

    online_count = db.get_online_operators_count()
    if online_count == 0:
        await message.answer(t["no_operators"])

    await state.set_state(UserState.choosing_urgency)
    await message.answer(t["urgency"], reply_markup=keyboards.get_urgency_menu(lang))


@router.callback_query(UserState.choosing_urgency, F.data.startswith("urgency_"))
async def urgency_callback(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(state)
    t = texts.LANGUAGES[lang]
    action = callback.data.split("_")[1]

    if action == "cancel":
        await state.clear()
        await state.update_data(lang=lang)
        await callback.message.edit_text(t["cancel_success"])
        await callback.answer()
        return

    user = callback.from_user
    db.upsert_user(telegram_id=user.id, full_name=user.full_name, username=_format_user(user), lang=lang)
    session_id = db.create_session(telegram_id=user.id, urgency=action)

    online_count = db.get_online_operators_count()
    if online_count >= 10:
        time_str = t["time_3"]
    elif online_count >= 5:
        time_str = t["time_5"]
    elif online_count >= 1:
        time_str = t["time_10"]
    else:
        time_str = t["time_unknown"]

    await state.set_state(UserState.waiting_for_operator)
    await state.update_data(session_id=session_id)
    await callback.message.edit_text(
        t["wait"].format(wait_time=time_str),
        reply_markup=keyboards.get_waiting_menu(lang),
    )
    await callback.answer()


# --- 4. WAITING ROOM ---


@router.callback_query(F.data == "cancel_waiting")
async def cancel_waiting_callback(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(state)
    t = texts.LANGUAGES[lang]

    current_state = await state.get_state()
    if current_state == UserState.waiting_for_operator.state:
        data = await state.get_data()
        session_id = data.get("session_id")
        if session_id:
            db.update_session_status(session_id=session_id, status="closed")

        await state.clear()
        await state.update_data(lang=lang)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(t["cancel_success"], reply_markup=keyboards.get_main_menu(lang))
        await callback.answer()
    else:
        await callback.answer("Қате / Error", show_alert=True)


# --- 5. RECEIVING MESSAGES DURING ACTIVE SESSION ---


@router.message(F.text & ~F.text.startswith("/"))
async def ingest_kid_message(message: Message, state: FSMContext):
    lang = await get_lang(state)
    t = texts.LANGUAGES[lang]
    active_session = db.get_active_session(message.from_user.id)
    if not active_session:
        await message.answer(texts.LANGUAGES[lang]["start"], reply_markup=keyboards.get_main_menu(lang))
        return

    status = active_session["status"]
    if status == "waiting":
        await message.answer(t["wait_block"])
        return

    if status == "active":
        session_id = active_session["id"]
        text = message.text or message.caption
        photo_id = message.photo[-1].file_id if message.photo else None
        db.add_message(session_id=session_id, sender_type="kid", text=text, photo_id=photo_id)


# --- 6. CLOSE CHAT ---


@router.callback_query(F.data == "kid_close_chat")
async def close_session_handler(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(state)
    t = texts.LANGUAGES[lang]
    active_session = db.get_active_session(callback.from_user.id)
    if active_session:
        db.update_session_status(session_id=active_session["id"], status="closed")

    await state.clear()
    await state.update_data(lang=lang)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t["chat_closed_kid"], reply_markup=keyboards.get_main_menu(lang))
    await callback.answer()
