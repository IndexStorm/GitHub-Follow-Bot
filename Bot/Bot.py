import logging
import aiosqlite
import re
import random
import time
import datetime
import asyncio
import pytz
import aiogram.utils.markdown as md

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler


from GitApi import validate_username, check_follows_direct
from Distribution import creat_pools, create_groups, send_messages, create_group_for_user
import Database
import Localize

# Create token: https://core.telegram.org/bots
API_TOKEN = 'TELEGRAM_BOT_TOKEN'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    set_language = State()
    git_url = State()


async def pipeline():
    await creat_pools()
    groups = await create_groups()
    await send_messages(groups)


async def pipeline_for_user(send_id: int):
    send_git = await Database.get_git_from_telegram(send_id)
    group = await create_group_for_user(send_id, send_git)
    await send_messages(group)


@dp.message_handler(Text(equals='My GitHub', ignore_case=True))
@dp.message_handler(Text(equals='Мой GitHub', ignore_case=True))
async def get_git(message: types.Message):
    try:
        user_id = message.chat.id
    except:
        await message.answer("Error with user_id")
        return
    if message.text.lower() == "my github":
        user_locale = 'en'
    else:
        user_locale = 'ru'

    username = await Database.get_git_from_telegram(user_id)
    if username:
        await message.answer(Localize.YourGithub[user_locale].format(username=username))
    else:
        await message.answer(Localize.NoGithub[user_locale])


@dp.message_handler(Text(equals='Rules', ignore_case=True))
@dp.message_handler(Text(equals='Правила', ignore_case=True))
async def rules(message: types.Message):
    if message.text.lower() == "rules":
        user_locale = 'en'
    else:
        user_locale = 'ru'
    utc_hour = datetime.datetime.now(pytz.timezone('UTC')).hour
    london = 12 + datetime.datetime.now(pytz.timezone('Europe/London')).hour - utc_hour
    moscow = 12 + datetime.datetime.now(pytz.timezone('Europe/Moscow')).hour - utc_hour
    la = 12 + datetime.datetime.now(pytz.timezone('America/Los_Angeles')).hour - utc_hour
    await message.answer(Localize.Rules[user_locale].format(london=london, moscow=moscow, la=la))


@dp.message_handler(Text(equals='Change GitHub Profile', ignore_case=True))
@dp.message_handler(Text(equals='Изменить профиль GitHub', ignore_case=True))
async def change_git(message: types.Message):
    if message.text.lower() == 'change github profile':
        user_locale = 'en'
    else:
        user_locale = 'ru'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    if user_locale == 'en':
        markup.add("Cancel")
    else:
        markup.add("Отмена")
    await message.answer(Localize.ChangingGit[user_locale], reply_markup=markup)
    await Form.git_url.set()


@dp.message_handler(Text(equals="Today's list", ignore_case=True))
@dp.message_handler(Text(equals='Список на сегодня', ignore_case=True))
async def today_list(message: types.Message):
    try:
        user_id = message.chat.id
    except:
        await message.answer("Error with user_id")
        return
    user_locale = await Database.get_user_locale(user_id)
    to_follow_list = await Database.get_to_follow_list(user_id)
    str_to_send = ""
    # make a list of people to follow
    for i in range(len(to_follow_list)):
        str_to_send += f"{i}. https://github.com/{to_follow_list[i]}\n"
    if str_to_send != "":
        await message.answer(Localize.YourList[user_locale].format(str_to_send=str_to_send))
    else:
        await message.answer(Localize.NoList[user_locale])


