// product_offers.js – клиентские фильтры и сортировка (без перезагрузки)

document.addEventListener('DOMContentLoaded', () => {
    const offersContainer = document.getElementById('offersContainer');
    if (!offersContainer) return;

    // Сохраняем исходные карточки (HTML-элементы)
    let allCards = Array.from(offersContainer.querySelectorAll('.product-card'));
    // Если карточек нет, то и фильтровать нечего
    if (allCards.length === 0) return;

    // Функция для извлечения данных из карточки
    function getCardData(card) {
        // цена (число)
        const priceElem = card.querySelector('.card-price');
        let price = 0;
        if (priceElem) {
            const priceText = priceElem.innerText.replace(/[^\d]/g, '');
            price = parseInt(priceText) || 0;
        }
        // магазин (например, "🏷️ Ozon")
        const shopElem = card.querySelector('.card-meta:last-child span:last-child');
        let shop = '';
        if (shopElem) {
            shop = shopElem.innerText.trim();
        }
        // доставка в днях (из текста "Завтра" → 1, "Послезавтра" → 2, "3 дн." → 3)
        const deliveryElem = card.querySelector('.card-meta:first-child span:last-child');
        let deliveryDays = 9999;
        if (deliveryElem) {
            const text = deliveryElem.innerText;
            if (text.includes('Завтра')) deliveryDays = 1;
            else if (text.includes('Послезавтра')) deliveryDays = 2;
            else {
                const match = text.match(/(\d+)\s*дн/);
                if (match) deliveryDays = parseInt(match[1]);
            }
        }
        // наличие (true/false)
        const stockElem = card.querySelector('.card-meta:first-child span:first-child');
        const inStock = stockElem ? stockElem.innerText.includes('В наличии') : false;

        return { card, price, shop, deliveryDays, inStock };
    }

    let cardsData = allCards.map(card => getCardData(card));

    // DOM-элементы фильтров
    const priceFromInput = document.getElementById('priceFrom');
    const priceToInput = document.getElementById('priceTo');
    const marketCheckboxes = document.querySelectorAll('#marketMultiSelect .multi-dropdown input[type="checkbox"]');
    const deliveryRadios = document.querySelectorAll('input[name="deliveryRadio"]');
    const sortSelect = document.getElementById('sortPrice');

    // Функция применения фильтров и сортировки
    function filterAndSort() {
        // Получаем значения фильтров
        let priceMin = priceFromInput ? parseInt(priceFromInput.value) || 0 : 0;
        let priceMax = priceToInput ? parseInt(priceToInput.value) || Infinity : Infinity;
        // Если поле "До" пустое – не ограничиваем
        if (priceToInput && priceToInput.value === '') priceMax = Infinity;

        // Выбранные маркетплейсы
        let selectedShops = [];
        marketCheckboxes.forEach(cb => {
            if (cb.checked && cb.value !== 'all') {
                selectedShops.push(cb.value);
            }
        });
        // Если чекбокс "Все" отмечен или ничего не выбрано – показываем все магазины
        const allCheck = document.getElementById('marketAll');
        const isAllShops = (allCheck && allCheck.checked) || selectedShops.length === 0;

        // Срок доставки
        let maxDeliveryDays = 9999;
        deliveryRadios.forEach(r => {
            if (r.checked) {
                maxDeliveryDays = parseInt(r.value);
            }
        });

        // Сортировка
        const sortType = sortSelect ? sortSelect.value : 'none';

        // Фильтрация
        let filtered = cardsData.filter(data => {
            if (data.price < priceMin || data.price > priceMax) return false;
            if (!isAllShops && !selectedShops.includes(data.shop)) return false;
            if (data.deliveryDays > maxDeliveryDays) return false;
            return true;
        });

        // Сортировка
        if (sortType === 'asc') {
            filtered.sort((a, b) => a.price - b.price);
        } else if (sortType === 'desc') {
            filtered.sort((a, b) => b.price - a.price);
        } else {
            // none – возвращаем в исходном порядке (сохраняем порядок, как на сервере)
            // можно не сортировать
        }

        // Перерисовка контейнера
        offersContainer.innerHTML = '';
        if (filtered.length === 0) {
            offersContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">😞 Нет предложений, соответствующих фильтрам.</div>';
            return;
        }
        filtered.forEach(data => {
            offersContainer.appendChild(data.card);
        });

        // После перерисовки нужно заново привязать кнопки избранного (т.к. карточки переместились)
        if (typeof bindFavoriteButtons === 'function') {
            bindFavoriteButtons(offersContainer);
        }
    }

    // Навешиваем обработчики на все элементы фильтров
    if (priceFromInput) priceFromInput.addEventListener('input', filterAndSort);
    if (priceToInput) priceToInput.addEventListener('input', filterAndSort);
    marketCheckboxes.forEach(cb => cb.addEventListener('change', filterAndSort));
    deliveryRadios.forEach(r => r.addEventListener('change', filterAndSort));
    if (sortSelect) sortSelect.addEventListener('change', filterAndSort);

    // Запускаем начальную фильтрацию (чтобы применить сортировку по умолчанию, если нужно)
    filterAndSort();

    // Инициализация кнопок избранного (для карточек, которые уже есть в контейнере)
    if (typeof bindFavoriteButtons === 'function') {
        bindFavoriteButtons(offersContainer);
    }
});