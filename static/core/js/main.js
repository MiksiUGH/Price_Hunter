// main.js – логика главной страницы (поиск с фильтрами и переключение режимов)

document.addEventListener('DOMContentLoaded', () => {
    const nameSection = document.getElementById('searchByNameSection');
    const urlSection = document.getElementById('searchByUrlSection');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const searchInput = document.getElementById('productNameSearch');
    const searchBtn = document.getElementById('executeNameSearch');
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    const urlField = document.getElementById('urlField');
    const urlResultArea = document.getElementById('urlResultArea');
    const productsContainer = document.getElementById('productsContainer');

    // ---------- Фильтры ----------
    const priceFrom = document.getElementById('priceFrom');
    const priceTo = document.getElementById('priceTo');
    const deliveryRadios = document.querySelectorAll('input[name="deliveryRadio"]');
    const marketCheckboxes = document.querySelectorAll('#marketMultiSelect .multi-dropdown input[type="checkbox"]');
    const allCheck = document.getElementById('marketAll');

    // Функция для получения выбранных маркетплейсов
    function getSelectedMarkets() {
        const selected = [];
        marketCheckboxes.forEach(cb => {
            if (cb.checked && cb.value !== 'all') selected.push(cb.value);
        });
        return selected;
    }

    // Функция для получения выбранного срока доставки
    function getSelectedDeliveryDays() {
        let days = 9999;
        deliveryRadios.forEach(r => {
            if (r.checked) days = parseInt(r.value);
        });
        return days;
    }

    // Поиск с отправкой фильтров на сервер
    async function performSearch() {
        if (!productsContainer) return;
        const query = searchInput?.value.trim();
        if (!query) {
            productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">Введите название товара.</div>';
            return;
        }

        productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';

        const params = new URLSearchParams();
        params.append('query', query);
        params.append('limit', 20);

        // Добавляем фильтры
        const minPrice = priceFrom?.value ? parseInt(priceFrom.value) : 0;
        const maxPrice = priceTo?.value ? parseInt(priceTo.value) : 999999;
        if (minPrice > 0) params.append('price_min', minPrice);
        if (maxPrice < 999999) params.append('price_max', maxPrice);

        const deliveryDays = getSelectedDeliveryDays();
        if (deliveryDays < 9999) params.append('delivery_days', deliveryDays);

        const markets = getSelectedMarkets();
        if (markets.length > 0 && !(allCheck && allCheck.checked)) {
            markets.forEach(m => params.append('marketplaces', m));
        }

        try {
            const response = await fetch(`/hunter/query_search?${params.toString()}`);
            if (!response.ok) throw new Error();
            const html = await response.text();
            productsContainer.innerHTML = html;
            const currentParams = window.location.search;
            document.querySelectorAll('.view-offers-btn').forEach(link => {
                const separator = link.href.includes('?') ? '&' : '?';
                link.href = link.href + separator + currentParams.slice(1);
            });
        } catch (error) {
            productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem; color:#ffaa66;">⚠️ Ошибка при загрузке товаров. Попробуйте позже.</div>';
            console.error(error);
        }
    }

    // Привязываем обработчики к фильтрам (изменение любого фильтра вызывает поиск)
    if (priceFrom) priceFrom.addEventListener('input', performSearch);
    if (priceTo) priceTo.addEventListener('input', performSearch);
    deliveryRadios.forEach(r => r.addEventListener('change', performSearch));
    marketCheckboxes.forEach(cb => cb.addEventListener('change', () => {
        if (allCheck && allCheck.checked && cb.value !== 'all') {
            allCheck.checked = false;
        }
        performSearch();
    }));
    if (allCheck) {
        allCheck.addEventListener('change', (e) => {
            marketCheckboxes.forEach(cb => {
                if (cb !== allCheck) cb.checked = e.target.checked;
            });
            performSearch();
        });
    }

    // Кнопка "Искать" тоже вызывает поиск (на случай, если фильтры не вызывали)
    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch();
        });
    }
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    // Обновление текста выбранной доставки в дропдауне
    function updateDeliveryLabel() {
        const label = document.getElementById('deliverySelectedLabel');
        if (!label) return;
        for (let r of deliveryRadios) {
            if (r.checked) {
                label.innerText = r.parentElement.innerText.trim();
                break;
            }
        }
    }
    deliveryRadios.forEach(r => r.addEventListener('change', updateDeliveryLabel));
    updateDeliveryLabel();

    // Переключение режимов (поиск по названию / по URL)
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
                const params = new URLSearchParams();
                params.append('url', urlValue);
                const response = await fetch(`/hunter/url_search?${params.toString()}`);
                if (!response.ok) throw new Error();
                const html = await response.text();
                urlResultArea.innerHTML = html;
                if (typeof bindFavoriteButtons === 'function') bindFavoriteButtons(urlResultArea);
            } catch (error) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Не удалось загрузить товар. Проверьте URL.</div>';
                console.error(error);
            }
        });
    }
});