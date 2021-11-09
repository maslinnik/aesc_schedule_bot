#-*- coding: utf-8 -*-

from aiogram import Bot, Dispatcher, executor
from aiogram.types import ParseMode, Message

from os import getenv
from datetime import date, time, datetime, timedelta
from typing import Optional, Any

import logging
import asyncio
import json

HOME_CHAT_ID: int = int(getenv("HOME_CHAT") or -1001542214018)

HELP_STRING: str = """
/schedule - расписание на сегодня
/tomorrow - расписание на завтра
/now - текущий урок
/next - следующий урок
/help - помощь
"""

DEFAULT_MESSAGE_PARAMS: dict[str, Any] = {
    "disable_web_page_preview": True
}

bot_token: str | None = getenv("BOT_TOKEN")
assert bot_token, "Token is not provided"

bot = Bot(
    token=bot_token,
    parse_mode=ParseMode.HTML
)

# Диспетчер для бота
dp = Dispatcher(bot)
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)


def get_lessons_time() -> list[tuple[time, time]]:
    "Get list of lesson start and end times"
    return [
        (
            time.fromisoformat(start),
            time.fromisoformat(end)
        )
        for start, end in json.load(open('data/lessons.json'))['time']
    ]


def get_lessons_info() -> dict[str, str]:
    "Get lessons information"
    return json.load(open('data/lessons.json'))['info']


def get_schedule() -> list[list[str]]:
    "Get list of lessons on weekdays"
    return json.load(open('data/lessons.json'))['schedule']


def get_current_lesson() -> Optional[int]:
    "Get index of current lesson"
    now: time = datetime.now().time()
    for i, (start_time, end_time) in enumerate(get_lessons_time()):
        if start_time <= now < end_time:
            return i
    return None


def get_next_lesson() -> Optional[int]:
    "Get index of next lesson"
    now: time = datetime.now().time()
    today_schedule: list[str] = get_schedule()[date.today().weekday()]
    for i, (start, _) in reversed(list(enumerate(get_lessons_time()[:len(today_schedule)]))):
        if now < start:
            return i

    return None


def get_schedule_representation(day: date) -> str:
    "Get human-readable schedule representation for specified day"
    current_lesson: Optional[int] = (
        get_current_lesson() if date.today() == date
        else None
    )
    lesson_times: list[tuple[time, time]] = get_lessons_time()

    return '\n'.join([
        (
            '<b>{}</b>' if i == current_lesson
            else '{}'
        ).format(
            (
                "{}. {} ({} - {})"
            ).format(
                i + 1,
                lesson,
                *map(lambda s: s.isoformat('minutes'), lesson_times[i])
            )
        )
        for i, lesson in enumerate(get_schedule()[day.weekday()])
    ])


def get_lesson_representation(weekday: int, lesson_index: int) -> str:
    "Get human-readable lesson representation"
    lesson: str = get_schedule()[weekday][lesson_index]
    return "{} ({} - {})\n\n{}".format(
        lesson,
        *map(lambda t: t.isoformat('minutes'), get_lessons_time()[lesson_index]),
        get_lessons_info()[lesson]
    )


@dp.message_handler(commands="help")
async def cmd_help(message: Message):
    "Handler for /help command"
    await message.answer(HELP_STRING, **DEFAULT_MESSAGE_PARAMS)


@dp.message_handler(commands="schedule")
async def cmd_schedule(message: Message):
    "Handler for /schedule command"
    await message.answer(
        get_schedule_representation(date.today()),
        **DEFAULT_MESSAGE_PARAMS
    )


@dp.message_handler(commands="tomorrow")
async def cmd_tomorrow(message: Message):
    "Handler for /tomorrow command"
    await message.answer(
        get_schedule_representation(date.today() + timedelta(days=1)),
        **DEFAULT_MESSAGE_PARAMS
    )


@dp.message_handler(commands="now")
async def cmd_now(message: Message):
    "Handler for /now command"
    weekday: int = date.today().weekday()
    lesson: Optional[int] = get_current_lesson()

    if lesson is None:
        await cmd_next(message)
    else:
        await message.reply(
            f'<b>Сейчас идёт:</b>\n\n'
                + get_lesson_representation(weekday, lesson),
            **DEFAULT_MESSAGE_PARAMS
        )


@dp.message_handler(commands="next")
async def cmd_next(message: Message):
    "Handler for /next command"
    weekday: int = date.today().weekday()
    lesson: Optional[int] = get_next_lesson()

    if lesson is None:
        await message.reply("<b>Сегодня больше нет уроков</b>", **DEFAULT_MESSAGE_PARAMS)
    else:
        await message.reply(
            f'<b>Следующий урок:</b>\n\n'
                + get_lesson_representation(weekday, lesson),
            **DEFAULT_MESSAGE_PARAMS
        )


async def notify_lesson(deltas: list[int]):
    lessons_time: list[tuple[time, time]] = get_lessons_time()

    now: datetime = datetime.now()

    next_lesson: Optional[int] = get_next_lesson()

    if next_lesson is None:
        return

    lesson_start: datetime = datetime.combine(
        date=now.date(),
        time=lessons_time[next_lesson][0]
    )

    time_comment: str

    for delta in deltas:
        minutes_left: int = (lesson_start - now).seconds // 60
        if (minutes_left == delta):
            time_comment = f'Через {(lesson_start - now).seconds // 60} минуты начнётся'
        else:
            time_comment = 'Сейчас начнётся'
        break
    else:
        return

    await bot.send_message(
        HOME_CHAT_ID,
        f'<b>{time_comment}:</b>\n\n' \
            + get_lesson_representation(now.weekday(), next_lesson),
        **DEFAULT_MESSAGE_PARAMS
    )

async def notify_lessons():
    while True:
        await notify_lesson([5, 0])
        await asyncio.sleep(60)

async def run_notifier(_):
    asyncio.create_task(notify_lessons())


if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=run_notifier
    )
