import json
import os
import asyncio
import shutil
import boto3
from botocore.client import Config
from datetime import datetime, timedelta
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram import types
from client import MyClient
from logging_config import get_logger
from dotenv import load_dotenv

load_dotenv() 
logger = get_logger()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'),
    region_name='ru-central-1',
    endpoint_url='https://s3.cloud.ru',
    config=Config(signature_version='s3v4')
)

bucket_name = os.getenv('BUCKET_NAME')

class Generation(StatesGroup):
    wait_for_style = State()
    wait_for_answer = State()
    wait_for_policy_acceptance = State() 

class HandlerMessages:
    def __init__(
            self,
            dispatcher: Dispatcher,
            sendler: MyClient
    ):
        self._dispatcher = dispatcher
        self._sendler = sendler
        self.base_photo_dir = 'app/photo'
        os.makedirs(self.base_photo_dir, exist_ok=True)
        self.current_timestamp = None
        self.today = None
        self.user_id = None


    def start_message_handler(self) -> None:
        """ Начало работы с ботом """
        @self._dispatcher.message_handler(commands="start")
        async def starting_bot(message: types.Message, state: FSMContext):
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            buttons = ["Принять", "Отказаться"]
            keyboard.add(*buttons)
            
            policy_text = (
                "Привет! Я умею стилизировать изображения, хочешь попробовать?\n\n"
                "Для этого необходимо принять политику конфиденциальности:\n\n"
                "1. Изображения с незаконным контентом будут отвергнуты.\n"
                "2. Пожалуйста, избегайте загрузки изображений с лицами других людей без их согласия.\n\n"
                "Примите ли вы политику конфиденциальности?"
            )
            
            await Generation.wait_for_policy_acceptance.set()  # Устанавливаем состояние
            await message.answer(policy_text, reply_markup=keyboard)


    def handle_policy_acceptance(self) -> None:
        """ Отправка ответа пользователю на сообщении о политике конфиденциальности """
        @self._dispatcher.message_handler(Text(equals="Принять"), state=Generation.wait_for_policy_acceptance)
        async def accept_policy(message: types.Message, state: FSMContext):
            await state.finish()
            await message.answer("Спасибо за принятие политики! Теперь отправьте изображение для стилизации.")
        
        @self._dispatcher.message_handler(Text(equals="Отказаться"), state=Generation.wait_for_policy_acceptance)
        async def decline_policy(message: types.Message, state: FSMContext):
            await state.finish()
            await message.answer("Вы отказались от принятия политики. К сожалению, я не могу с вами работать.")


    def input_photo(self) -> None: 
        " Получение от пользователя фотографии, перевод пользователя в состояние ожидания выбора стиля "      
        @self._dispatcher.message_handler(content_types = ['photo'])
        async def get_user_photo(message):
            self.today = datetime.now().strftime('%Y-%m-%d')
            self.user_dir = f'/app/photo/{self.today}'
            os.makedirs(self.user_dir, exist_ok=True)

            self.current_timestamp = datetime.now().strftime("%H%M%S")
            filename = f'{self.user_dir}/content_image_{message.from_user.id}_{self.current_timestamp}.jpg'
            await message.photo[-1].download(filename)
            
            try:
                s3.upload_file(filename, bucket_name, filename)
                logger.info(f"Фото получено. Файл загружен в S3: {filename}")
            except Exception as e:
                logger.info(f"Ошибка загрузки в S3: {e}")

            os.remove(filename)

            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
            button = ["В.В.Кандинский «Композиция VII»", "К.Хокусай «Большая волна в Канагаве»", "И.К.Айвазовский «Океан»", "Акварельные краски", "Э.Р.Кальзадо «Начало»"]
            markup.add(*button)
            await Generation.wait_for_style.set()
            await message.answer("Отлично! У меня есть несколько стилей, которые я могу предложить тебе. Выбери заинтересовавший стиль.",  reply_markup = markup)


    def consent_to_generate(self) -> None:
        """ Согласие пользователя на стилизацию """
        @self._dispatcher.message_handler(Text(equals = "Да, конечно!"))
        async def await_input_from_user(message: types.Message):
            await message.answer("Замечательно! Отправь мне изображение, которое хочешь стилизовать.")


    async def get_answer_and_reply(self, id: int, message: str, state: FSMContext) -> None:
        """ Получение ответа от сервера, отправка результата пользователю, сброс состояния ожидания генерации """
        # Получаем ответ от сервера
        response = await self._sendler.call(message, id, self.today, self.current_timestamp)
        answer = json.loads(response.decode("UTF-8"))
        stylized_image_path = f'{self.user_dir}/stylized_image_{id}_{self.current_timestamp}.jpg'
        
        # Проверяем, содержит ли ответ сообщение о негативном контенте
        if 'text' in answer and answer['text'] == 'Изображение содержит неприемлемый контент.':
            # Если изображение содержит негативный контент, отправляем уведомление пользователю
            await self._dispatcher.bot.send_message(answer['user_id'], 'Ваше изображение содержит неприемлемый контент. Пожалуйста, отправьте другое изображение.')
        else:
            try:
                s3.download_file(bucket_name, stylized_image_path, stylized_image_path)
                logger.info(f"Файл {stylized_image_path} успешно скачан из S3 и сохранен как {stylized_image_path}.")
            except Exception as e:
                logger.error(f"Ошибка при скачивании файла {stylized_image_path} из S3: {e}")

            await self._dispatcher.bot.send_photo(answer['user_id'], photo=open(stylized_image_path, 'rb'))
            await self._dispatcher.bot.send_message(answer['user_id'], 'Мне нравится результат! Отправь новую фотографию для стилизации.')
            os.remove(stylized_image_path)

        await state.finish()


    def send_and_reply_message(self) -> None:
        """ Получение ответа от пользователя, отправка запроса к серверу, сброс состояния выбора стиля, перевод в состояния ожидания генерации """
        @self._dispatcher.message_handler(state = Generation.wait_for_style)
        async def answer_on_input(message: types.Message, state: FSMContext):
            await message.answer("Нужно чуточку подождать!")
            await state.finish()
            await Generation.wait_for_answer.set()
            # Запрос к серверу в зависимости от выбранного пользователем стиля 
            if(message.text == "В.В.Кандинский «Композиция VII»"):
                await self.get_answer_and_reply(message.from_user.id, '/app/checkpoints/kandinskyVII_10000.pth', state)
            elif(message.text == "К.Хокусай «Большая волна в Канагаве»"):
                await self.get_answer_and_reply(message.from_user.id, '/app/checkpoints/wave_10000.pth', state)
            elif(message.text == "И.К.Айвазовский «Океан»"):
                await self.get_answer_and_reply(message.from_user.id, '/app/checkpoints/aivazovsky-ocean_5000.pth', state)
            elif(message.text == "Акварельные краски"):
                await self.get_answer_and_reply(message.from_user.id, '/app/checkpoints/akvarel_9000.pth', state)
            elif(message.text == "Э.Р.Кальзадо «Начало»"):
                await self.get_answer_and_reply(message.from_user.id, '/app/checkpoints/kalzado_10000.pth', state)
    
    def cleanup_old_images(self):
        now = datetime.now()
        for folder_name in os.listdir(self.base_photo_dir):
            try:
                folder_date = datetime.strptime(folder_name, '%Y-%m-%d')
                if now - folder_date > timedelta(days=1):
                    folder_path = os.path.join(self.base_photo_dir, folder_name)
                    shutil.rmtree(folder_path)
            except ValueError:
                continue
            except OSError as e:
                logger.error(f"Error removing folder {folder_name}: {e}")
    
    def cleanup_on_shutdown(self):
        try:
            if os.path.exists(self.base_photo_dir):
                shutil.rmtree(self.base_photo_dir)
        except OSError as e:
            logger.error(f"Error during cleanup on shutdown: {e}")
    
    def refusal_to_generate(self) -> None:
        """ Отказ пользователя от стилизации """
        @self._dispatcher.message_handler(Text(equals = "Нет, не хочу."))
        async def not_bot(message: types.Message):
            await message.answer("Жаль! Отправь мне «/start», если всё-таки захочешь приступить к стилизации изображения.")   
   
    def block_message_for_generation(self) -> None:
        """ Блокирование пользователю новых запросов, пока не будет получен ответ от сервера """
        @self._dispatcher.message_handler(content_types = ['text'], state = Generation.wait_for_answer)
        async def warning_gen(message: types.Message, state: FSMContext):
            await state.finish()
            await message.answer("Сначала необходимо дождаться окончания генерации!")
    
    def block_photo_for_generation(self) -> None:
        """ Блокирование отправки пользователем новой фотографии, пока не будет получен ответ от сервера """
        @self._dispatcher.message_handler(content_types = ['photo'], state = Generation.wait_for_answer)
        async def warning_gen_photo(message: types.Message, state: FSMContext):
            await state.finish()
            await message.answer("Сначала необходимо дождаться окончания генерации!")
    
    def handle_non_photo_files(self) -> None:
        """ Обработка сообщений, содержащих файлы"""
        @self._dispatcher.message_handler(content_types=['document', 'video', 'audio', 'voice', 'sticker', 'location', 'contact'])
        async def handle_non_photo(message: types.Message):
            await message.reply("Некорректный формат изображения, отправьте, пожалуйста, другое изображение.")
    
    def register_all_handlers(self) -> None:
        self.start_message_handler()
        self.handle_policy_acceptance()
        self.input_photo()
        self.consent_to_generate()
        self.send_and_reply_message()
        self.refusal_to_generate()
        self.block_message_for_generation()
        self.block_photo_for_generation()
        self.handle_non_photo_files() 
