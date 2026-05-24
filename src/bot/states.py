# states.py
from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    choosing_urgency = State()
    waiting_for_operator = State()
    in_chat = State()
