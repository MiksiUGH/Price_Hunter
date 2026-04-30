"""Утилиты для работы со строками"""
import re


STOP_WORDS: set[str] = {
    'купить', 'заказать', 'цена', 'дешево', 'недорого', 'официальный',
    'гарантия', 'продажа', 'магазин', 'интернет', 'доставка', 'скидка',
    'лучший', 'новый', 'оригинал', 'копия', 'аналог', 'подарок',
    'в', 'на', 'с', 'по', 'для', 'и', 'или', 'но', 'да', 'же'
}


def normalize_name(name: str) -> str:
    """
    Нормализует имя или запрос

    :param name: Изначальоне имя
    :type name: str
    :return: Нормализованное имя
    :rtype: str
    """
    if not name:
        return ''

    name = name.lower()
    name = name.replace('ё', 'е')
    name = re.sub(r'[^\w\s]', '', name)
    words = name.split()
    words = [w for w in words if w not in STOP_WORDS]
    normalized = ' '.join(words)
    return normalized
