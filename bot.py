#!venv/bin/python
import logging
import asyncio
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


def get_weekday(shift=0):
    return (datetime.datetime.today().weekday() + shift) % 7 + 1


def get_time():
    return datetime.datetime.now().hour, datetime.datetime.now().minute


def get_readable_time(time):
    return "{hh}:{mm}".format(hh=str(time[0]), mm=("" if time[1] >= 10 else "0") + str(time[1]))


def get_normalised_time(time):
    return time[0] * 60 + time[1]


def get_curr_lesson_number():
    curr_hour, curr_min = get_time()
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
    for i, time in sorted(lesson_time.items()):
        start, end = time
        if get_normalised_time(start) <= get_normalised_time((curr_hour, curr_min)) <= get_normalised_time(end):
            return int(i)
    return 9


def get_last_lesson_number():
    curr_hour, curr_min = get_time()
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
    for i, time in sorted(lesson_time.items(), reverse=True):
        start = time[0]
        if get_normalised_time(start) <= get_normalised_time((curr_hour, curr_min)):
            return int(i)
    return -1


def get_lesson_time(i):
    with open("data/lesson_time.json") as json_lesson_time:
        lesson_time = json.load(json_lesson_time)
    return lesson_time[str(i)]


# @dp.message_handler(commands="test")
# async def cmd_test(message: types.Message):
#     await message.answer(str(get_last_lesson_time()))


@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    s = "Привет! Я бот, который сообщает расписание 10В.\n"
    s += "За 5 и за 1 минуту до урока я автоматически пришлю ссылку на него.\n"
    s += "Также можно получить информацию командами:\n"
    s += "/schedule - расписание на сегодня\n"
    s += "/tomorrow - расписание на завтра\n"
    s += "/now - текущий урок\n"
    s += "/next - следующий урок\n"
    s += "/help - помощь\n"
    await message.answer(s, parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="schedule")
async def cmd_schedule(message: types.Message):
    ans = ""
    curr_lesson_number = get_curr_lesson_number()
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
    if len(schedule[str(get_weekday())]) != 0:
        for i, subject in schedule[str(get_weekday())].items():
            if curr_lesson_number == i:
                start, end = get_lesson_time(i)
                ans += "<b>{i}. {subject} ({start_time} - {end_time})</b>\n".format(i=i, subject=subject,
                                                                                    start_time=get_readable_time(start),
                                                                                    end_time=get_readable_time(end))
            else:
                start, end = get_lesson_time(i)
                ans += "{i}. {subject} ({start_time} - {end_time})\n".format(i=i, subject=subject,
                                                                                    start_time=get_readable_time(start),
                                                                                    end_time=get_readable_time(end))
    else:
        ans += "Сегодня нет уроков\n"
    await message.answer(ans, parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="tomorrow")
async def cmd_tomorrow(message: types.Message):
    ans = ""
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
    if len(schedule[str(get_weekday(1))]) != 0:
        for i, subject in schedule[str(get_weekday(1))].items():
            start, end = get_lesson_time(i)
            ans += "{i}. {subject} ({start_time} - {end_time})\n".format(i=i, subject=subject,
                                                                         start_time=get_readable_time(start),
                                                                         end_time=get_readable_time(end))
    else:
        ans = "Завтра нет уроков\n"
    await message.answer(ans, parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="now")
async def cmd_now(message: types.Message):
    curr_lesson_number = get_curr_lesson_number()
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        today_schedule = schedule[str(get_weekday())]
    with open("data/lesson_specifiers.json") as json_specifiers:
        specifiers = json.load(json_specifiers)
    if curr_lesson_number <= len(today_schedule):
        ans = "Сейчас идёт:\n"
        curr_subject = today_schedule[str(curr_lesson_number)]
        start, end = get_lesson_time(curr_lesson_number)
        ans += "<b>{subject}</b> ({start_time} - {end_time})\n".format(subject=curr_subject,
                                                                       start_time=get_readable_time(start),
                                                                       end_time=get_readable_time(end))
        ans += specifiers[curr_subject]
    else:
        ans = "Сейчас нет урока\n"
    await message.answer(ans, parse_mode=types.ParseMode.HTML, disable_web_page_preview=True)


@dp.message_handler(commands="next")
async def cmd_next(message: types.Message):
    next_lesson_number = get_last_lesson_number() + 1
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        today_schedule = schedule[str(get_weekday())]
    with open("data/lesson_specifiers.json") as json_specifiers:
        specifiers = json.load(json_specifiers)
    if next_lesson_number <= len(today_schedule):
        ans = "Следующий урок:\n"
        next_subject = today_schedule[str(next_lesson_number)]
        start, end = get_lesson_time(next_lesson_number)
        ans += "<b>{subject}</b> ({start_time} - {end_time})\n".format(subject=next_subject,
                                                                       start_time=get_readable_time(start),
                                                                       end_time=get_readable_time(end))
        ans += specifiers[next_subject]
    else:
        ans = "Сегодня больше нет уроков\n"
    await message.answer(ans, parse_mode=types.ParseMode.HTML, disable_web_page_preview=True)


@dp.message_handler(commands="lesson_test")
async def cmd_lesson_test(message: types.Message):
    weekday, req_lesson_number = map(int, message.text.split()[1:])
    with open("data/schedule.json") as json_schedule:
        schedule = json.load(json_schedule)
        req_schedule = schedule[str(weekday)]
    with open("data/lesson_specifiers.json") as json_specifiers:
        specifiers = json.load(json_specifiers)
    if req_lesson_number <= len(req_schedule):
        req_subject = req_schedule[str(req_lesson_number)]
        ans = ""
        start, end = get_lesson_time(req_lesson_number)
        ans += "<b>{subject}</b> ({start_time} - {end_time})\n".format(subject=req_subject,
                                                                       start_time=get_readable_time(start),
                                                                       end_time=get_readable_time(end))
        ans += specifiers[req_subject]
    else:
        ans = "error"
    await message.answer(ans, parse_mode=types.ParseMode.HTML, disable_web_page_preview=True)


async def periodic(delta):  # delta in min
    while True:
        with open("data/lesson_time.json") as json_lesson_time:
            lesson_time = json.load(json_lesson_time)
        with open("data/schedule.json") as json_schedule:
            schedule = json.load(json_schedule)
            today_schedule = schedule[str(get_weekday())]
        with open("data/lesson_specifiers.json") as json_specifiers:
            specifiers = json.load(json_specifiers)
        curr_time = get_time()
        for i, subject in today_schedule.items():
            if get_normalised_time(curr_time) + delta + 1 == get_normalised_time(lesson_time[i][0]):
                start, end = get_lesson_time(i)
                if delta > 0:
                    answer = "Через {delta} минут начнётся\n" \
                             "<b>{subject}</b> ({start_time} - {end_time})\n".format(delta=delta,
                                                                                     subject=subject,
                                                                                     start_time=get_readable_time(start),
                                                                                     end_time=get_readable_time(end))
                else:
                    answer = "Сейчас начнётся\n" \
                             "<b>{subject}</b> ({start_time} - {end_time})\n".format(subject=subject,
                                                                                     start_time=get_readable_time(start),
                                                                                     end_time=get_readable_time(end))
                answer += specifiers[subject]
                await bot.send_message(-1001542214018, answer,
                                       disable_web_page_preview=True, parse_mode=types.ParseMode.HTML)
        await asyncio.sleep(60)


async def on_startup(_):
    asyncio.create_task(periodic(5))
    asyncio.create_task(periodic(0))


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
