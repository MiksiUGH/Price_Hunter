"""Модуль со всеми функциями для парсинга и вспомогательными функциями для парсинга"""
import time
import re

from selenium import webdriver, common
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager


OZON_URL: str = 'https://www.ozon.ru/search/?from_global=true&text='
WB_URL: str = 'https://www.wildberries.ru/catalog/0/search.aspx?search='


def get_chrome_options() -> Options:
    """
    Создает объект с опциями для драйвера браузера

    :return: Обьект с настройками драйвера
    :rtype: Options
    """
    options = Options()

    # 1. Базовые опции для скрытия автоматизации
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # 2. Отключаем WebRTC (чтобы не было утечки реального IP)
    options.add_argument('--force-webrtc-ip-handling-policy=default_public_interface_only')

    # 3. Отключаем автоматическое воспроизведение медиа
    options.add_argument('--autoplay-policy=no-user-gesture-required')

    # 4. Задаём язык
    options.add_argument('--lang=ru-RU')

    # 5. Убираем лишние уведомления
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')

    # 6. Опции для стабильности
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-setuid-sandbox')

    # 7. Имитация экрана (чтобы не было fingerprint)
    options.add_argument('--window-size=1920,1080')

    # 8. Если нужен headless — раскомментируй, но для отладки лучше видимый браузер
    # options.add_argument('--headless')

    # 9. Отключаем сохранение паролей и автозаполнение
    options.add_argument('--disable-save-password-bubble')
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
    })

    return options


def get_driver() -> webdriver.Chrome:
    """
    Создает объект драйвера браузера

    :return: Драйвер браузера
    :rtype: webdriver.Chrome
    """
    options: Options = get_chrome_options()
    ua: UserAgent = UserAgent()
    user_agent: str = ua.random
    options.add_argument(f'user-agent={user_agent}')
    service: Service = Service(ChromeDriverManager().install())
    driver: webdriver.Chrome = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def check_availability(card, mp: str) -> bool:
    """
    Проверяет есть ли товар в наличии при поиске

    :param card: HTML-разметка карты товара
    :param mp: Маркетплейс, на котором ищем
    :type mp: str
    :return: В наличии товар или нет
    :rtype: bool
    """
    try:
        if mp == 'ozon':
            ...
        elif mp == 'wb':
            card.find_element(By.CSS_SELECTOR, 'a.product-card__add-basket')
        return True
    except common.NoSuchElementException:
        return False


def extract_ozon_sku(url: str) -> str | None:
    """
    Достает артикул из ссылки Ozon на товар

    :param url: Ссылка на товар
    :type url: str
    :return: Артикул товара
    :rtype: str | None
    """
    match = re.search(r'/product/.*?-(\d+)(?:/|\?)', url)
    if match:
        return match.group(1)
    return None


def price_in_float(price: str) -> float | None:
    """
    Представление цены в виде float

    :param price: Изначальная цена
    :type price: str
    :return: Цена в новом типе данных 
    :rtype: float | None
    """
    if not price:
        return None
    cleaned = re.sub(r'[^\d.,]', '', price)
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None


def update_availability(dr: webdriver.Chrome, mp: str) -> bool:
    """
    Проверяет есть ли товар в наличии при обновлении

    :param dr: Драйвер браузера
    :type dr: webdriver.Chrome
    :param mp: Маркетплейс, на котором проверяем
    :type mp: str
    :return: Есть ли в наличии обновляемый товар
    :rtype: bool
    """
    if mp == 'ozon':
        ...
    elif mp == 'wb':
        try:
            dr.find_element(By.CSS_SELECTOR, 'button.buyNowButton--akeKg')
            return True
        except common.NoSuchElementException:
            return False


class WbParser:
    """
    Парсер данных о товарах с ВБ
    """
    @staticmethod
    def search_wb(query: str) -> list[dict[str, str | bool | float]]:
        """Поиск товаров на ВБ

        :param query: То, что мы ищем на маркетплейсе
        :type query: str
        :return: 20 самых дешевых товаров из найденных
        :rtype: list[dict[str, str | bool | float]]
        """
        driver: webdriver.Chrome = get_driver()
        try:
            driver.get(WB_URL + query)
            wait: WebDriverWait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn-icon__white')))
            time.sleep(2)
            sort_btn = driver.find_element(By.CSS_SELECTOR, 'button.dropdown-filter__btn--sorter')
            actions: ActionChains = ActionChains(driver)
            actions.move_to_element(sort_btn).perform()
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='По возрастанию цены']"))
            )
            button.click()
            time.sleep(1)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.product-card')))
            result: list[dict[str, str | bool | float]] = []
            cards = driver.find_elements(By.CSS_SELECTOR, 'article.product-card')[:20]
            for card in cards:
                try:
                    name: str = card.find_element(By.CSS_SELECTOR, 'span.product-card__name').text
                    price: float = price_in_float(card.find_element(By.CSS_SELECTOR, 'ins.price__lower-price').text)
                    availability: bool = check_availability(card, 'wb')
                    url_el = card.find_element(By.CSS_SELECTOR, 'a.product-card__link')
                    url: str = url_el.get_attribute('href')
                    article_number: str = card.get_attribute('data-nm-id')
                    product: dict[str, str | bool | float] = {
                        'name': name,
                        'price': price,
                        'availability': availability,
                        'article_number': article_number,
                        'url': url,
                    }
                    result.append(product)
                except Exception as e:
                    print(f"Ошибка при парсинге карточки: {e}")
                    continue
            return result
        finally:
            driver.quit()

    @staticmethod
    def update_product_wb(url: str) -> dict[str, float | bool]:
        """Обновление информации о товаре по url

        :param url: url обновляемого товара
        :type url: str
        :return: Обновленные цена и наличие товара
        :rtype: dict[str, float | bool]
        """
        driver: webdriver.Chrome = get_driver()
        try:
            driver.get(url)
            wait: WebDriverWait = WebDriverWait(driver, 12)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sellerInfoNameDefaultText--qLwgq')))
            availability: bool = update_availability(driver, 'wb')
            if availability:
                try:
                    new_price: float | None = price_in_float(driver.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_danger').text)
                except common.NoSuchElementException:
                    try:
                        new_price = price_in_float(driver.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_accent').text)
                    except common.NoSuchElementException:
                        new_price = price_in_float(driver.find_element(By.CSS_SELECTOR, 'ins.priceBlockFinalPrice--iToZR').text)
            else:
                new_price = None
            result: dict[str, bool | float] = {
                'new_price': new_price,
                'availability': availability,
            }
            return result
        finally:
            driver.quit()


class OzonParser:
    """
    Парсер данных о товарах с Ozon
    """
    @staticmethod
    def search_ozon(query: str) -> list[dict[str, str | bool | float]]:
        """Поиск товаров на Озон

        :param query: То, что мы ищем на маркетплейсе
        :type query: str
        :return: 20 самых дешевых товаров из найденных
        :rtype: list[dict[str, str | bool | float]]
        """
        ...

    @staticmethod
    def update_product_ozon(url: str) -> dict[str, float | bool]:
        """Обновление информации о товаре по url

        :param url: url обновляемого товара
        :type url: str
        :return: Обновленные цена и наличие товара
        :rtype: dict[str, float | bool]
        """
        ...
