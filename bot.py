#-*- coding: utf-8 -*-

from aiogram import Bot, Dispatcher, executor
from aiogram.types import ParseMode, Message

from os import getenv
from datetime import date, time, datetime, timedelta
from typing import Optional

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

bot_token: str | None = getenv("BOT_TOKEN")
assert bot_token, "Token is not provided"

bot = Bot(token=bot_token)

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
    for i, (start, _) in reversed(list(enumerate(get_lessons_time()))):
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

    return '/n'.join([
        (
            '**{}**' if i == current_lesson
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


def get_lesson_representation(weekday: int, lesson: int) -> str:
    "Get human-readable lesson representation"
    return "{} ({} - {})\n\n{}".format(
        lesson,
        *map(lambda t: t.isoformat('minutes'), get_lessons_time()[lesson]),
        get_lessons_info()[get_schedule()[weekday][lesson]]
    )


@dp.message_handler(commands="help")
async def cmd_help(message: Message):
    "Handler for /help command"
    await message.answer(HELP_STRING, parse_mode=ParseMode.HTML)


@dp.message_handler(commands="schedule")
async def cmd_schedule(message: Message):
    "Handler for /schedule command"
    await message.answer(
        get_schedule_representation(date.today()),
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message_handler(commands="tomorrow")
async def cmd_tomorrow(message: Message):
    "Handler for /tomorrow command"
    await message.answer(
        get_schedule_representation(date.today() + timedelta(days=1)),
        parse_mode=ParseMode.MARKDOWN
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
            f'**Сейчас идёт:**\n\n' \
                + get_lesson_representation(weekday, lesson),
            parse_mode=ParseMode.MARKDOWN
        )


@dp.message_handler(commands="next")
async def cmd_next(message: Message):
    "Handler for /next command"
    weekday: int = date.today().weekday()
    lesson: Optional[int] = get_next_lesson()

    if lesson is None:
        await message.reply(
            "**Сегодня больше нет уроков**",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply(
            f'**Следующий урок:**\n\n' \
                + get_lesson_representation(weekday, lesson),
            parse_mode=ParseMode.MARKDOWN
        )


async def notify_lesson(deltas: list[timedelta]):
    while True:
        lessons_time: list[tuple[time, time]] = get_lessons_time()
        today_schedule: list[str] = get_schedule()[date.today().weekday()]

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
            if (now + delta).time() >= lessons_time[next_lesson][0]:
                minutes_left: int = (lesson_start - now).seconds // 60
                if (minutes_left > 0):
                    time_comment = f'Через {(lesson_start - now).seconds // 60} начнётся'
                else:
                    time_comment = 'Сейчас начнётся'
                break
        else:
            return

        await bot.send_message(
            HOME_CHAT_ID,
            f'**{time_comment}:**\n\n' \
                + get_lesson_representation(now.weekday(), next_lesson),
            parse_mode=ParseMode.MARKDOWN
        )

async def notify_lessons(_):
    while True:
        asyncio.create_task(notify_lesson([
            timedelta(minutes=5)
        ]))
        await asyncio.sleep(60)


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=notify_lessons
    )
