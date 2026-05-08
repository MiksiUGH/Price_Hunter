// product_offers.js – клиентские фильтры и сортировка (с сохранением исходных карточек)

document.addEventListener('DOMContentLoaded', () => {
    const offersContainer = document.getElementById('offersContainer');
    if (!offersContainer) {
        console.warn('offersContainer не найден');
        return;
    }

    // Сохраняем исходные карточки и их данные
    let allCards = Array.from(offersContainer.querySelectorAll('.product-card'));
    if (allCards.length === 0) {
        console.warn('Нет карточек в offersContainer');
        return;
    }

    // Функция для извлечения данных из карточки
    function getCardData(card) {
        // Цена
        const priceElem = card.querySelector('.card-price');
        let price = 0;
        if (priceElem) {
            const priceText = priceElem.innerText.replace(/[^\d]/g, '');
            price = parseInt(priceText) || 0;
        }

        // Магазин – из второго блока .card-meta, последний span
        let shop = '';
        const shopBlocks = card.querySelectorAll('.card-meta');
        if (shopBlocks.length >= 2) {
            const shopSpan = shopBlocks[1].querySelector('span:last-child');
            if (shopSpan) {
                shop = shopSpan.innerText.replace(/[🏷️]/g, '').trim();
            }
        }

        // Доставка – из первого блока .card-meta, последний span
        let deliveryDays = 9999;
        if (shopBlocks.length >= 1) {
            const deliverySpans = shopBlocks[0].querySelectorAll('span');
            if (deliverySpans.length >= 2) {
                const deliveryText = deliverySpans[deliverySpans.length - 1].innerText;
                if (deliveryText.includes('Завтра')) {
                    deliveryDays = 1;
                } else if (deliveryText.includes('Послезавтра')) {
                    deliveryDays = 2;
                } else {
                    const match = deliveryText.match(/(\d+)\s*дн/);
                    if (match) deliveryDays = parseInt(match[1]);
                }
            }
        }

        return { card, price, shop, deliveryDays };
    }

    let cardsData = allCards.map(card => getCardData(card));

    // Элементы фильтров
    const priceFromInput = document.getElementById('priceFrom');
    const priceToInput = document.getElementById('priceTo');
    const marketCheckboxes = document.querySelectorAll('#marketMultiSelect .multi-dropdown input[type="checkbox"]');
    const allCheck = document.getElementById('marketAll');
    const deliveryRadios = document.querySelectorAll('input[name="deliveryRadio"]');
    const sortSelect = document.getElementById('sortPrice');

    // Элементы для отображения выбранных значений
    const marketTriggerText = document.querySelector('#marketMultiSelect .multi-select-trigger span');
    const deliverySelectedSpan = document.getElementById('deliverySelectedLabel');

    // Функция обновления текста для маркетплейсов
    function updateMarketLabel() {
        if (!marketTriggerText) return;
        const selected = Array.from(marketCheckboxes)
            .filter(cb => cb.checked && cb.value !== 'all')
            .map(cb => cb.value);
        if (selected.length === 0 || (allCheck && allCheck.checked)) {
            marketTriggerText.innerText = 'Все';
        } else if (selected.length === 1) {
            marketTriggerText.innerText = selected[0];
        } else {
            marketTriggerText.innerText = `Выбрано (${selected.length})`;
        }
    }

    // Функция обновления текста для доставки
    function updateDeliveryLabel() {
        if (!deliverySelectedSpan) return;
        for (let r of deliveryRadios) {
            if (r.checked) {
                deliverySelectedSpan.innerText = r.parentElement.innerText.trim();
                break;
            }
        }
    }

    function filterAndSort() {
        let priceMin = priceFromInput ? parseInt(priceFromInput.value) || 0 : 0;
        let priceMax = priceToInput ? parseInt(priceToInput.value) || Infinity : Infinity;
        if (priceToInput && priceToInput.value === '') priceMax = Infinity;

        let selectedShops = [];
        marketCheckboxes.forEach(cb => {
            if (cb.checked && cb.value !== 'all') {
                selectedShops.push(cb.value);
            }
        });
        const isAllShops = (allCheck && allCheck.checked) || selectedShops.length === 0;

        let maxDeliveryDays = 9999;
        deliveryRadios.forEach(r => {
            if (r.checked) maxDeliveryDays = parseInt(r.value);
        });

        const sortType = sortSelect ? sortSelect.value : 'none';

        // Отладка: выводим отфильтрованные данные
        let filtered = cardsData.filter(data => {
            const priceOk = (data.price >= priceMin && data.price <= priceMax);
            const shopOk = isAllShops || selectedShops.includes(data.shop);
            const deliveryOk = (data.deliveryDays <= maxDeliveryDays);
            if (!shopOk) console.log('shop mismatch:', data.shop, 'not in', selectedShops);
            if (!deliveryOk) console.log('delivery mismatch:', data.deliveryDays, '>', maxDeliveryDays);
            return priceOk && shopOk && deliveryOk;
        });

        if (sortType === 'asc') filtered.sort((a, b) => a.price - b.price);
        else if (sortType === 'desc') filtered.sort((a, b) => b.price - a.price);

        offersContainer.innerHTML = '';
        if (filtered.length === 0) {
            offersContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">😞 Нет предложений, соответствующих фильтрам.</div>';
            return;
        }
        filtered.forEach(data => offersContainer.appendChild(data.card));

        if (typeof bindFavoriteButtons === 'function') {
            bindFavoriteButtons(offersContainer);
        }
    }

    // Навешиваем обработчики на все элементы фильтров
    if (priceFromInput) priceFromInput.addEventListener('input', filterAndSort);
    if (priceToInput) priceToInput.addEventListener('input', filterAndSort);
    marketCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            updateMarketLabel();
            filterAndSort();
        });
    });
    if (allCheck) {
        allCheck.addEventListener('change', () => {
            // Если отмечен "Все", снимаем все остальные
            if (allCheck.checked) {
                marketCheckboxes.forEach(cb => { if (cb !== allCheck) cb.checked = false; });
            }
            updateMarketLabel();
            filterAndSort();
        });
    }
    deliveryRadios.forEach(r => {
        r.addEventListener('change', () => {
            updateDeliveryLabel();
            filterAndSort();
        });
    });
    if (sortSelect) sortSelect.addEventListener('change', filterAndSort);

    // Инициализация дропдаунов (открытие/закрытие)
    function setupDropdown(container, trigger) {
        if (!container || !trigger) return;
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.filter-card.open').forEach(card => {
                if (card !== container) card.classList.remove('open');
            });
            container.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) container.classList.remove('open');
        });
    }

    const marketContainer = document.getElementById('marketMultiSelect');
    const marketTrigger = marketContainer?.querySelector('.multi-select-trigger');
    setupDropdown(marketContainer, marketTrigger);

    const deliveryContainer = document.getElementById('deliverySelect');
    const deliveryTrigger = deliveryContainer?.querySelector('.delivery-trigger');
    setupDropdown(deliveryContainer, deliveryTrigger);

    // Синхронизируем чекбокс "Все" с остальными при загрузке
    if (allCheck) {
        const anyChecked = Array.from(marketCheckboxes).some(cb => cb.checked && cb !== allCheck);
        if (!anyChecked) allCheck.checked = true;
    }

    // Обновляем метки и применяем фильтры
    updateMarketLabel();
    updateDeliveryLabel();
    filterAndSort();

    if (typeof bindFavoriteButtons === 'function') {
        bindFavoriteButtons(offersContainer);
    }
});