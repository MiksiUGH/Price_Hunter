"""Утилиты для работы со строками"""
import re
import datetime


STOP_WORDS: set[str] = {
    'купить', 'заказать', 'цена', 'дешево', 'недорого', 'официальный',
    'гарантия', 'продажа', 'магазин', 'интернет', 'доставка', 'скидка',
    'лучший', 'новый', 'оригинал', 'копия', 'аналог', 'подарок',
    'в', 'на', 'с', 'по', 'для', 'и', 'или', 'но', 'да', 'же'
}


def normalize_name(name: str) -> str:
    """
    Нормализует имя товара для поиска и сравнения:
    1. Очищает от мусора (скобки, дубликаты слов и т.п.) через clean_product_name
    2. Приводит к нижнему регистру, заменяет 'ё' на 'е'
    3. Удаляет стоп-слова
    4. Убирает пунктуацию и лишние пробелы

    :param name: Изначальоне имя
    :type name: str
    :return: Нормализованное имя
    :rtype: str
    """
    if not name:
        return ''

    name = clean_product_name(name)
    name = name.lower()
    name = name.replace('ё', 'е')
    name = re.sub(r'[^\w\s]', '', name)
    words = name.split()
    words = [w for w in words if w not in STOP_WORDS]
    normalized = ' '.join(words)
    return normalized.strip()


def str_in_date(str_date: str) -> datetime.date:
    """
    Превращает строку с датой доставки в объект даты

    :param str_date: Строка с датой
    :type str_date: str
    :return: Готовый объект даты
    :rtype: datetime.date
    """
    months = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    try:
        if str_date.capitalize() == 'Завтра':
            return datetime.date.today() + datetime.timedelta(days=1)
        elif str_date.capitalize() == 'Послезавтра':
            return datetime.date.today() + datetime.timedelta(days=2)
        else:
            match = re.match(r'(\d{1,2})\s+(\w+)', str_date)
            day = int(match.group(1))
            month_name = match.group(2)
            month = months[month_name]
            today = datetime.date.today()
            candidate = datetime.date(today.year, month, day)

            if candidate < today:
                candidate = datetime.date(today.year + 1, month, day)

            return candidate
    except Exception:
        return datetime.date.today() + datetime.timedelta(days=60)


def clean_product_name(name: str) -> str:
    """
    Очищает название товара от типового мусора:
    - Удаляет начальные слеши, дефисы, точки
    - Удаляет артикулы в круглых скобках (чисто цифры)
    - Удаляет содержимое квадратных скобок (включая сами скобки)
    - Убирает лишние пробелы
    - Удаляет повторяющиеся слова (игнорируя регистр)
    """
    if not name:
        return ''

    # Удаляем начальные символы: / - . и пробелы
    name = re.sub(r'^[\s/\.\-]+', '', name)
    # Удаляем артикулы в круглых скобках (только цифры, возможно с пробелом)
    name = re.sub(r'\s*\(\s*\d+\s*\)', '', name)
    # Удаляем квадратные скобки с содержимым (например, [White Blue Colour-In])
    name = re.sub(r'\s*\[[^\]]*\]', '', name)

    # Извлекаем слова для обработки дубликатов
    words = re.findall(r'\w+', name)
    seen = set()
    unique_words = []

    for word in words:
        if word.lower() not in seen:
            seen.add(word.lower())
            unique_words.append(word)

    # Восстанавливаем строку из уникальных слов
    cleaned_name = ' '.join(unique_words)

    # Убираем лишние пробелы и возвращаем результат
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
    return cleaned_name.strip()
