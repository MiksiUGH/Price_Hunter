"""Модуль со всеми функциями для парсинга и вспомогательными функциями для парсинга"""
import time
import re
import datetime
import abc
import logging

from decimal import Decimal
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager
from django.db import transaction

from selenium import webdriver, common
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from core.models import Offer, PriceHistory
from .string_utils import clean_product_name, str_in_date


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
    options.add_argument('--headless')

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


class AbstractParser(abc.ABC):
    """Абстрактный класс парсера для работы с маркетплейсами."""

    @staticmethod
    @abc.abstractmethod
    def search_by_query(query: str, answer_cnt: int = 20, price_limit: list[int] = None, delivery_limit: int = None) -> list[dict[str, str | bool | float]]:
        """Поиск товаров на маркетплейсе по пользовательскому запросу с возможностью фильтрации.

        :param query: Поисковый запрос (название товара или категория)
        :type query: str
        :param answer_cnt: Количество товаров для возврата (допустимый диапазон: 10–30), по умолчанию 20
        :type answer_cnt: int, optional
        :param price_limit: Диапазон цен для фильтрации в формате [min_price, max_price], по умолчанию None (без фильтрации)
        :type price_limit: list[int], optional
        :param delivery_limit: Максимальное количество дней для срока доставки, по умолчанию None (без ограничения)
        :type delivery_limit: int, optional
        :return: Список словарей с информацией о найденных товарах (отсортированных по возрастанию цены),
            каждый словарь содержит ключи: 'name' (название), 'price' (цена), 'availability' (наличие),
            'article_number' (артикул), 'url' (ссылка на товар), 'delivery_time' (срок доставки)
        :rtype: list[dict[str, str | bool | float]]
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def search_by_url(url: str) -> dict[str, str | bool | float]:
        """Получение подробной информации о конкретном товаре по его URL.

        :param url: URL страницы товара на маркетплейсе
        :type url: str
        :return: Словарь с информацией о товаре, содержащий ключи:
            'name' (название), 'price' (цена), 'availability' (наличие),
            'article_number' (артикул), 'url' (ссылка), 'delivery_time' (срок доставки).
            При ошибке возвращает словарь с ключом 'error' и описанием ошибки.
        :rtype: dict[str, str | bool | float]
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def update_and_save_batch(urls: list[str]) -> list[dict[str, str | bool | float]] | None:
        """Массовое обновление информации о нескольких товарах по их URL.

        :param urls: Список URL страниц товаров для обновления информации
        :type urls: list[str]
        :return: Список словарей с обновлённой информацией о товарах
            (каждый словарь соответствует формату из search_by_url).
            При возникновении ошибки возвращает словарь с ключом 'error'.
            Если все запросы завершились ошибкой, может вернуть None.
        :rtype: list[dict[str, str | bool | float]] | None
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def update_by_url(dr: webdriver.Chrome, url: str) -> dict[str, float | bool]:
        """Обновление информации о конкретном товаре (цена и наличие) по URL с использованием переданного драйвера.

        :param dr: Экземпляр драйвера браузера (webdriver.Chrome), используемый для выполнения запросов
        :type dr: webdriver.Chrome
        :param url: URL страницы товара для обновления информации
        :type url: str
        :return: Словарь с обновлёнными данными о товаре, содержащий:
            - 'new_price' (обновлённая цена, float) и 'availability' (наличие, bool),
              если товар доступен;
            - только 'availability' (bool), если товар отсутствует;
            - при ошибке — словарь с ключом 'error' и описанием проблемы.
        :rtype: dict[str, float | bool]
        """
        ...


class WbParser(AbstractParser):
    """
    Парсер данных о товарах с ВБ
    """
    @staticmethod
    def _open_filter_menu(dr: webdriver.Chrome) -> None:
        """
        Открывает меню со всеми фильтрами.
        Вспомогательный метод для основного парсинга

        :param dr: Драйвеп браузера
        :type dr: webdriver.Chrome
        """
        filter_btn = dr.find_element(By.CSS_SELECTOR, 'button.dropdown-filter__btn--all')
        filter_btn.click()

    @staticmethod
    def _apply_used_filters(dr: webdriver.Chrome) -> None:
        """
        Применяет установленные фильтры.
        Вспомогательный метод для основного парсинга

        :param dr: _description_
        :type dr: webdriver.Chrome
        """
        apply_btn = WebDriverWait(dr, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.filters-desktop__btn-main"))
        )
        apply_btn.click()

    @staticmethod
    def _use_price_limit(dr: webdriver.Chrome, limit: list[int]) -> None:
        """
        Добавление диапозона цен при парсинге по названию.
        Вспомогательный метод для основного парсинга

        :param dr: Драйвер браузера
        :type dr: webdriver.Chrome
        :param limit: Диапозон цен
        :type limit: list[int]
        """
        left_limit = WebDriverWait(dr, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='startN']"))
        )
        left_limit.clear()
        left_limit.send_keys(str(limit[0]))

        right_limit = WebDriverWait(dr, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='endN']"))
        )
        right_limit.clear()
        right_limit.send_keys(str(limit[-1]))

    @staticmethod
    def _update_availability(dr: webdriver.Chrome) -> bool:
        """
        Проверяет есть ли товар в наличии при обновлении.
        Вспомогательный метод для основного парсинга

        :param dr: Драйвер браузера
        :type dr: webdriver.Chrome
        :return: Есть ли в наличии обновляемый товар
        :rtype: bool
        """
        try:
            dr.find_element(By.XPATH, '//span[text()="Добавить в корзину"]')
            return True
        except common.NoSuchElementException:
            return False

    @staticmethod
    def _check_availability(card) -> bool:
        """
        Проверяет есть ли товар в наличии при поиске.
        Вспомогательный метод для основного парсинга

        :param card: HTML-разметка карты товара
        :return: В наличии товар или нет
        :rtype: bool
        """
        try:
            card.find_element(By.CSS_SELECTOR, 'a.product-card__add-basket')
            return True
        except common.NoSuchElementException:
            return False

    @staticmethod
    def search_by_query(query: str, answer_cnt: int = 20, price_limit: list[int] = None, delivery_limit: int = None) -> list[dict[str, str | bool | float]]:
        """Поиск товаров на ВБ по запросу от пользователя

        :param query: То, что мы ищем на маркетплейсе
        :type query: str
        :param answer_cnt: Сколько товаров нужно вернуть(10 <= answer_cnt <= 30), defaults to 20
        :type answer_cnt: int
        :param price_limit: Диапозон цены, defaults to None
        :type price_limit: list[int]
        :param delivery_limit: Ограничение по сроку доставки, defaults to None
        :type delivery_limit: int
        :return: Самые дешевые товары из найденных
        :rtype: list[dict[str, str | bool | float]]
        """
        driver: webdriver.Chrome = get_driver()
        res_cnt: int = answer_cnt
        try:
            driver.get(WB_URL + query)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn-icon__white')))
            time.sleep(2)

            sort_btn = driver.find_element(By.CSS_SELECTOR, 'button.dropdown-filter__btn--sorter')
            actions: ActionChains = ActionChains(driver)
            actions.move_to_element(sort_btn).perform()
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='По возрастанию цены']"))
            )
            button.click()

            if price_limit:
                WbParser._open_filter_menu(driver)
                WbParser._use_price_limit(driver, price_limit)
                WbParser._apply_used_filters(driver)
            time.sleep(1)

            try:
                WebDriverWait(driver, 1.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'b.not-found-result__title'))
                )
                return {'error': 'ResNotFound'}

            except common.TimeoutException:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.product-card')))
                result: list[dict[str, str | bool | float]] = []
                pars_cnt: int = 0
                existing_articles: set[str] = set(Offer.objects.filter(
                    shop__slug='wb',
                    is_active=True,
                    article__isnull=False
                ).values_list('article', flat=True))

                while res_cnt > 0:
                    left: int = answer_cnt * 2 * pars_cnt
                    right: int = answer_cnt * 2 * (pars_cnt + 1)
                    cards = driver.find_elements(By.CSS_SELECTOR, 'article.product-card')[left:right]
                    if not cards:
                        break
                    driver.execute_script("arguments[0].scrollIntoView(true);", cards[0])
                    for card in cards:
                        if res_cnt == 0:
                            break
                        try:
                            article_number: str = card.get_attribute('data-nm-id')
                            if article_number in existing_articles:
                                continue

                            delivery_time: str = card.find_element(By.CSS_SELECTOR, 'span[data-helper="delivery-display"]').text
                            if delivery_limit:
                                if str_in_date(delivery_time) - datetime.date.today() > datetime.timedelta(days=delivery_limit):
                                    continue

                            name: str = card.find_element(By.CSS_SELECTOR, 'span.product-card__name').text.lstrip('/').strip()
                            price: float = price_in_float(card.find_element(By.CSS_SELECTOR, 'ins.price__lower-price').text)
                            availability: bool = WbParser._check_availability(card)
                            url_el = card.find_element(By.CSS_SELECTOR, 'a.product-card__link')
                            url: str = url_el.get_attribute('href')
                            product: dict[str, str | bool | float] = {
                                'name': name,
                                'price': price,
                                'availability': availability,
                                'article_number': article_number,
                                'url': url,
                                'delivery_time': delivery_time.strip().replace(',', ''),
                                'marketplace': 'Wildberries',
                            }
                            result.append(product)
                            res_cnt -= 1
                            existing_articles.add(article_number)

                        except Exception:
                            continue
                    pars_cnt += 1

                return result

        except Exception as e:
            return {'error': e}

        finally:
            driver.quit()

    @staticmethod
    def search_by_url(url: str) -> dict[str, str | bool | float]:
        """
        Поиск товара на ВБ по url

        :param url: url товара, который ищем
        :type url: str
        :return: Информация о найденном товаре
        :rtype: dict[str, str | bool | float]
        """
        try:
            driver: webdriver.Chrome = get_driver()
            driver.get(url)
            try:
                WebDriverWait(driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.content404__title'))
                )
                return {'error': 'Content404'}

            except common.TimeoutException:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sellerInfoNameDefaultText--qLwgq')))
                name: str = driver.find_element(By.CSS_SELECTOR, 'h2.productTitle--lfc4o').text
                try:
                    price: float | None = price_in_float(driver.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_danger').text)
                except common.NoSuchElementException:
                    try:
                        price = price_in_float(driver.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_accent').text)
                    except common.NoSuchElementException:
                        price = price_in_float(driver.find_element(By.CSS_SELECTOR, 'ins.priceBlockFinalPrice--iToZR').text)
                availability: bool = WbParser._update_availability(driver)
                article_number: str = driver.find_element(By.CSS_SELECTOR, 'button.cellCopy--sPwsd > span').text
                delivery_time: str = driver.find_element(By.CSS_SELECTOR, 'div.deliveryTitleWrapper--WMRNu > span').text
                product: dict[str, str | bool | float] = {
                    'name': name,
                    'price': price,
                    'availability': availability,
                    'article_number': article_number,
                    'url': url,
                    'delivery_time': delivery_time.strip().replace(',', ''),
                    'marketplace': 'Wildberries',
                }
                return product

        except Exception as e:
            return {'error': e}

        finally:
            driver.quit()

    @staticmethod
    def update_and_save_batch(urls: set[str]) -> set[Offer | None]:
        """
        Обновляет сразу несколько товаров по их url

        :param urls: Множество с url обновляемых товаров
        :type urls: set[str]
        :return: Множество успешно обновленных товаров
        :rtype: set[Offer | None]
        """
        try:
            driver: webdriver.Chrome = get_driver()
            res: set[Offer] = set()
            for url in urls:
                updated_offer = WbParser.update_by_url(driver, url)
                if 'error' in updated_offer:
                    logging.error('Ошибка при парсинге(update_by_url): %s', updated_offer['error'])
                    continue

                try:
                    with transaction.atomic():
                        offer: Offer = Offer.objects.select_for_update().get(url=url)
                        if offer.price != Decimal(updated_offer['new_price']) or offer.in_stock != updated_offer['availability']:
                            _ = PriceHistory.objects.create(
                                price=Decimal(updated_offer['new_price']),
                                in_stock=updated_offer['availability'],
                                offer=offer,
                            )

                        offer.price = Decimal(updated_offer['new_price'])
                        offer.in_stock = updated_offer['availability']
                        offer.title = clean_product_name(updated_offer.get('new_name', offer.title))
                        offer.delivery_days = (str_in_date(updated_offer['new_delivery_time']) - datetime.date.today()).days
                        offer.save()
                        res.add(offer)

                except Offer.DoesNotExist:
                    logging.warning('Offer с URL %s не найден(update_and_save_batch)', url)
                    continue

                except Exception as e:
                    logging.error('Ошибка при обновлении данных предложения(update_and_save_batch): %s', e)
                    continue

            return res

        except Exception as e:
            logging.error('Ошибка в работе update_and_save_batch: %s', e)
            return res

        finally:
            driver.quit()

    @staticmethod
    def update_by_url(dr: webdriver.Chrome, url: str) -> dict[str, float | bool]:
        """Обновление информации о товаре на ВБ по url

        :param dr: Драйвер браузера
        :type dr: webdriver.Chrome
        :param url: url обновляемого товара
        :type url: str
        :return: Обновленные цена и наличие товара
        :rtype: dict[str, float | bool]
        """
        try:
            dr.get(url)
            try:
                WebDriverWait(dr, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.content404__title'))
                )
                return {'error': 'Content404'}
            except common.TimeoutException:
                WebDriverWait(dr, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sellerInfoNameDefaultText--qLwgq')))

                availability: bool = WbParser._update_availability(dr)
                new_name: str = dr.find_element(By.CSS_SELECTOR, 'h2.productTitle--lfc4o').text
                try:
                    new_price: float | None = price_in_float(dr.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_danger').text)
                except common.NoSuchElementException:
                    try:
                        new_price = price_in_float(dr.find_element(By.CSS_SELECTOR, 'h2.mo-typography_color_accent').text)
                    except common.NoSuchElementException:
                        new_price = price_in_float(dr.find_element(By.CSS_SELECTOR, 'ins.priceBlockFinalPrice--iToZR').text)
                new_delivery_time: str = dr.find_element(By.CSS_SELECTOR, 'div.deliveryTitleWrapper--WMRNu > span').text

                result: dict[str, bool | float] = {
                    'new_name': new_name,
                    'new_price': new_price,
                    'availability': availability,
                    'new_delivery_time': new_delivery_time.strip().replace(',', ''),
                }

                return result

        except Exception as e:
            return {'error': e}


class OzonParser(AbstractParser):
    """
    Парсер данных о товарах с Ozon
    """
    @staticmethod
    def use_price_limit(dr: webdriver.Chrome, limit: list[int]) -> None:
        """
        

        :param dr: _description_
        :type dr: webdriver.Chrome
        :param limit: _description_
        :type limit: list[int]
        """
        ...

    @staticmethod
    def update_availability(dr: webdriver.Chrome) -> bool:
        """
        

        :param dr: _description_
        :type dr: webdriver.Chrome
        :return: _description_
        :rtype: bool
        """

    @staticmethod
    def check_availability(card) -> bool:
        """
        

        :param card: _description_
        :type card: _type_
        :return: _description_
        :rtype: bool
        """
        ...

    @staticmethod
    def search_by_query(query: str, answer_cnt: int = 20, price_limit: list[int] = None, delivery_limit: str = None) -> list[dict[str, str | bool | float]]:
        """
        

        :param query: _description_
        :type query: str
        :param answer_cnt: _description_, defaults to 20
        :type answer_cnt: int, optional
        :param price_limit: _description_, defaults to None
        :type price_limit: list[int], optional
        :param delivery_limit: _description_, defaults to None
        :type delivery_limit: str, optional
        :return: _description_
        :rtype: list[dict[str, str | bool | float]]
        """
        ...

    @staticmethod
    def search_by_url(url: str) -> dict[str, str | bool | float]:
        """
        

        :param url: _description_
        :type url: str
        :return: _description_
        :rtype: dict[str, str | bool | float]
        """
        ...

    @staticmethod
    def update_by_url(url: str) -> dict[str, float | bool]:
        """Обновление информации о товаре по url

        :param url: url обновляемого товара
        :type url: str
        :return: Обновленные цена и наличие товара
        :rtype: dict[str, float | bool]
        """
        ...


class YandexMarketParser(AbstractParser):
    """
    Парсер данных о товарах с YandexMarket
    """
    ...
