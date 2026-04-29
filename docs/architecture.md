# Архитектура проекта PriceHunter

## Общее описание
PriceHunter – веб-приложение для отслеживания цен на товары в интернет-магазинах (Wildberries, в перспективе Ozon). Пользователи ищут товары, подписываются на конкретные предложения и получают email-уведомления при снижении цены или появлении товара в наличии.

## Стек технологий
- **Backend:** Python 3.12+, Django 5.x
- **База данных:** SQLite (в разработке), позже PostgreSQL (при необходимости)
- **Парсинг:** Selenium + ChromeDriver, BeautifulSoup (не используется напрямую, только Selenium)
- **Фоновые задачи:** кастомные management commands + cron (на сервере)
- **Почта:** SMTP (django.core.mail)
- **Фронтенд:** HTML, Sass (препроцессор CSS), чистый JavaScript (Chart.js для графиков)
- **Аутентификация:** django-allauth (email/пароль)

## Структура проекта (вариант 1 – одно приложение `core`)

    pricehunter/
    ├── core/
    │ ├── models.py # Shop, Product, Offer, PriceHistory, Subscription
    │ ├── admin.py # Настройки админки
    │ ├── views.py # Все представления (поиск, товар, подписка, профиль)
    │ ├── urls.py # Маршруты приложения
    │ ├── forms.py # Формы (поиск, подписка, редактирование профиля)
    │ ├── utils/
    │ │ ├── parsers.py # Классы WbParser, OzonParser
    │ │ ├── db_saver.py # Сохранение результатов парсинга в БД
    │ │ ├── notifications.py # Отправка email
    │ │ └── helpers.py # price_in_float, извлечение артикулов и т.п.
    │ └── management/
    │ └── commands/
    │ ├── update_prices.py # Обновление цен для Offer с подписками
    │ └── cleanup_old.py # Удаление старых записей (опционально)
    ├── static/ # CSS, JS, изображения
    ├── templates/ # base.html, search.html, product.html, dashboard.html
    ├── docs/ # Документация
    ├── requirements.txt
    └── manage.py

## Модели данных и связи
- **Shop** – магазин (Wildberries, Ozon). Поля: name, slug, search_url_template, is_active.
- **Product** – абстрактный товар. Поля: name, slug.
- **Offer** – конкретное предложение (связь Product + Shop). Поля: url, article, price, in_stock, is_active, last_updated.
- **PriceHistory** – история цен для Offer. Поля: price, in_stock, checked_at.
- **Subscription** – подписка пользователя на Offer. Поля: target_price, notify_on_drop, notify_on_restore, last_notified_price, is_active.

Связи:
- Shop 1 → * Offer
- Product 1 → * Offer
- Offer 1 → * PriceHistory
- Offer 1 → * Subscription
- User 1 → * Subscription

## Основные сценарии использования

### Поиск товара
1. Пользователь вводит запрос в строку поиска.
2. Представление `search` вызывает `WbParser.search_wb(query)` (и, возможно, другие парсеры).
3. Результаты (список словарей) передаются в функцию `save_search_results()`, которая:
   - Для каждого найденного товара создаёт или получает `Product` (по нормализованному названию).
   - Создаёт или обновляет `Offer` (уникальность по product+shop+article).
   - Сохраняет текущую цену в `PriceHistory` (если изменилась).
4. Список `Offer` отображается на странице результатов.

### Подписка
1. На странице товара (или результатов) пользователь выбирает конкретное `Offer` и задаёт условия.
2. Форма отправляет POST → создаётся `Subscription`, связанная с `user` и `offer`.
3. Пользователь видит подписку в личном кабинете.

### Фоновое обновление цен
1. Cron запускает `python manage.py update_prices` (например, каждые 3 часа).
2. Команда:
   - Получает все уникальные `Offer`, на которые есть активные подписки.
   - Для каждого `Offer` вызывает `WbParser.update_product_wb(offer.url)`.
   - Обновляет поля `price`, `in_stock`, `last_updated` в `Offer`.
   - Создаёт новую запись в `PriceHistory` (если цена изменилась).
   - Для каждой подписки на этот `Offer` проверяет условия:
     - Если `notify_on_drop` и новая цена < старой (или < `target_price`), отправляет email.
     - Если `notify_on_restore` и товар вернулся в наличие, отправляет email.
   - Обновляет `last_notified_price` в `Subscription`.

### Уведомления
- Email отправляется через настроенный SMTP (например, Gmail).
- Шаблоны писем: простой текст или HTML.

## Безопасность и производительность
- Переменные окружения (SECRET_KEY, DEBUG, почтовые настройки) через `python-decouple`.
- Для обновления цен используются задержки между запросами (2 секунды), чтобы не перегружать Wildberries.
- Обновляются только `Offer` с активными подписками (не все).
- Админка доступна только суперпользователям.

## Планы по развитию
- Добавить парсер Ozon (после решения проблемы блокировки).
- Добавить сохранение изображений товаров.
- Внедрить фильтрацию по цене и сроку доставки.
- Перейти на PostgreSQL.
- Реализовать телеграм-бота для уведомлений.