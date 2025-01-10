import os
import asyncio
import json
import boto3
from botocore.client import Config
from aio_pika import Message, connect
from aio_pika.abc import AbstractIncomingMessage
import torch
from torch.autograd import Variable
from torchvision.utils import save_image
from PIL import Image
from models import TransformerNet
from utils import *
from detector import run_detection_model
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

def style_image(content_path, name, today, timestamp):
    device = torch.device("cpu")

    transform = style_transform()

    # Определение модели, загрузка весов модели
    transformer = TransformerNet().to(device)
    transformer.load_state_dict(torch.load(content_path))
    transformer.eval()

    content_path = f'/app/photo/{today}/content_image_{name}_{timestamp}.jpg'
    try:
        s3.download_file(bucket_name, content_path, content_path)
        logger.info(f"The {content_path} file was successfully downloaded from S3 and saved as {content_path}.")
    except Exception as e:
        logger.error(f"Error when downloading the {content_path} file from S3: {e}")
    
    image_tensor = Variable(transform(Image.open(content_path))).to(device)
    image_tensor = image_tensor.unsqueeze(0)
    os.remove(content_path)
    
    # Стилизация изображения
    with torch.no_grad():
        stylized_image = denormalize(transformer(image_tensor)).cpu()
    
    stylized_image_path = f'/app/photo/{today}/stylized_image_{name}_{timestamp}.jpg'
    save_image(stylized_image, stylized_image_path)
    try:
        s3.upload_file(stylized_image_path, bucket_name, stylized_image_path)
        logger.info(f"The styling is complete. The file is uploaded to S3: {stylized_image_path}")
    except Exception as e:
        logger.info(f"S3 upload error: {e}")
    os.remove(stylized_image_path)


async def process_detection(inputMessage):
    today = inputMessage.get('today')  
    timestamp = inputMessage.get('timestamp')  
    user_id = inputMessage.get('user_id') 
    
    image_path = f'/app/photo/{today}/content_image_{user_id}_{timestamp}.jpg'
    
    try:
        s3.download_file(bucket_name, image_path, image_path)
        logger.info(f"The {image_path} file was successfully downloaded from S3 and saved as {image_path}.")
    except Exception as e:
        logger.error(f"Error when downloading the {image_path} file from S3: {e}")
    
    # Проверяем контент изображения
    detection_result = run_detection_model(image_path)
    os.remove(image_path)
    
    if detection_result == "Porn":
        outputMessage = {'user_id': inputMessage['user_id'], 'text': 'Изображение содержит неприемлемый контент.'}
        logger.info(f"User {user_id} notified: {outputMessage['text']}")
        return None
    
    return inputMessage

async def process_stylization(inputMessage):
    style_image(inputMessage['text'], inputMessage['user_id'], inputMessage['today'], inputMessage['timestamp'])
    outputMessage = inputMessage
    logger.info(f"User {inputMessage['user_id']} styled the image.")
    return outputMessage

async def main() -> None:
    try:
        connection = await connect(os.environ["AMQP_URL"])
    except Exception:
        logger.exception("connection not open")

    channel = await connection.channel()

    exchange = channel.default_exchange

    queue_detection = await channel.declare_queue("detection_queue", durable=True)
    queue_stylization = await channel.declare_queue("stylization_queue", durable=True)

    logger.info(" [x] Awaiting messages")

    async def consume_detection():
        async with queue_detection.iterator() as detection_iterator:
            async for message in detection_iterator:
                try:
                    async with message.process(requeue=True):
                        assert message.reply_to is not None
                        inputJsonDet = message.body.decode("UTF-8")
                        inputMessageDet = json.loads(inputJsonDet)
                        
                        resultMessageDet = await process_detection(inputMessageDet)

                        outputJsonDet = json.dumps(inputMessageDet)
                        response = outputJsonDet.encode("UTF-8")
                        
                        if resultMessageDet:
                            # Если изображение прошло проверку, отправляем на стилизацию
                            await exchange.publish(
                                Message(
                                    body=response,
                                    reply_to=message.reply_to,
                                    correlation_id=message.correlation_id
                                ),
                                routing_key="stylization_queue",
                            )
                        else:
                            outputMessageDet = {'user_id': inputMessageDet['user_id'], 'text': 'Изображение содержит неприемлемый контент.'}
                            outputJsonDet = json.dumps(outputMessageDet)
                            responseDet = outputJsonDet.encode("UTF-8")
                            await exchange.publish(
                                Message(
                                    body=responseDet,
                                    correlation_id=message.correlation_id,
                                ),
                                routing_key=message.reply_to,
                            )
                except Exception:
                    logger.exception("Processing error for message %r", message)
        
    async def consume_stylization():
        async with queue_stylization.iterator() as stylization_iterator:
            async for message in stylization_iterator:
                try:
                    async with message.process(requeue=True):
                        assert message.reply_to is not None
                        inputJson = message.body.decode("UTF-8")
                        inputMessage = json.loads(inputJson)
                        
                        outputMessage = await process_stylization(inputMessage)
                        
                        outputJson = json.dumps(outputMessage)
                        response = outputJson.encode("UTF-8")
                        await exchange.publish(
                            Message(
                                body=response,
                                correlation_id=message.correlation_id,
                            ),
                            routing_key=message.reply_to,
                        )

                except Exception:
                    logger.exception("Processing error for message %r", message)
    
    await asyncio.gather(consume_detection(), consume_stylization())

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(" [x] Server is down")
