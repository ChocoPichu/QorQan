# states.py
from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    # Kid clicked "Contact Operator", now looking at the Urgency buttons
    choosing_urgency = State()

    # Kid answered urgency, now waiting. Anything typed here is saved/forwarded
    waiting_for_operator = State()

    # Operator pressed "Accept". Direct chat is now open!
    in_chat = State()
