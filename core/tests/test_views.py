import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Product, Shop, Offer, Subscription, UserSetting


# ------------------------- Фикстуры -------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def auth_client(client, user):
    """Авторизованный клиент (force_login)"""
    client.force_login(user)
    return client

@pytest.fixture
def shop(db):
    return Shop.objects.create(
        name='Wildberries',
        slug='wb',
        search_url_template='https://www.wildberries.ru/catalog/0/search.aspx?search={query}',
        is_active=True
    )

@pytest.fixture
def product(db):
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        normalized_name='test product'
    )

@pytest.fixture
def offer(db, product, shop):
    return Offer.objects.create(
        product=product,
        shop=shop,
        url='https://example.com/test',
        article='12345',
        price=1000.00,
        in_stock=True,
        delivery_days=3,
        is_active=True
    )

@pytest.fixture
def subscription(db, user, offer):
    return Subscription.objects.create(
        user=user,
        offer=offer,
        last_notified_price=None,
        notify_on_drop=False,
        notify_on_restore=False,
        is_active=True
    )


# ------------------------- Главная -------------------------
def test_index_view(client):
    url = reverse('hunter')
    response = client.get(url)
    assert response.status_code == 200


# ------------------------- Аутентификация -------------------------
def test_login_page(client):
    url = reverse('login')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_login_post_success(client, user):
    url = reverse('login')
    response = client.post(url, {
        'username': 'testuser',
        'password': 'testpass123'
    })
    assert response.status_code == 302
    assert response.url == reverse('profile')

@pytest.mark.django_db
def test_login_post_invalid(client):
    url = reverse('login')
    response = client.post(url, {'username': 'wrong', 'password': 'wrong'})
    assert response.status_code == 200
    assert 'name="password"' in response.content.decode()

def test_register_page(client):
    url = reverse('register')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_register_post_success(client):
    url = reverse('register')
    response = client.post(url, {
        'username': 'newuser',
        'email': 'new@example.com',
        'password1': 'StrongPwd123',
        'password2': 'StrongPwd123'
    })
    assert response.status_code == 302
    assert response.url == reverse('profile')
    assert User.objects.filter(username='newuser').exists()

def test_logout(auth_client):
    url = reverse('logout')
    response = auth_client.post(url)
    assert response.status_code == 302
    assert response.url == reverse('hunter')


# ------------------------- Профиль -------------------------
def test_profile_view_unauthorized(client):
    url = reverse('profile')
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse('login'))

def test_profile_view_authorized(auth_client, subscription):
    url = reverse('profile')
    response = auth_client.get(url)
    # Если падает с 500 – проверьте логи сервера, это ошибка вьюхи
    assert response.status_code == 200
    assert 'Избранные товары' in response.content.decode()
    assert 'Test Product' in response.content.decode()


# ------------------------- Редактирование профиля -------------------------
def test_edit_profile_unauthorized(client):
    url = reverse('edit_profile')
    response = client.get(url)
    assert response.status_code == 302

def test_edit_profile_get(auth_client):
    url = reverse('edit_profile')
    response = auth_client.get(url)
    assert response.status_code == 200
    assert 'Редактирование профиля' in response.content.decode()

def test_edit_profile_post(auth_client, user):
    url = reverse('edit_profile')
    response = auth_client.post(url, {
        'username': 'newname',
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'email': 'ivan@example.com'
    })
    assert response.status_code == 302
    assert response.url == reverse('profile')
    user.refresh_from_db()
    assert user.username == 'newname'
    assert user.first_name == 'Иван'


# ------------------------- Настройки -------------------------
def test_settings_view_html(auth_client):
    url = reverse('settings')
    response = auth_client.get(url)
    assert response.status_code == 200
    assert 'Настройки' in response.content.decode()

def test_settings_view_json(auth_client):
    url = reverse('settings') + '?format=json'
    response = auth_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert 'theme' in data

def test_settings_put(auth_client, user):
    url = reverse('settings')
    payload = {
        'theme': 'light',
        'currency': 'USD',
        'check_interval': 48,
        'email_notifications': True
    }
    response = auth_client.put(
        url,
        data=json.dumps(payload),
        content_type='application/json',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 200
    settings = UserSetting.objects.get(user=user)
    assert settings.theme == 'light'
    assert settings.currency == 'USD'
    assert settings.check_interval == 48
    assert settings.email_notifications is True


# ------------------------- Смена пароля -------------------------
def test_change_password_page(auth_client):
    url = reverse('edit_password')
    response = auth_client.get(url)
    assert response.status_code == 200
    assert 'Смена пароля' in response.content.decode()

def test_change_password_post_valid(auth_client, user):
    url = reverse('edit_password')
    response = auth_client.post(url, {
        'old_password': 'testpass123',
        'new_password1': 'NewPass456',
        'new_password2': 'NewPass456'
    })
    assert response.status_code == 302
    assert response.url == reverse('profile')
    user.refresh_from_db()
    assert user.check_password('NewPass456')


# ------------------------- Поиск по URL -------------------------
def test_url_search_no_url(client):
    url = reverse('url_search')
    response = client.get(url)
    assert response.status_code == 200

def test_url_search_invalid_url(client):
    url = reverse('url_search')
    response = client.get(url, {'url': 'invalid'})
    assert response.status_code == 200  # или 400, но не падает


# ------------------------- Поиск по названию -------------------------
def test_query_search_no_query(client):
    url = reverse('query_search')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.skip(reason="Требует реального парсера или заглушки")
def test_query_search_with_query(client, product, offer):
    url = reverse('query_search')
    response = client.get(url, {'query': 'test'})
    # Если падает 500 – проверьте логи
    assert response.status_code == 200


# ------------------------- Предложения продукта -------------------------
def test_product_offers_view(client, product, offer):
    url = reverse('product_offers', args=[product.slug])
    response = client.get(url)
    assert response.status_code == 200
    assert product.name in response.content.decode()
    assert '1000' in response.content.decode()

@pytest.mark.django_db
def test_product_offers_not_found(client):
    url = reverse('product_offers', args=['nonexistent'])
    response = client.get(url)
    assert response.status_code == 404


# ------------------------- Избранное -------------------------
def test_favorites_post_unauthorized(client, offer):
    url = reverse('favorites', args=[offer.id])
    response = client.post(url)
    assert response.status_code == 401

def test_favorites_post_authorized(auth_client, user, offer):
    url = reverse('favorites', args=[offer.id])
    response = auth_client.post(url)
    assert response.status_code == 200
    sub = Subscription.objects.filter(user=user, offer=offer).first()
    assert sub is not None
    assert sub.is_active is True

def test_favorites_delete(auth_client, user, subscription):
    url = reverse('favorites', args=[subscription.offer.id])
    response = auth_client.delete(url)
    assert response.status_code == 200
    subscription.refresh_from_db()
    assert subscription.is_active is False


# ------------------------- Удаление аккаунта -------------------------
def test_delete_user_unauthorized(client):
    url = reverse('delete_user')
    response = client.delete(url)
    assert response.status_code == 401

def test_delete_user_success(auth_client, user):
    user_pk = user.pk
    url = reverse('delete_user')
    response = auth_client.delete(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert not User.objects.filter(pk=user_pk).exists()


# ------------------------- Инструкция -------------------------
def test_instruction_view(client):
    url = reverse('instruction')
    response = client.get(url)
    assert response.status_code == 200
    assert 'Инструкция' in response.content.decode()
