import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from datetime import datetime as dt
from random import randint

TOKEN = ""
STARTING_MESSAGE = "Привет! Данный бот позволяет: \
                    \n 0. Вернуться в начало (покажет стартовое сообщение) \
                    \n 1. Запланировать тренировку \
                    \n 2. Удалить запланированную тренировку\
                    \n 3. Посмотреть список запланированных тренировок (N последних) \
                    \n Введите соответствующую цифру для выполнения одного из вышеперечисленных действий."
FIRST_COMMAND = 1
SECOND_COMMAND = 2
THIRD_COMMAND = 3
CHAT_IDS = {}

COMMAND_LIST = [0, FIRST_COMMAND, SECOND_COMMAND, THIRD_COMMAND]

MAX_ID = 31000

NOT_IN_LIST_MSG = "Такой команды не существует."
GIVE_STRING_MSG = "Введите данные о тренировке в следующей последовательности через знак \";\" без кавычек: время;координаты;расстояние;темп;комментарий;\
                    \n Пример строки для ввода:\
                    \n 16:30 23-05-24;60.02134,60.12345;12.5;4:30;развивающий кросс; \
                    \n Время и дата указывается в 24-часовом формате ЧЧ:ММ ДД-ММ-ГГ,\
                    \n координаты указываются двумя числами с плавающей точкой через запятую, \
                    \n расстояние указывается в километрах в формате числа с плавающей точкой, \
                    \n темп бега указывается в формате М:СС (минуты, секунды),\
                    \n комментарий - обычный текст."
GIVE_ID_MSG = "Введите ID тренировки, которую нужно удалить."
BAD_ID_MSG = "Нет такого ID"
BAD_CONNECT = "Проблемы взаимодействия с базой данных или неправильный ID"
GIVE_NUM_MSG = "Введите натуральное число N. Бот выведет последние N записей о запланированных тренировках."
SUCCESS_MSG = "Тренировка успешно записана. Ее ID: "
BAD_ARG_MSG = "Неправильный ввод"
SUCCESS_DEL_MSG = "Тренировка успешно отменена"

class MyError(Exception):
    def __init__(self, msg=""):
        self.message = msg

class DBBad(MyError):
    def __init__(self):
        super().__init__(BAD_CONNECT)

class BadArgs(MyError):
    def __init__(self):
        super().__init__(BAD_ARG_MSG)

class BadDate(MyError):
    def __init__(self):
        super().__init__("Неправильно введена дата и время")

class BadCoords(MyError):
    def __init__(self):
        super().__init__("Неправильно заданы координаты")

class BadDist(MyError):
    def __init__(self):
        super().__init__("Неправильно задана дистанция")

class BadVeloc(MyError):
    def __init__(self):
        super().__init__("Неправильно задан темп")

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=TOKEN)
# Диспетчер
dp = Dispatcher()



def handle_command(cmnd_id: int) -> str:
    """
        Функция, обрабатывающая полученную от пользователя валидный номер команды
        Выдает ответ, который отдаст обработчик
    """
    match cmnd_id:
        case 1:
            # Просим дать строку для записи тренировки
            return GIVE_STRING_MSG
        
        case 2:
            # Просим дать ID тренировки для удаления
            return GIVE_ID_MSG
        
        case 3:
            # Просим дать число N
            return GIVE_NUM_MSG
        
        case 0:
            return STARTING_MESSAGE
        

def train_str_parser(train_input: str) -> int:
    """
        Обработка строки о тренировке для записи
        train_input - строка в формате время;коорд;расст;темп;комментарий
        возвращает ID тренировки
    """
    train_list = train_input.split(";")
    # проверяем по длине
    if len(train_list) < 6:
        raise BadArgs
    # берем дату и время
    try:
        date_and_time = dt.strptime(train_list[0], "%H:%M %d-%m-%y")
    except Exception:
        raise BadDate
    # берем координаты
    try:
        inp_coords = train_list[1].split(",")
        if len(inp_coords) != 2:
            raise BadCoords
        first_coord = float(inp_coords[0])
        sec_coord = float(inp_coords[1])
    except Exception:
        raise BadCoords
    # берем расстояние
    try:
        dist = float(train_list[2])
    except Exception:
        raise BadDist
    # берем темп
    try:
        veloc_input = train_list[3].split(':')
        if len(veloc_input) != 2:
            raise BadVeloc
        min_per_km = int(veloc_input[0])
        sec_per_km = int(veloc_input[1])
    except:
        raise BadVeloc
    # считываем с БД все айдишники
    ID_LIST = get_id_from_bd()
    
    # генерируем ID
    train_id = randint(1, MAX_ID)
    while (train_id in ID_LIST):
        train_id = randint(1, MAX_ID)
    # запись в бд
    input_to_write = [str(train_id),
                      str(date_and_time),
                      str(first_coord)+";"+str(sec_coord),
                      str(dist),
                      str(min_per_km)+":"+str(sec_per_km),
                      train_list[-2]]
    write_to_db(input_to_write)
    return train_id

