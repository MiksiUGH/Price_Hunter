// main.js – логика главной страницы

document.addEventListener('DOMContentLoaded', () => {
    // DOM-элементы
    const nameSection = document.getElementById('searchByNameSection');
    const urlSection = document.getElementById('searchByUrlSection');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const searchInput = document.getElementById('productNameSearch');
    const searchBtn = document.getElementById('executeNameSearch');
    const limitInput = document.getElementById('limitCount');
    const priceFrom = document.getElementById('priceFrom');
    const priceTo = document.getElementById('priceTo');
    const sortPrice = document.getElementById('sortPrice');
    const sortMarket = document.getElementById('sortMarket');
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    const urlField = document.getElementById('urlField');
    const urlResultArea = document.getElementById('urlResultArea');
    const productsContainer = document.getElementById('productsContainer');

    // Фильтры
    const marketContainer = document.getElementById('marketMultiSelect');
    const marketTrigger = marketContainer?.querySelector('.multi-select-trigger');
    const marketCheckboxes = marketContainer?.querySelectorAll('.multi-dropdown input[type="checkbox"]') || [];
    const allCheck = document.getElementById('marketAll');
    const deliveryRadios = document.querySelectorAll('input[name="deliveryRadio"]');
    const deliverySelectedSpan = document.getElementById('deliverySelectedLabel');

    // Инициализация дропдаунов
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
    setupDropdown(marketContainer, marketTrigger);
    setupDropdown(document.getElementById('deliverySelect'), document.querySelector('.delivery-trigger'));

    // Обработка "Все" для маркетплейсов
    if (allCheck) {
        allCheck.addEventListener('change', () => {
            const isAll = allCheck.checked;
            marketCheckboxes.forEach(cb => { if (cb !== allCheck) cb.checked = isAll; });
        });
        marketCheckboxes.forEach(cb => {
            if (cb !== allCheck) cb.addEventListener('change', () => { if (allCheck.checked) allCheck.checked = false; });
        });
    }

    // Обновление текста выбранной доставки
    function updateDeliveryLabel() {
        for (let r of deliveryRadios) {
            if (r.checked) {
                if (deliverySelectedSpan) deliverySelectedSpan.innerText = r.parentElement.innerText.trim();
                break;
            }
        }
    }
    deliveryRadios.forEach(r => r.addEventListener('change', updateDeliveryLabel));
    updateDeliveryLabel();

    // Клиентская сортировка
    function sortExistingCards() {
        if (!productsContainer) return;
        const cards = Array.from(productsContainer.querySelectorAll('.product-card'));
        if (cards.length === 0) return;
        const priceSort = sortPrice?.value || 'none';
        const marketFilter = sortMarket?.value || 'any';

        let filteredCards = marketFilter !== 'any' ? cards.filter(card => {
            const marketplaceElem = card.querySelector('.card-meta:last-child span:last-child');
            return marketplaceElem?.innerText.trim() === marketFilter;
        }) : [...cards];

        if (priceSort !== 'none') {
            filteredCards.sort((a, b) => {
                const priceA = parseInt(a.querySelector('.card-price')?.innerText.replace(/[^\d]/g, '') || 0);
                const priceB = parseInt(b.querySelector('.card-price')?.innerText.replace(/[^\d]/g, '') || 0);
                return priceSort === 'asc' ? priceA - priceB : priceB - priceA;
            });
        }
        productsContainer.innerHTML = '';
        filteredCards.forEach(card => productsContainer.appendChild(card));
    }

    if (sortPrice) sortPrice.addEventListener('change', sortExistingCards);
    if (sortMarket) sortMarket.addEventListener('change', sortExistingCards);

    // Привязка кнопок "В избранное"
    function bindFavoriteButtons() {
        document.querySelectorAll('.fav-btn:not(.bound)').forEach(btn => {
            btn.classList.add('bound');
            btn.onclick = async (e) => {
                e.preventDefault();
                const productId = btn.dataset.id || btn.closest('.product-card')?.dataset.id;
                if (!productId) return;
                // TODO: заменить эндпоинт на реальный
                try {
                    await fetch('/api/favorites/add/', {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: productId })
                    });
                } catch (err) { console.error(err); }
            };
        });
    }

    // Поиск товаров
    async function performSearch() {
        if (!productsContainer) return;
        productsContainer.innerHTML = '<div style="text-align:center; padding:2rem;"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';

        const params = new URLSearchParams();
        params.append('query', searchInput?.value.trim() || '');
        params.append('limit', limitInput?.value || 12);
        params.append('price_min', priceFrom?.value || 0);
        params.append('price_max', priceTo?.value || 999999);

        // Маркетплейсы
        const selectedMarkets = [];
        marketCheckboxes.forEach(cb => {
            if (cb.checked && cb.value !== 'all') selectedMarkets.push(cb.value);
        });
        if (selectedMarkets.length === 0 || (allCheck && allCheck.checked)) {
            params.append('marketplaces', 'all');
        } else {
            selectedMarkets.forEach(m => params.append('marketplaces', m));
        }

        // Срок доставки
        let deliveryDays = 9999;
        for (let r of deliveryRadios) {
            if (r.checked) { deliveryDays = parseInt(r.value); break; }
        }
        params.append('delivery_days', deliveryDays);

        try {
            // TODO: заменить эндпоинт на реальный /api/search/
            const response = await fetch(`/api/search/?${params.toString()}`);
            if (!response.ok) throw new Error();
            const html = await response.text();
            productsContainer.innerHTML = html;
            sortExistingCards();
            bindFavoriteButtons();
        } catch (error) {
            productsContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:#ffaa66;">⚠️ Ошибка при загрузке товаров. Попробуйте позже.</div>';
            console.error(error);
        }
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch();
        });
    }

    // Переключение режимов
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (mode === 'name') {
                nameSection?.classList.add('active-section');
                urlSection?.classList.remove('active-section');
            } else {
                nameSection?.classList.remove('active-section');
                urlSection?.classList.add('active-section');
            }
        });
    });

    // Поиск по URL
    if (fetchUrlBtn && urlField && urlResultArea) {
        fetchUrlBtn.addEventListener('click', async () => {
            const urlValue = urlField.value.trim();
            if (!urlValue) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Введите URL товара</div>';
                return;
            }
            urlResultArea.innerHTML = '<div style="text-align:center;"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
            try {
                // TODO: заменить эндпоинт на реальный /api/parse-url/
                const response = await fetch('/api/parse-url/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlValue })
                });
                if (!response.ok) throw new Error();
                const html = await response.text();
                urlResultArea.innerHTML = html;
                bindFavoriteButtons(); // если в большой карточке есть кнопка "В избранное"
            } catch (error) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Не удалось загрузить товар. Проверьте URL.</div>';
                console.error(error);
            }
        });
    }

    bindFavoriteButtons();
});