# Развёртывание PriceHunter на Selectel VPS (Ubuntu)

Данное руководство описывает процесс установки и настройки проекта PriceHunter на виртуальном сервере (VPS) под управлением Ubuntu 22.04/24.04. Инструкция максимально подробна и подходит для начинающих администраторов.

## 1. Подготовка сервера

### 1.1. Подключение к серверу через SSH

После создания VPS вы получите IP-адрес, логин (обычно `root`) и пароль. На вашем локальном компьютере (Windows, macOS, Linux) выполните:

```bash
ssh root@<IP_сервера>
```

При первом подключении может появиться предупреждение о неизвестном хосте – введите `yes`.

### 1.2. Обновление системы и установка базовых пакетов

```bash
apt update && apt upgrade -y
apt install -y python3-pip python3-venv nginx git supervisor unzip wget gnupg curl
```

**Что установили:**
- `python3-pip` – менеджер пакетов Python
- `python3-venv` – для создания виртуального окружения
- `nginx` – веб-сервер (будет отдавать статику и проксировать запросы)
- `git` – для клонирования репозитория
- `supervisor` – для управления процессом Gunicorn
- `unzip`, `wget`, `curl`, `gnupg` – утилиты для установки Chrome

### 1.3. Установка Google Chrome (для Selenium)

```bash
# Добавляем репозиторий Google Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt update
apt install -y google-chrome-stable
```

Проверьте, что Chrome установлен:

```bash
google-chrome --version
```

### 1.4. Настройка swap (если мало оперативной памяти)

Для VPS с 512–1024 МБ RAM рекомендуется создать swap-файл, чтобы Chrome и Gunicorn не падали из-за нехватки памяти.

```bash
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
```

Проверьте:

```bash
free -h
swapon --show
```

## 2. Создание пользователя для приложения

Запускать веб-приложение от `root` небезопасно. Создадим отдельного пользователя `pricehunter`.

```bash
useradd -m -s /bin/bash pricehunter
```

Параметры:
- `-m` – создаёт домашнюю директорию `/home/pricehunter`
- `-s /bin/bash` – назначает оболочку bash

## 3. Клонирование репозитория и настройка окружения

### 3.1. Создание директории и клонирование

```bash
mkdir -p /var/www
chown pricehunter:pricehunter /var/www
```

Теперь переключитесь на пользователя `pricehunter`:

```bash
su - pricehunter
```

Склонируйте репозиторий (замените URL на свой):

```bash
git clone https://github.com/MiksiUGH/Price_Hunter.git /var/www/pricehunter
```

Если репозиторий приватный, используйте SSH-ключи или Personal Access Token.

### 3.2. Виртуальное окружение и зависимости

```bash
cd /var/www/pricehunter
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Убедитесь, что в `requirements.txt` есть все нужные пакеты (Django, selenium, webdriver-manager, fake-useragent, python-decouple, gunicorn).

### 3.3. Настройка переменных окружения

Скопируйте пример файла `.env`:

```bash
cp .env.example .env
nano .env
```

Заполните своими значениями:

```
SECRET_KEY=сгенерируйте_уникальную_строку
DEBUG=False
ALLOWED_HOSTS=82.148.16.130,pricehunter.ru,www.pricehunter.ru
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=PriceHunter <noreply@your-domain.ru>
```

**Как сгенерировать SECRET_KEY:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Для Gmail** обязательно используйте пароль приложения, если включена двухфакторная аутентификация.

### 3.4. Миграции, статика, суперпользователь

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Выйдите из пользователя `pricehunter`:

```bash
exit
```

Теперь вы снова `root`.

## 4. Настройка Gunicorn через Supervisor

Gunicorn будет запускать Django-приложение и слушать Unix-сокет.

### 4.1. Установка Gunicorn в виртуальное окружение (от пользователя)

```bash
su - pricehunter
source /var/www/pricehunter/venv/bin/activate
pip install gunicorn
exit
```

### 4.2. Создание конфигурационного файла supervisor

```bash
nano /etc/supervisor/conf.d/pricehunter.conf
```

Вставьте:

```ini
[program:pricehunter]
command=/var/www/pricehunter/venv/bin/gunicorn --workers 1 --timeout 600 --bind unix:/var/www/pricehunter/pricehunter.sock pricehunter.wsgi:application
directory=/var/www/pricehunter
user=pricehunter
autostart=true
autorestart=true
stderr_logfile=/var/log/pricehunter/err.log
stdout_logfile=/var/log/pricehunter/out.log
environment=HOME="/home/pricehunter",PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",PYTHONPATH="/var/www/pricehunter"
```

**Пояснения:**
- `workers 1` – на сервере с 512 МБ RAM рекомендуется один воркер.
- `timeout 600` – 10 минут на выполнение долгих операций (парсинг).
- `bind unix:` – сокет, через который nginx будет общаться с Gunicorn.

### 4.3. Создание папки для логов

```bash
mkdir -p /var/log/pricehunter
chown pricehunter:pricehunter /var/log/pricehunter
```

### 4.4. Запуск программы через supervisor

```bash
supervisorctl reread
supervisorctl update
supervisorctl start pricehunter
```

Проверьте статус:

```bash
supervisorctl status pricehunter
```

Должно быть `RUNNING`.

## 5. Настройка веб-сервера nginx

Nginx будет принимать HTTP-запросы, отдавать статические файлы и проксировать остальное к Gunicorn.

### 5.1. Создание конфигурации сайта

```bash
nano /etc/nginx/sites-available/pricehunter
```

Вставьте:

```nginx
server {
    listen 80;
    server_name 82.148.16.130 pricehunter.ru www.pricehunter.ru;  # замените на ваш IP/домен

    location /static/ {
        alias /var/www/pricehunter/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/pricehunter/pricehunter.sock;
        proxy_read_timeout 600;
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
    }
}
```

### 5.2. Активация сайта и удаление дефолтного

```bash
ln -s /etc/nginx/sites-available/pricehunter /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## 6. Настройка автоматических задач (cron)

