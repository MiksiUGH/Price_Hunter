// main.js – логика главной страницы:
// - отправка поискового запроса + первых 4 фильтров на сервер
// - полученные карточки сохраняются и сортируются клиентскими фильтрами (цена, маркетплейс)

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

    // Элементы фильтров (первые 4 блока)
    const marketContainer = document.getElementById('marketMultiSelect');
    const marketTrigger = marketContainer?.querySelector('.multi-select-trigger');
    const marketCheckboxes = marketContainer?.querySelectorAll('.multi-dropdown input[type="checkbox"]') || [];
    const allCheck = document.getElementById('marketAll');
    const deliveryRadios = document.querySelectorAll('input[name="deliveryRadio"]');
    const deliverySelectedSpan = document.getElementById('deliverySelectedLabel');

    // ========== Инициализация дропдаунов ==========
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

    // Обработчик "Все" для маркетплейсов
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

    // ========== Переменные для хранения текущих товаров и сортировки ==========
    let currentProductsHtml = '';       // HTML карточек, полученных от сервера
    let currentProductsData = [];       // массив объектов товаров (если сервер отдаёт JSON, иначе парсим HTML)
    // Если сервер возвращает готовый HTML, для сортировки нужно извлечь данные (цена, маркетплейс)
    // Ниже предполагаем, что сервер возвращает HTML карточек, и для сортировки мы будем переставлять блоки.
    // Альтернатива: сервер возвращает JSON, тогда сохраняем массив и рендерим сами.
    // Для простоты оставим работу с HTML: при сортировке будем извлекать блоки и переставлять.

    // Функция перестановки карточек в соответствии с выбранной сортировкой
    function sortExistingCards() {
        if (!productsContainer) return;
        const cards = Array.from(productsContainer.querySelectorAll('.product-card'));
        if (cards.length === 0) return;
        const priceSort = sortPrice?.value || 'none';
        const marketFilter = sortMarket?.value || 'any';

        // Сначала фильтруем по маркетплейсу (если выбран конкретный)
        let filteredCards = cards;
        if (marketFilter !== 'any') {
            filteredCards = cards.filter(card => {
                const marketplaceElem = card.querySelector('.card-meta:last-child span:last-child');
                const marketplace = marketplaceElem?.innerText.trim() || '';
                return marketplace === marketFilter;
            });
        } else {
            filteredCards = [...cards];
        }

        // Сортируем по цене
        if (priceSort !== 'none') {
            filteredCards.sort((a, b) => {
                const priceA = parseInt(a.querySelector('.card-price')?.innerText.replace(/[^\d]/g, '') || 0);
                const priceB = parseInt(b.querySelector('.card-price')?.innerText.replace(/[^\d]/g, '') || 0);
                return priceSort === 'asc' ? priceA - priceB : priceB - priceA;
            });
        }

        // Переставляем элементы в контейнере
        productsContainer.innerHTML = '';
        filteredCards.forEach(card => productsContainer.appendChild(card));
    }

    // Навешиваем обработчики на сортировку
    if (sortPrice) sortPrice.addEventListener('change', sortExistingCards);
    if (sortMarket) sortMarket.addEventListener('change', sortExistingCards);

    // ========== Функция отправки поискового запроса (первые 4 фильтра + поиск) ==========
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
            // Замените URL на реальный эндпоинт Django
            const response = await fetch(`/api/search/?${params.toString()}`);
            if (!response.ok) throw new Error();
            const html = await response.text();
            productsContainer.innerHTML = html;
            // После загрузки новых карточек применяем текущую сортировку (если она активна)
            sortExistingCards();
        } catch (error) {
            productsContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:#ffaa66;">⚠️ Ошибка при загрузке товаров. Попробуйте позже.</div>';
            console.error(error);
        }
    }

    // Кнопка "Искать"
    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch();
        });
    }

    // Переключение между режимами "По названию" и "По URL"
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (mode === 'name') {
                if (nameSection) nameSection.classList.add('active-section');
                if (urlSection) urlSection.classList.remove('active-section');
                // Если нужно загрузить товары при переключении – можно вызвать performSearch()
            } else {
                if (nameSection) nameSection.classList.remove('active-section');
                if (urlSection) urlSection.classList.add('active-section');
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
                // Замените на реальный эндпоинт
                const response = await fetch('/api/parse-url/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlValue })
                });
                if (!response.ok) throw new Error();
                const html = await response.text();
                urlResultArea.innerHTML = html;
            } catch (error) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Не удалось загрузить товар. Проверьте URL.</div>';
                console.error(error);
            }
        });
    }

    // При загрузке страницы можно выполнить поиск с параметрами по умолчанию
    // (если нужно показать какие-то товары сразу)
    // performSearch(); – раскомментируйте при необходимости
});