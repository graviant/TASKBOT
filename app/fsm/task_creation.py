# fsm/task_creation.py
from aiogram.fsm.state import StatesGroup, State


class TaskCreation(StatesGroup):
    work_type = State()
    deadline = State()
    project = State()
    customer = State()
    total_volume = State()
    comment = State()

# НОВОЕ: FSM для «взять задание»
class ClaimTask(StatesGroup):
    volume = State()