Cron будет запускать команды `update_all_offers`, `update_favorites` и `cleanup_subscriptions` по расписанию.

### 6.1. Редактирование crontab для пользователя pricehunter

```bash
su - pricehunter
crontab -e
```

Добавьте строки:

```cron
0 * * * * cd /var/www/pricehunter && /var/www/pricehunter/venv/bin/python manage.py update_all_offers >> /var/log/pricehunter/update_all.log 2>&1
5 * * * * cd /var/www/pricehunter && /var/www/pricehunter/venv/bin/python manage.py update_favorites >> /var/log/pricehunter/update_fav.log 2>&1
0 3 * * 0 cd /var/www/pricehunter && /var/www/pricehunter/venv/bin/python manage.py cleanup_subscriptions >> /var/log/pricehunter/cleanup.log 2>&1
```

Сохраните и выйдите. Убедитесь, что папка `/var/log/pricehunter` существует и доступна для записи пользователем `pricehunter`.

## 7. Настройка HTTPS (при наличии домена)

После того как DNS-записи вашего домена укажут на IP сервера, установите бесплатный SSL-сертификат Let's Encrypt.

### 7.1. Установка Certbot

```bash
apt install certbot python3-certbot-nginx -y
```

### 7.2. Получение сертификата

```bash
certbot --nginx -d pricehunter.ru -d www.pricehunter.ru
```

Следуйте инструкциям:
- Введите email для уведомлений.
- Согласитесь с условиями.
- Выберите, нужно ли перенаправлять HTTP на HTTPS (рекомендуется **2**).

Certbot автоматически изменит конфигурацию nginx, добавив блок `listen 443 ssl`.

## 8. Проверка работоспособности

- Откройте браузер и перейдите на `http://<IP_сервера>` (или домен). Должна открыться главная страница PriceHunter.
- Проверьте поиск товаров.
- Зарегистрируйтесь, добавьте товар в избранное.
- Вручную выполните `sudo -u pricehunter bash -c 'cd /var/www/pricehunter && /var/www/pricehunter/venv/bin/python manage.py update_favorites'` и проверьте, приходит ли email (если настроен).
- Посмотрите логи cron через несколько часов.

## 9. Устранение типичных проблем

### 9.1. Ошибка 502 Bad Gateway

- Проверьте, запущен ли Gunicorn: `supervisorctl status pricehunter`
- Проверьте логи: `tail -f /var/log/pricehunter/err.log`
- Проверьте, существует ли сокет: `ls -la /var/www/pricehunter/pricehunter.sock`

### 9.2. Selenium не запускается, таймаут

- Увеличьте таймауты в nginx и Gunicorn (уже сделано).
- Добавьте swap (см. п. 1.4).
- Уменьшите число воркеров Gunicorn до 1.
- В `parsers.py` в `get_driver()` добавьте опции:
  ```python
  options.add_argument('--headless=new')
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-dev-shm-usage')
  options.add_argument('--disable-gpu')
  options.add_argument('--memory-pressure-off')
  options.add_argument('--max_old_space_size=256')
  ```

### 9.3. Статика не грузится (нет CSS)

- Проверьте, что `STATIC_ROOT` в `settings.py` совпадает с `alias` в nginx.
- Пересоберите статику: `python manage.py collectstatic --noinput`
- Проверьте права: `chown -R pricehunter:pricehunter /var/www/pricehunter/staticfiles`

### 9.4. Ошибка DisallowedHost

- Добавьте домен или IP в `ALLOWED_HOSTS` в `.env` и перезапустите Gunicorn.

### 9.5. Cron не выполняется

- Проверьте, что пользователь `pricehunter` имеет права на выполнение команд.
- Проверьте, что пути в crontab абсолютные.
- Посмотрите логи cron: `grep CRON /var/log/syslog`

## 10. Заключение

После выполнения всех шагов сайт будет работать в production-режиме. Автоматическое обновление цен и уведомления будут происходить по расписанию. Рекомендуется периодически проверять логи и следить за свободной памятью на сервере.

Для обновления кода на сервере:

```bash
su - pricehunter
cd /var/www/pricehunter
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
exit
supervisorctl restart pricehunter
```

Если возникнут вопросы, обращайтесь к документации проекта или к автору.