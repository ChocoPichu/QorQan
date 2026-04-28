# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from texts import LANGUAGES

def get_main_menu(lang='ru'):
    t = LANGUAGES[lang]
    buttons = [
        [KeyboardButton(text=t['btn_about']), KeyboardButton(text=t['btn_lang'])],
        [KeyboardButton(text=t['btn_tips']), KeyboardButton(text=t['btn_chat'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_lang_menu():
    buttons = [
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton(text="Қазақша 🇰🇿", callback_data="lang_kz")],
        [InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_urgency_menu(lang='ru'):
    t = LANGUAGES[lang]
    buttons = [
        [InlineKeyboardButton(text=t['btn_danger'], callback_data="urgency_danger")],
        [InlineKeyboardButton(text=t['btn_safe'], callback_data="urgency_safe")],
        # МҰНДА ТҮЗЕТІЛДІ: urgency_notsure
        [InlineKeyboardButton(text=t['btn_not_sure'], callback_data="urgency_notsure")],
        [InlineKeyboardButton(text=t['btn_cancel'], callback_data="urgency_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_waiting_menu(lang='ru'):
    t = LANGUAGES[lang]
    buttons = [
        [InlineKeyboardButton(text=t['btn_game'], web_app=WebAppInfo(url="https://tbot.xyz/lumber/"))],
        [InlineKeyboardButton(text=t['btn_cancel_wait'], callback_data="cancel_waiting")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_kid_close_menu(lang='ru'):
    t = LANGUAGES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t['btn_close'], callback_data="kid_close_chat")
    ]])