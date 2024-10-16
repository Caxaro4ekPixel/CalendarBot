from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import CallbackQuery, ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram_timepicker.panel import full_timep_callback
from aiogram_timepicker.panel import FullTimePicker
from decouple import config
from sql import first_start, User, Event
import asyncio
from datetime import datetime
from forms import Form

bot = Bot(token=config('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=MemoryStorage())
delay = 300
first_start()

start_kb = ReplyKeyboardMarkup(resize_keyboard=True, )
start_kb.row('Navigation Calendar')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        'Бот для контроля твоего расписания!\n\n'
        '/reg - регистрация\n'
        '/new - создать новое событие в расписание\n'
        '/list - список событий\n\n'
        'Для просмотра списка команд введите /help'
    )


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer(
        'Бот для контроля твоего расписания!\n\n'
        '/reg - регистрация\n'
        '/new - создать новое событие в расписание\n'
        '/list - список событий\n'
        '/cancel - отмена создания события\n'
    )


@dp.message_handler(commands=['reg'])
async def reg(message: types.Message):
    res, status = User(message.chat.username, message.chat.id).add_user()
    await message.answer(status)


@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Отменено')


@dp.message_handler(commands=['new'])
async def new_event(message: types.Message):
    await Form.event_body.set()
    await message.answer("Введите ОПИСАНИЕ события: ")


@dp.message_handler(state=Form.event_body)
async def event_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['event_body'] = message.text
    await Form.next()
    await message.reply("Введите название события: ")


@dp.message_handler(state=Form.event_name)
async def event_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['event_name'] = message.text
    await Form.next()
    await message.answer("Выберите дату: ", reply_markup=await SimpleCalendar().start_calendar())


@dp.message_handler(commands=['list'])
async def list_events(message: types.Message):
    status, data = Event.get_all_events(username=message.chat.username)
    markup = types.InlineKeyboardMarkup()

    split_size = 3
    splitted_list = [data[i:i + split_size] for i in range(0, len(data), split_size)]

    button_list = []

    for i in splitted_list:
        temp = []
        for j in i:
            temp.append(types.InlineKeyboardButton(text=j[3], callback_data=f"event_{j[0]}"))
        button_list.append(temp)

    for i in button_list:
        markup.add(*i)

    if status:
        mess = "Ваш список событий:"
        await message.answer(mess, reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('event_'))
async def process_callback(callback_query: CallbackQuery):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text='❌Удалить❌', callback_data=f"delete_{callback_query.data.split('_')[1]}"))
    event_id = callback_query.data.split('_')[1]
    status, data = Event.get_events_by_id(event_id)
    await callback_query.message.answer(
        f"""ID: {data[0]}\nДата: {data[1]}\nНазвание: {data[3]}\nОписание: {data[4]}\n\n""", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
async def process_simple_calendar(callback_query: CallbackQuery):
    status, data = Event.delete_event(callback_query.data.split('_')[1])
    if status:
        await callback_query.message.edit_text(callback_query.message.text)
    await callback_query.message.answer(data)


@dp.callback_query_handler(simple_cal_callback.filter(), state='*')
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        async with state.proxy() as data:
            data['event_date'] = date
        await Form.next()
        await callback_query.message.answer("Введите время: ", reply_markup=await FullTimePicker().start_picker())


@dp.callback_query_handler(full_timep_callback.filter(), state='*')
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    r = await FullTimePicker().process_selection(callback_query, callback_data)
    if r.selected:
        await callback_query.message.edit_text("Введите время:")
        async with state.proxy() as data:
            data['event_date'] = data['event_date'].replace(hour=r.time.hour, minute=r.time.minute,
                                                            second=r.time.second)
            res, status = Event.add_event(datetime_event=data['event_date'], event_handler=data['event_name'],
                                          event_data=data['event_body'], username=callback_query['from']['username'])
            if status:
                await callback_query.message.answer(
                    f"Событие: {data['event_name']}\nОписание: {data['event_body']}\n\n Добавлено!")
            else:
                await callback_query.message.answer(f"Ошибка: {res}")
        await state.finish()


def repeat(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(delay, repeat, coro, loop)


async def while_true_task():
    status_2h, alerts_2h = Event.get_all_events_by_date(datetime.now(), 2)
    status_1d, alerts_1d = Event.get_all_events_by_date(datetime.now(), 24)

    if status_2h:
        for i in alerts_2h:
            await bot.send_message(i[3], f"❕❕❕Напоминаем о событии❕❕❕\n\n"
                                         f"⌛️Через 2 часа\n\n"
                                         f"📌Событие: {i[1]}\n\n"
                                         f"🗓Описание: {i[2]}")
    if status_1d:
        for i in alerts_1d:
            await bot.send_message(i[3], f"❕❕❕Напоминаем о событии❕❕❕\n\n"
                                         f"⌛️Через 1 день\n\n"
                                         f"📌Событие: {i[1]}\n\n"
                                         f"🗓Описание: {i[2]}")
    else:
        await asyncio.sleep(delay)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.call_later(delay, repeat, while_true_task, loop)
    executor.start_polling(dp)
