import os
import uuid
import asyncio
import json
from typing import MutableMapping
from aio_pika import Message, connect
from aio_pika.abc import(
    AbstractChannel, AbstractConnection, AbstractIncomingMessage, AbstractQueue,
)
from logging_config import get_logger

# Получаем логгер
logger = get_logger()


class MyClient:
    connection: AbstractConnection
    channel: AbstractChannel
    callback_queue: AbstractQueue
    loop: asyncio.AbstractEventLoop

    def __init__(self) -> None:
        self.futures: MutableMapping[str, asyncio.Future] = {}
        self.loop = asyncio.get_running_loop()

    async def connect(self) -> "MyClient":
        """ Установка соединения с RabbitMQ, создание очереди для получения запросов, старт прослушивания очереди """
        self.connection = None
        while(self.connection == None):
            try:
                self.connection = await connect(
                    os.environ["AMQP_URL"], loop = self.loop,
                )
            except:
                print('waiting for connection')
                await asyncio.sleep(50)

        self.channel = await self.connection.channel()
        self.callback_queue = await self.channel.declare_queue(exclusive = True, durable = True)
        await self.callback_queue.consume(self.on_response)
        return self

    async def on_response(self, message: AbstractIncomingMessage) -> None:
        """ Действие на возврат ответа message от сервера """
        if message.correlation_id is None:
            logger.warning(f"Bad message {message!r}")
            return

        future: asyncio.Future = self.futures.pop(message.correlation_id)
        future.set_result(message.body)
        inputJson = message.body.decode("UTF-8")
        inputMessage = json.loads(inputJson)
        logger.info("Message from server: %r", inputMessage['text'])
        logger.info(" [x] Response complete")

    async def call(self, text: str, id: int, today: str, timestamp: str) -> int:
        """ Создание запроса к очереди, передача id пользователя и ссылки на веса модели выбранного пользователем стиля в формате json """
        correlation_id = str(uuid.uuid4())
        future = self.loop.create_future()
        params = {
            "user_id": id,
            "text": text,
            "today": today,
            "timestamp": timestamp
        }
        jsonParams = json.dumps(params)
        self.futures[correlation_id] = future
        
        try:
            await self.channel.default_exchange.publish(
                Message(
                    jsonParams.encode(),
                    content_type = "application/json",
                    correlation_id = correlation_id,
                    reply_to = self.callback_queue.name,
                ),
                routing_key = "detection_queue",
            )
        except:
            logger.exception(" [x] Message not sending")

        return await future
