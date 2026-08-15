from aiogram.fsm.state import State, StatesGroup


class ActivityForm(StatesGroup):
    waiting_for_quantity = State()
