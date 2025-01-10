import os
import json
import numpy as np
from PIL import Image
from skimage import transform
from keras.models import load_model
from tensorflow.keras.optimizers import SGD
from logging_config import get_logger

logger = get_logger()

model = None

def load_model_once():
    global model
    if model is None:
        model_path = os.getenv("MODEL_PATH", "/app/checkpoints/detector.h5")
        model = load_model(model_path, compile=False)
        optimizer = SGD(learning_rate=3.162277789670043e-05)
        model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])
        logger.info(f"Model loaded from {model_path}")
    return model

def load(filename):
    np_image = Image.open(filename)
    np_image = np.array(np_image).astype('float32') / 255
    np_image = transform.resize(np_image, (224, 224, 3))
    np_image = np.expand_dims(np_image, axis=0)
    return np_image

def run_detection_model(image_path):
    model = load_model_once()
    image = load(image_path)

    ans = model.predict(image)
    mapping = {0: "Neutral", 1: "Porn", 2: "Sexy"}
    new_ans = np.argmax(ans[0])
    prediction = mapping[new_ans]

    logger.info(f"Prediction for image {image_path}: {prediction}")

    return prediction
