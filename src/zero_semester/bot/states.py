from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_login = State()
    waiting_for_school = State()


class SecretStates(StatesGroup):
    waiting_for_secret = State()


class SupportStates(StatesGroup):
    waiting_for_message = State()
