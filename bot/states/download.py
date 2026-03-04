from aiogram.fsm.state import State, StatesGroup


class DownloadFlow(StatesGroup):
    awaiting_format = State()

