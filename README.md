# **Проект: Style-Transfer**

## Ссылка на презентацию проекта
[Презентация проекта стилизации изображений](https://github.com/VetaShine/Style-Transfer/blob/main/StyleTransfer_presentation.pdf)  

## Ссылка на демонстрацию работы проекта
[Демонстрация работы](https://drive.google.com/file/d/1iLvPYBFEonq8fy6-j2FDzqLlf7ol4hq1/view?usp=sharing)

## Таблица участников  

| ФИО                 | Номер группы      | Обязанности                                |
|---------------------|-------------------|-------------------------------------------|
| Журавлев К.И       | М8О-410Б-21       | анализ литературы, настройка работы инфраструктуры cloud.ru, разработка Telegram-бота, настройка взаимодействия сервера и бота с облачным хранилищем, оформление документации, создание презентации |
| Минеева С.А        | М8О-410Б-21       | обучение модели стилизации, интеграция моделей стилизации и детекции негативного контента, разработка Telegram-бота и его интеграция с сервером, реализация внутренней логики сервера, оформление документации|
| Русаков А.В        | М8О-410Б-21       | развертывание виртуальной машины, реализация внутренней логики сервера, настройка взаимодействия сервера и бота с облачным хранилищем, дебаггинг кода, оформление документации, съемка видео-демонстрации работы проекта|

## **Описание**
Проект - телеграм бот стилизации изображений. Стилизация изображений происходит за счет предварительно подготовленной свёрточной нейронной сети выделения признаков изображений - VGG16, самостоятельно обученной для пяти стилей. Обученные веса модели можно скачать [здесь](https://disk.yandex.ru/d/0HQSxoOTknugWw). Перед стилизацией изображение проверяется на наличие негативного контента с помощью использования готовой модели [NSFW Classifier](https://github.com/lakshaychhabra/NSFW-Detection-DL/tree/master). Также скачать веса модели и посмотреть демонстрацию ее работы можно в папке проекта [nsfw_model](https://github.com/VetaShine/Style-Transfer/tree/main/nsfw_model). Телеграм бот реализован с помощью библиотеки aiogram в асинхронном режиме. Для хранения запросов пользователей в виде «ключ-значение» используется хранилище данных Redis. Очереди сообщений реализуются с помощью брокера сообщений RabbitMQ. Загрузка обученных весов моделей и хранение присылаемых пользователем изображений и сгенерированных изображений реализуются с помощью облачного хранилища S3 Evolution Object Storage. 

## **Запуск проекта**
1. Склонировать репозиторий:
  ```
  git clone https://github.com/VetaShine/Style-Transfer.git
  ```
2. Создать и настроить окружение в файле `.env`, используя `.env.example`:
  ```
  cp .env.example .env
  ```
3. Собрать и запустить *docker-compose*:
  ```
  docker-compose up --build
  ```

## **Бизнес-цель проекта**
Основной бизнес-целью проекта является создание инновационного платного сервиса для стилизации изображений в Telegram, который предлагает пользователям уникальные художественные стили на основе мощной нейронной сети. Основная цель — монетизация через модель подписки и платные запросы, что позволит пользователям получать доступ к высококачественным результатам стилизации. 

## **ML-цель проекта**
Основной ML-целью проекта является достижение высокой точности в задаче стилизации изображений и фильтрации неподобающего контента, обеспечив при этом быструю и качественную обработку запросов пользователей.

## **Архитектура**

### Схема C4
Ниже представлена архитектурная схема системы, соответствующая стандарту C4:  
1. **Контекст (Context):** Показывает взаимодействие пользователей и внешних систем с приложением.
![Схема контекста](https://github.com/VetaShine/Style-Transfer/blob/main/images/context.png)  
2. **Контейнеры (Containers):** Описывает верхнеуровневую архитектуру.
![Схема контейнеров](https://github.com/VetaShine/Style-Transfer/blob/main/images/containers.png)
3. **Компоненты (Components):** Углублённое описание каждого контейнера.
![Схема компонентов](https://github.com/VetaShine/Style-Transfer/blob/main/images/components.png)
4. **Код (Code):** Включает структуру ключевых частей кода.
   ``` text
   /root
   │
   ├── bot/                       # Каталог с кодом Telegram-бота
   │   ├── app.py                 # Основной файл для запуска бота
   │   ├── client.py              # Логика взаимодействия с сервером
   │   ├── handler.py             # Обработчики команд и событий
   │   ├── logging_config.py      # Настройка логирования
   │   ├── requirements.txt       # Зависимости для бота
   │   └── Dockerfile             # Dockerfile для сборки контейнера бота
   │
   ├── server/                    # Каталог с серверной частью
   │   ├── detector.py            # Загрузки модели для детекции негативного контента
   │   ├── models.py              # Загрузка модели для стилизации изображений
   │   ├── server.py              # Основной серверный файл
   │   ├── utils.py               # Вспомогательные функции
   │   ├── logging_config.py      # Настройка логирования
   │   ├── requirements.txt       # Зависимости для сервера
   │   └── Dockerfile             # Dockerfile для сборки контейнера сервера
   │
   ├── docker-compose.yml         # Оркестрация контейнеров
   ```

## **Обоснование архитектуры**
Архитектура проекта основана на модульности и асинхронности, что позволяет обеспечить высокую производительность, масштабируемость и надежность системы. Выбор технологий был обусловлен как функциональными требованиями проекта, так и преимуществами конкретных инструментов. Ниже приводится обоснование архитектурных решений и выбора технологий.

* **Язык программирования: Python**

Python был выбран за его простоту, читабельность и обширную экосистему библиотек для машинного обучения и обработки данных, таких как TensorFlow, PyTorch, NumPy и PIL. Эти особенности сделали Python оптимальным выбором для быстрой разработки и интеграции ML-решений.

**Почему не другой язык?**
Альтернативы, такие как Java или C++, требуют большего времени на реализацию и имеют меньшую популярность среди библиотек для обработки изображений и нейронных сетей.

* **ML-фреймворк: TensorFlow и PyTorch**

Эти фреймворки предоставляют все необходимое для разработки, обучения и применения сложных нейронных сетей. В проекте VGG16 используется как часть модели для выделения признаков изображений. TensorFlow и PyTorch обеспечивают гибкость в настройке и высокую производительность при работе с большими объемами данных.

**Почему не OpenCV или Scikit-learn?**
Эти библиотеки недостаточно мощны для работы с глубокими нейронными сетями и не поддерживают современные архитектуры, такие как VGG16.

* **Оркестрация контейнеров: Docker**

Docker позволяет упаковать приложение вместе со всеми зависимостями, обеспечивая совместимость и упрощая развёртывание в различных средах. Контейнеризация делает систему более управляемой и масштабируемой.

**Почему не VirtualBox или подобные технологии?**
VirtualBox требует значительно больше ресурсов, тогда как Docker работает с контейнерами, которые легче и быстрее.

* **Брокер сообщений: RabbitMQ**

RabbitMQ обеспечивает асинхронное взаимодействие между компонентами системы. Это особенно важно для задач стилизации изображений, которые требуют времени на обработку, и проверки изображений на неприемлемый контент. Асинхронная обработка позволяет разгрузить основные процессы и улучшить отзывчивость бота.

**Почему не Celery или Kafka?**
Celery использует Redis как брокер, что менее эффективно для сложных очередей сообщений. Kafka лучше подходит для потоковой обработки данных, но RabbitMQ проще в настройке и более универсален.

* **Хранилище данных: Redis**

Redis используется для временного хранения данных в формате «ключ-значение», таких как информация о запросах пользователей. Этот инструмент отличается низкой задержкой и высокой скоростью обработки запросов.

**Почему не PostgreSQL?**
База данных SQL или NoSQL избыточна для временного хранения информации и не обеспечивает такой же скорости доступа.

* **Облачная инфраструктура: Cloud.ru (Evolution)**

Cloud.ru предоставляет удобную и производительную облачную инфраструктуру, которая позволяет масштабировать проект в зависимости от нагрузки. Высокая доступность сервиса обеспечивает бесперебойную работу бота.

**Почему не Google Cloud или подобные инфраструктуры?**
Cloud.ru предлагает более доступные тарифы и соответствует требованиям локального рынка.

* **Объектное хранилище: S3 Evolution Object Storage**

Объектное хранилище используется для долговременного хранения изображений и данных. S3 Evolution поддерживает управление большими объемами данных, предоставляя быстрый доступ и возможность масштабирования.

**Почему не локальное хранилище?**
Локальное хранилище сложно масштабировать и обеспечить высокую доступность данных.

## **Стек технологий**
Для реализации проекта использовались следующие технологии:

| Компонент            | Технология                        | Обоснование                                                                 |
|----------------------|------------------------------------|-----------------------------------------------------------------------------|
| Язык программирования| Python                            | Большое количество библиотек для ML, простота написания кода               |
| ML-фреймворк         | TensorFlow, PyTorch              | Высокая производительность, поддержка сложных нейронных сетей              |
| Оркестрация          | Docker              | Для контейнеризации и масштабирования приложения                           |
| Оркестрация сообщений| RabbitMQ             | Для асинхронной обработки задач, управления очередями сообщений и улучшения производительности взаимодействия между компонентами системы         |
| Хранилище данных     | Redis              | Для хранения временных данных и быстрого доступа к часто используемой информации                           |
| Виртуальная машина   | Cloud.ru (Evolution)     | Для размещения и масштабирования приложения в облачной среде с высокими показателями доступности и производительности                           |
| Объектное хранилище  | S3 Evolution Object Storage | Для хранения и управления большими объемами данных с возможностью быстрого доступа и масштабирования                           |