def write_to_db(input: list) -> None:
    """
        Функция записывает тренировку в БД
    """ 
    try:
        conn = sqlite3.connect('lastlase_db.db')
        conn.execute(f"INSERT INTO train_data (id, datetime, coords, dist, veloc, comment) \
                      VALUES ({input[0]}, '{input[1]}', '{input[2]}', '{input[3]}', '{input[4]}', '{input[5]}')")
        conn.commit()
        conn.close()
    except Exception:
        raise DBBad

def get_id_from_bd() -> list:
    """
        Берет все существующие айдишники в БД
    """
    ID_LIST = []
    readed_db = read_from_db()
    for trains in readed_db:
        ID_LIST.append(int(trains[0]))
    return ID_LIST
    
def read_from_db(number: int = MAX_ID) -> list:
    """
        Функция выдает number последних тренировок из БД
    """
    try:
        conn = sqlite3.connect('lastlase_db.db')
        readed_list = conn.execute(f"SELECT * \
                    FROM (SELECT * \
                    FROM train_data \
                    ORDER BY datetime DESC LIMIT {str(number)}) q \
                    ORDER BY q.datetime ASC;").fetchall()
        
        conn.close()
        return readed_list
    except Exception:
        raise DBBad
    
def delete_from_db(id: int) -> None:
    """
        Функция, удаляющая тренировку id
    """
    try:
        conn = sqlite3.connect('lastlase_db.db')
        conn.execute(f"DELETE FROM train_data WHERE id = {str(id)};")
        conn.commit()
        conn.close()
    except Exception:
        raise DBBad

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(STARTING_MESSAGE)

@dp.message(F.text)
async def parse_text(message: types.Message):
    """
        Функция, обрабатывающая введенный пользователем текст в зависимости от состояния STATUS
        Если STATUS == False, то смотрим, что за команду ввел пользователь
        Если STATUS == True, то смотрим, что за команда сейчас вводится и обрабатываем
        
    """
    
    global CHAT_IDS

    if message.chat.id in CHAT_IDS.keys():
        # значит уже общаемся
        if CHAT_IDS[message.chat.id] == 0:
            STATUS = 0
        else:
            STATUS = 1
    else:
        CHAT_IDS[message.chat.id] = 0
        STATUS = 0

    if message.text == "0":
        CHAT_IDS[message.chat.id] = 0
        STATUS = 0
    
    if STATUS:
        # код обработки строки
        match CHAT_IDS[message.chat.id]:
            case 1:
                # обработка строки о тренировке
                try:
                    ID_of_train = train_str_parser(message.text)
                    del CHAT_IDS[message.chat.id]
                    await message.answer(SUCCESS_MSG + str(ID_of_train))
                except MyError as err:
                    await message.answer(err.message)
                except Exception as err_def:
                    await message.answer(err_def)

            case 2:
                # обработка id тренировки
                id = 0
                try:
                    id = int(message.text)
                except Exception:
                    await message.answer(BAD_ARG_MSG)
                # удаление из бд
                try:
                    # считаем есть ли такой id вообще 
                    ID_LIST = get_id_from_bd()
                    if id in ID_LIST:
                        delete_from_db(id)
                        del CHAT_IDS[message.chat.id]
                        await message.answer(SUCCESS_DEL_MSG)
                    else:
                        await message.answer(BAD_ID_MSG)
                except MyError as err:
                    await message.answer(err.message)

            case 3:
                # обработка числа N, выдача сообщения о тренировках
                try:
                    N = int(message.text)
                except Exception:
                    await message.answer(BAD_ARG_MSG)
                # считываем с бд и выводим N записей
                if N > 1:
                    try:
                        trains = read_from_db(N)
                        trains = trains[::-1]
                        return_stroke = ""
                        for train in trains:
                            return_stroke += f"id: {train[0]}, дата и время: {train[1]}, координаты: {train[2]}, расстояние (км): {train[3]}, темп: {train[4]}, комментарий: {train[5]} \n\n"
                        del CHAT_IDS[message.chat.id]
                        if return_stroke != "":
                            await message.answer(return_stroke)
                        else:
                            await message.answer("История пуста.")
                    except MyError as err:
                        await message.answer(err.message)
                else:
                    await message.answer(BAD_ARG_MSG)
              
                
    else:
        # пробуем в int преобразовать
        try:
            parsed_command = int(message.text)
        except ValueError:
            # удаляем
            del CHAT_IDS[message.chat.id]
            await message.answer(NOT_IN_LIST_MSG)
        # если получилось, проверяем есть ли такая комманда
        if parsed_command in COMMAND_LIST:
            # обрабатываем команду
            answer = handle_command(parsed_command)
            CHAT_IDS[message.chat.id] = parsed_command
            await message.answer(answer)
        else:
            del CHAT_IDS[message.chat.id]
            await message.answer(NOT_IN_LIST_MSG)

    
# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
