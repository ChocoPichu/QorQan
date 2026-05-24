# states.py
from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    choosing_urgency = State() # choosing urgency
    waiting_for_operator = State() # kid waiting
    in_chat = State() # operator accepted
