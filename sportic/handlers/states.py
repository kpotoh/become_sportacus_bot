from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    timezone = State()
    timezone_custom = State()
    workout_name = State()
    workout_name_custom = State()
    workout_interval = State()
    workout_interval_custom = State()
    workout_window = State()
    workout_window_custom = State()
    more_workouts = State()
    notifications = State()
    notification_add = State()


class AddWorkout(StatesGroup):
    name = State()
    name_custom = State()
    interval = State()
    interval_custom = State()
    window = State()
    window_custom = State()


class SettingsFlow(StatesGroup):
    timezone_custom = State()
    notifications = State()
    notification_add = State()
