from this import s
from models import TransformerNet
from utils import *
import torch
from torch.autograd import Variable
import argparse
import os
from torchvision.utils import save_image
from PIL import Image

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_path", type = str, required = True, help = "Path to image")
    parser.add_argument("--checkpoint_model", type = str, required = True, help = "Path to checkpoint model")
    args = parser.parse_args()
    print(args)

    os.makedirs("images/outputs", exist_ok = True)

    device = torch.device("cpu")

    transform = style_transform()

    # Определение модели, загрузка весов модели 
    transformer = TransformerNet().to(device)
    transformer.load_state_dict(torch.load(args.checkpoint_model, map_location = 'cpu'))
    transformer.eval()

    # Загрузка контентного изображения
    image_tensor = Variable(transform(Image.open(args.image_path))).to(device)
    image_tensor = image_tensor.unsqueeze(0)

    # Стилизация изображения
    with torch.no_grad():
        stylized_image = denormalize(transformer(image_tensor)).cpu()

    # Сохранение сгенерированного изображения
    fn = args.image_path.split("/")[-1]
    save_image(stylized_image, f"stylized-{fn}")