@dp.message_handler(Text(equals='Cancel', ignore_case=True), state=Form.git_url)
@dp.message_handler(Text(equals='Отмена', ignore_case=True), state=Form.git_url)
async def cancel_git(message: types.Message, state: FSMContext):
    try:
        user_id = message.chat.id
    except:
        await message.answer("Error with user_id")
        return

    user_locale = await Database.get_user_locale(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    if user_locale == 'en':
        markup.add("Today's list", "Rules")
        markup.add("My GitHub", "Change GitHub Profile", "Contact Us")
    else:
        markup.add("Список на сегодня", "Правила")
        markup.add("Мой GitHub", "Изменить профиль GitHub",
                   "Обратная связь")

    await message.answer(Localize.CancelChangingGit[user_locale], reply_markup=markup)
    await state.finish()


@dp.message_handler(Text(equals='Contact Us', ignore_case=True), state='*')
@dp.message_handler(Text(equals='Обратная связь', ignore_case=True), state='*')
async def contact(message: types.Message):
    if message.text.lower() == 'contact us':
        user_locale = 'en'
    else:
        user_locale = 'ru'
    await message.answer(Localize.Contact[user_locale])


@dp.message_handler(state=Form.git_url)
async def process_git(message: types.Message, state: FSMContext):
    username = message.text.lower()
    try:
        user_id = message.chat.id
    except:
        await message.answer("Error with user_id")
        return

    user_locale = await Database.get_user_locale(user_id)
    if not user_locale:
        async with state.proxy() as data:
            user_locale = data['locale']

    git_pattern = re.compile("^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$")
    if git_pattern.match(username) is None or not await validate_username(username):
        await message.answer(Localize.IncorrectName[user_locale])
        return

    # TODO: rewrite
    if await Database.get_telegram_from_git(username):
        if await Database.get_telegram_from_git(username) != user_id:
            await message.answer(Localize.UsedName[user_locale])
            return

    await state.finish()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    if user_locale == 'en':
        markup.add("Today's list", "Rules")
        markup.add("My GitHub", "Change GitHub Profile", "Contact Us")
    else:
        markup.add("Список на сегодня", "Правила")
        markup.add("Мой GitHub", "Изменить профиль GitHub",
                   "Обратная связь")

    # only update username if user already exists
    if await Database.get_git_from_telegram(user_id):
        await Database.update_username(user_id, username)
        await message.answer(Localize.YourGithub[user_locale].format(username=username), reply_markup=markup)
        return

    await Database.add_to_db(user_id, username, data['locale'])
    await message.answer(Localize.Registered[user_locale].format(username=username))
    if user_locale == 'en':
        await message.answer(
            md.text(
                md.text(
                    'Now you are participating! Use ',
                    md.bold("Rules"),
                    ' button to find out more.', sep=''
                )
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            md.text(
                md.text(
                    'Теперь ты полноценный участник! Воспользуйся кнопкой ',
                    md.bold("Правила"),
                    ', чтобы узнать подробнее.', sep=''
                )
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN
        )
    now = datetime.datetime.now()
    # don't send if time is between 11:45 and 12
    if now.hour > 11 and now.hour < 12 and now.minutes > 50:
        await message.answer(Localize.WaitLittle[user_locale].format(minutes=60-now.minutes))
    else:
        # make a list for him otherwise
        await pipeline_for_user(user_id)


@dp.message_handler(Text(equals='English 🇬🇧', ignore_case=True), state=Form.set_language)
@dp.message_handler(Text(equals='Русский 🇷🇺', ignore_case=True), state=Form.set_language)
async def process_locale(message: types.Message, state: FSMContext):
    try:
        user_id = message.chat.id
    except:
        await message.answer("Error with user_id")
        return
    if message.text == 'English 🇬🇧':
        user_locale = 'en'
    else:
        user_locale = 'ru'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    # updating locale
    if await Database.get_git_from_telegram(user_id):
        await Database.update_locale(user_id, user_locale)
        if user_locale == 'en':
            markup.add("Today's list", "Rules")
            markup.add("My GitHub", "Change GitHub Profile", "Contact Us")
        else:
            markup.add("Список на сегодня", "Правила")
            markup.add("Мой GitHub", "Изменить профиль GitHub",
                       "Обратная связь")
        await message.answer(Localize.UsingLanguage[user_locale], reply_markup=markup)
        await state.finish()
        return
    # new user
    async with state.proxy() as data:
        data['locale'] = user_locale
    if user_locale == 'en':
        markup.add("Contact Us")
    else:
        markup.add("Обратная связь")
    await message.answer(Localize.Greetings[user_locale], reply_markup=markup)
    utc_hour = datetime.datetime.now(pytz.timezone('UTC')).hour
    london = 12 + datetime.datetime.now(pytz.timezone('Europe/London')).hour - utc_hour
    moscow = 12 + datetime.datetime.now(pytz.timezone('Europe/Moscow')).hour - utc_hour
    la = 12 + datetime.datetime.now(pytz.timezone('America/Los_Angeles')).hour - utc_hour
    await message.answer(Localize.Rules[user_locale].format(london=london, moscow=moscow, la=la), reply_markup=markup)
    await message.answer(Localize.ChangingGit[user_locale], reply_markup=markup)
    await Form.next()


@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message):
    await Form.set_language.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("English 🇬🇧", "Русский 🇷🇺")
    await message.answer("Hi! Choose your language.", reply_markup=markup)


if __name__ == '__main__':
    # Run pipeline once a day
    scheduler = AsyncIOScheduler(timezone='UTC')
    scheduler.add_job(pipeline, 'cron', hour=12, minute=0, second=0)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
