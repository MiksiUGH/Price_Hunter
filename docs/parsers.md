# Парсеры Wildberries и Ozon

## Общая информация
Парсеры используют Selenium с ChromeDriver. Причины: маркетплейсы активно блокируют простые `requests`, поэтому требуется эмуляция реального браузера. Настройки драйвера включают маскировку автоматизации, отключение уведомлений, фиксированный размер окна, случайный User-Agent.

## Wildberries (класс `WbParser`)

### Метод `search_wb(query: str) -> list[dict]`
- Выполняет поиск по запросу на `https://www.wildberries.ru/catalog/0/search.aspx?search={query}`
- Сортирует результаты **по возрастанию цены** (клик по кнопке «По возрастанию цены»)
- Извлекает первые 20 карточек товаров (селектор `article.product-card`)
- Для каждой карточки получает:
  - Название (`span.product-card__name`)
  - Цену (из `ins.price__lower-price`, преобразует в float через `price_in_float`)
  - Наличие (проверяет наличие кнопки `a.product-card__add-basket`)
  - URL (`a.product-card__link`)
  - Артикул (атрибут `data-nm-id`)
- Возвращает список словарей.

### Метод `update_product_wb(url: str) -> dict`
- Открывает страницу товара по прямой ссылке
- Ждёт загрузки (признак: элемент `span.sellerInfoNameDefaultText--qLwgq`)
- Проверяет наличие кнопки `button.buyNowButton--akeKg` (если есть – товар в наличии)
- Извлекает цену (пробует три варианта CSS-селекторов: `h2.mo-typography_color_danger`, `h2.mo-typography_color_accent`, `ins.priceBlockFinalPrice--iToZR`)
- Возвращает словарь с ключами `new_price` (float или None) и `availability` (bool)

### Вспомогательные функции
- `get_chrome_options()` – настройки браузера (скрытие автоматизации, отключение уведомлений, размер окна)
- `get_driver()` – создание драйвера с подстановкой случайного User-Agent
- `check_availability(card, mp)` – проверка наличия в поисковой выдаче
- `update_availability(dr, mp)` – проверка наличия на странице товара
- `price_in_float(price)` – очистка строки цены и преобразование в число

## Ozon (класс `OzonParser`)
Пока не реализован, так как Ozon активно блокирует автоматизированные запросы. Планируется использовать `undetected-chromedriver` или API продавца. Заглушки методов `search_ozon` и `update_product_ozon` присутствуют.

## Текущие ограничения
- Только Wildberries.
- Зависимость от стабильности CSS-селекторов (при изменении вёрстки парсер сломается).
- Selenium открывает видимый браузер (headless отключён для отладки).
- Не обрабатываются ситуации с капчей.