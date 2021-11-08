#!venv/bin/python
import logging
from aiogram import Bot, Dispatcher, executor, types
from os import getenv
from sys import exit
import datetime
import json

bot_token = getenv("BOT_TOKEN")
if not bot_token:
    exit("Error: no token provided")

bot = Bot(token=bot_token)


# Диспетчер для бота
dp = Dispatcher(bot)
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)


weekdays = {0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"}


def get_weekday():
    return weekdays[datetime.datetime.today().weekday()]


def get_time():
    return datetime.datetime.now().hour * 60 + datetime.datetime.now().minute


def get_readable_time(time):
    return "{hh}:{mm}".format(hh=str(time // 60), mm=("" if time % 60 >= 10 else "0") + str(time % 60))


def get_lesson_time():
    curr_time = get_time()
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
        for i, start in enumerate(lesson_time["lessons"]):
            if int(start) <= curr_time <= int(start) + 45:
                return i
        return len(lesson_time["lessons"])


def get_last_lesson_time():
    curr_time = get_time()
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
        for i, start in reversed(list(enumerate(lesson_time["lessons"]))):
            if int(start) <= curr_time:
                return i
        return -1


def get_lesson_start(i):
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
        if i < len(lesson_time["lessons"]):
            return lesson_time["lessons"][i]
        else:
            return 0


@dp.message_handler(commands="test")
async def cmd_test(message: types.Message):
    await message.answer(str(get_last_lesson_time()))


@dp.message_handler(commands="schedule")
async def cmd_schedule(message: types.Message):
    answer = ""
    curr_lesson_time = get_lesson_time()
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        for i, subject in enumerate(schedule[get_weekday()]):
            if curr_lesson_time == i:
                answer += "<b>{i}. {subject}</b>\n".format(i=i + 1, subject=subject)
            else:
                answer += "{i}. {subject}\n".format(i=i + 1, subject=subject)
    await message.answer(answer, parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="current")
async def cmd_current(message: types.Message):
    curr_lesson_time = get_lesson_time()
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        today_schedule = schedule[get_weekday()]
    if curr_lesson_time < len(today_schedule):
        curr_lesson = today_schedule[curr_lesson_time]
        answer = "Now running:\n"
        lesson_start = get_readable_time(get_lesson_start(curr_lesson_time))
        lesson_end = get_readable_time(get_lesson_start(curr_lesson_time) + 45)
        answer += "{lesson} ({start_time} - {end_time})\n".format(lesson=curr_lesson, start_time=lesson_start,
                                                                  end_time=lesson_end)
    else:
        answer = "No lesson is running now\n"
    await message.answer(answer, parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="next")
async def cmd_next(message: types.Message):
    curr_next_lesson_time = get_last_lesson_time() + 1
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        today_schedule = schedule[get_weekday()]
    if curr_next_lesson_time < len(today_schedule):
        curr_lesson = today_schedule[curr_next_lesson_time]
        answer = "Next lesson:\n"
        lesson_start = get_readable_time(get_lesson_start(curr_next_lesson_time))
        lesson_end = get_readable_time(get_lesson_start(curr_next_lesson_time) + 45)
        answer += "{lesson} ({start_time} - {end_time})\n".format(lesson=curr_lesson, start_time=lesson_start,
                                                                  end_time=lesson_end)
    else:
        answer = "There are no more lessons today\n"
    await message.answer(answer, parse_mode=types.ParseMode.HTML)


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
