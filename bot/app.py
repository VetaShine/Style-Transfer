import os 
import asyncio
import logging
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from client import MyClient
from handler import HandlerMessages
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aioredis import Redis
import redis
from dotenv import load_dotenv

load_dotenv() 
logging.basicConfig(level = logging.INFO)


async def prepare(sendler: MyClient) -> Dispatcher:
    """ Создание и конфигурация бота, подключение к RabbitMQ """
    storage = RedisStorage2(
        host=os.environ['REDIS_HOST'], db=5, port=os.environ['REDIS_PORT'], password=os.environ['REDIS_PASSWORD']
    )
    bot = Bot(os.getenv('BOT_TOKEN'))
    dp = Dispatcher(bot, storage=storage)
    handler = HandlerMessages(dp, sendler)
    handler.register_all_handlers()
    return dp


async def main() -> None:
    # Установка соединения с RabbitMQ
    sendler = await MyClient().connect()
    # Создание диспетчера
    dp = await prepare(sendler)
    # Запуск бота
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())