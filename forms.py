from aiogram.dispatcher.filters.state import State, StatesGroup


class Form(StatesGroup):
    event_body = State()
    event_name = State()
    event_date = State()
    event_time = State()
