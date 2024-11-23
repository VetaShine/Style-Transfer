import argparse
import os
import sys
import random
from PIL import Image
import numpy as np
import torch
import glob
from torch.optim import Adam
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.utils import save_image
from models import TransformerNet, VGG16
from utils import *

def save_sample(batches_done):
    """ Оценка модели и сохранение образцов изображений """
    transformer.eval()
    with torch.no_grad():
        output = transformer(image_samples.to(device))
    image_grid = denormalize(torch.cat((image_samples.cpu(), output.cpu()), 2))
    save_image(image_grid, f"images/outputs/{style_name}-training/{batches_done}.jpg", nrow = 4)
    transformer.train()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Parser for Fast-Neural-Style")
    parser.add_argument("--dataset_path", type = str, required = True, help = "path to training dataset")
    parser.add_argument("--style_image", type = str, default = "style-images/kalzado.jpg", help = "path to style image")
    parser.add_argument("--epochs", type = int, default = 1, help = "Number of training epochs")
    parser.add_argument("--batch_size", type = int, default = 4, help = "Batch size for training")
    parser.add_argument("--image_size", type = int, default = 256, help = "Size of training images")
    parser.add_argument("--style_size", type = int, help = "Size of style image")
    parser.add_argument("--lambda_content", type = float, default = 1e5, help = "Weight for content loss")
    parser.add_argument("--lambda_style", type = float, default = 1e10, help = "Weight for style loss")
    parser.add_argument("--lr", type = float, default = 1e-3, help = "Learning rate")
    parser.add_argument("--checkpoint_model", type = str, help = "Optional path to checkpoint model")
    parser.add_argument("--checkpoint_interval", type = int, default = 2000, help = "Batches between saving model")
    parser.add_argument("--sample_interval", type = int, default = 1000, help = "Batches between saving image samples")
    args = parser.parse_args()

    style_name = args.style_image.split("/")[-1].split(".")[0]
    os.makedirs(f"images/outputs/{style_name}-training", exist_ok = True)
    os.makedirs(f"checkpoints", exist_ok=True)

    device = torch.device("cpu")

    # Создание загрузчика данных для обучающих данных
    train_dataset = datasets.ImageFolder(args.dataset_path, train_transform(args.image_size))
    dataloader = DataLoader(train_dataset, batch_size=args.batch_size)

    # Определение сети
    transformer = TransformerNet().to(device)
    vgg = VGG16(requires_grad = False).to(device)

    # Загрузка весов модели, если они указаны
    if args.checkpoint_model:
        transformer.load_state_dict(torch.load(args.checkpoint_model))

    # Определение оптимизатора и потери
    optimizer = Adam(transformer.parameters(), args.lr)
    l2_loss = torch.nn.MSELoss().to(device)

    # Загрузка стилевого изображения
    style = style_transform(args.style_size)(Image.open(args.style_image))
    style = style.repeat(args.batch_size, 1, 1, 1).to(device)

    # Извлечение функции стиля
    features_style = vgg(style)
    gram_style = [gram_matrix(y) for y in features_style]

    # Выбор восьми изображений для визуальной оценки модели 
    image_samples = []
    for path in random.sample(glob.glob(f"{args.dataset_path}/*/*.png"), 8):
        image_samples += [style_transform(args.image_size)(Image.open(path))]
    image_samples = torch.stack(image_samples)
    
    k = 0

    for epoch in range(args.epochs):
        epoch_metrics = {"content": [], "style": [], "total": []}
        for batch_i, (images, _) in enumerate(dataloader):
            optimizer.zero_grad()

            images_original = images.to(device)
            images_transformed = transformer(images_original)

            # Извлечение функций
            features_original = vgg(images_original)
            features_transformed = vgg(images_transformed)

            # Вычисление потери контента как MSE между функциями
            content_loss = args.lambda_content * l2_loss(features_transformed.relu2_2, features_original.relu2_2)

            # Вычисление потери стиля как MSE между матрицами Грама
            style_loss = 0
            for ft_y, gm_s in zip(features_transformed, gram_style):
                gm_y = gram_matrix(ft_y)
                style_loss += l2_loss(gm_y, gm_s[: images.size(0), :, :])
            style_loss *= args.lambda_style

            total_loss = content_loss + style_loss
            total_loss.backward()
            optimizer.step()

            epoch_metrics["content"] += [content_loss.item()]
            epoch_metrics["style"] += [style_loss.item()]
            epoch_metrics["total"] += [total_loss.item()]

            sys.stdout.write(
                "\r[Epoch %d/%d] [Batch %d/%d] [Content: %.2f (%.2f) Style: %.2f (%.2f) Total: %.2f (%.2f)]"
                % (
                    epoch + 1,
                    args.epochs,
                    batch_i,
                    len(train_dataset),
                    content_loss.item(),
                    np.mean(epoch_metrics["content"]),
                    style_loss.item(),
                    np.mean(epoch_metrics["style"]),
                    total_loss.item(),
                    np.mean(epoch_metrics["total"]),
                )
            )
            k += 1

            if k%500 == 0:
                save_sample(batches_done)
                style_name = os.path.basename(args.style_image).split(".")[0]
                torch.save(transformer.state_dict(), f"checkpoints/{style_name}_%{batches_done}.pth")

            batches_done = epoch * len(dataloader) + batch_i + 1
            if batches_done % args.sample_interval == 0:
                save_sample(batches_done)
                style_name = os.path.basename(args.style_image).split(".")[0]
                torch.save(transformer.state_dict(), f"checkpoints/{style_name}_#{batches_done}.pth")
            
            print('  ', args.checkpoint_interval, batches_done)
            if args.checkpoint_interval > 0 and batches_done % args.checkpoint_interval == 0:
                style_name = os.path.basename(args.style_image).split(".")[0]
                torch.save(transformer.state_dict(), f"checkpoints/{style_name}_{batches_done}.pth")
