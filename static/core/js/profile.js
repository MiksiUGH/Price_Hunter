// profile.js – удаление из избранного, кнопка выхода + модальное окно для ошибок

document.addEventListener('DOMContentLoaded', () => {
    // ---------- Создаём красивое модальное окно (один раз) ----------
    function createModal() {
        // Проверяем, нет ли уже модалки на странице
        if (document.getElementById('customErrorModal')) return;

        const modalHTML = `
            <div id="customErrorModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(3px); z-index: 10000; justify-content: center; align-items: center; transition: all 0.3s;">
                <div style="background: white; max-width: 400px; width: 90%; border-radius: 24px; box-shadow: 0 20px 35px -10px rgba(0,0,0,0.3); padding: 24px 20px 20px; text-align: center; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; animation: modalFadeIn 0.2s ease-out;">
                    <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
                    <h3 style="margin: 0 0 8px; font-size: 24px; font-weight: 600; color: #dc2626;">Ошибка</h3>
                    <p id="errorModalMessage" style="margin: 12px 0 24px; color: #4b5563; font-size: 16px; line-height: 1.4;">Неизвестная ошибка</p>
                    <button id="closeErrorModalBtn" style="background: #3b82f6; border: none; color: white; font-weight: 600; padding: 10px 24px; border-radius: 40px; cursor: pointer; font-size: 15px; transition: 0.2s; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">Закрыть</button>
                </div>
            </div>
            <style>
                @keyframes modalFadeIn {
                    from { opacity: 0; transform: scale(0.95); }
                    to { opacity: 1; transform: scale(1); }
                }
                #customErrorModal.show {
                    display: flex !important;
                }
            </style>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const modal = document.getElementById('customErrorModal');
        const closeBtn = document.getElementById('closeErrorModalBtn');

        function closeModal() {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 200);
        }

        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    function showErrorModal(message) {
        createModal();
        const modal = document.getElementById('customErrorModal');
        const msgSpan = document.getElementById('errorModalMessage');
        if (msgSpan) msgSpan.innerText = message;
        modal.style.display = 'flex';
        // небольшая задержка для анимации
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // ---------- Основная логика ----------
    // Выход
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            const response = await fetch('/hunter/logout/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken }
            });
            if (response.ok) window.location.href = '/hunter/';
        });
    }

    // Единая функция удаления (используется и при загрузке, и после фильтрации)
    async function removeFromFavorites(btn) {
        const offerId = btn.getAttribute('data-id');
        if (!offerId) return;

        try {
            const response = await fetch(`/hunter/favorites/${offerId}/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
            });
            if (response.status === 401) {
                if (typeof showAuthModal === 'function') showAuthModal();
                else alert('Пожалуйста, войдите в аккаунт.');
                return;
            }
            if (!response.ok) throw new Error('Ошибка сервера');

            const card = btn.closest('.product-card');
            if (card) card.remove();

            const countSpan = document.getElementById('favoritesCount');
            if (countSpan) {
                const remaining = document.querySelectorAll('.favorites-section .product-card').length;
                countSpan.innerText = remaining;
            }

            const container = document.getElementById('favoritesContainer');
            if (container && container.querySelectorAll('.product-card').length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров.</div>';
            }

            // После удаления карточки обновляем фильтры (чтобы они работали по новому списку)
            if (typeof filterAndSort === 'function') filterAndSort();
        } catch (error) {
            console.error(error);
            showErrorModal('Не удалось удалить товар из избранного. Попробуйте позже.');
        }
    }

    // Обработчик клика для кнопок удаления
    function handleRemoveClick(e) {
        e.preventDefault();
        removeFromFavorites(e.currentTarget);
    }

    // Привязывает обработчики ко всем .remove-fav-btn внутри контейнера
    function attachRemoveHandlers(container) {
        const btns = container.querySelectorAll('.remove-fav-btn');
        btns.forEach(btn => {
            // Удаляем старый обработчик, если есть
            btn.removeEventListener('click', handleRemoveClick);
            btn.addEventListener('click', handleRemoveClick);
        });
    }

    // ---------- Клиентские фильтры и сортировка (без кеширования) ----------
    const favoritesContainer = document.getElementById('favoritesContainer');
    if (favoritesContainer) {
        // Элементы фильтров
        const priceFrom = document.getElementById('priceFromProfile');
        const priceTo = document.getElementById('priceToProfile');
        const marketCheckboxes = document.querySelectorAll('#marketDropdownProfile input[type="checkbox"]');
        const allCheck = document.getElementById('marketAllProfile');
        const deliveryRadios = document.querySelectorAll('input[name="deliveryRadioProfile"]');
        const sortSelect = document.getElementById('sortPriceProfile');

        // Функция сбора данных из текущих карточек (всегда актуальна)
        function getCurrentCardsData() {
            const cards = Array.from(favoritesContainer.querySelectorAll('.product-card'));
            return cards.map(card => {
                // Цена
                const priceElem = card.querySelector('.card-price');
                let price = 0;
                if (priceElem) {
                    const priceText = priceElem.innerText.replace(/[^\d]/g, '');
                    price = parseInt(priceText) || 0;
                }
                // Магазин (последний span в .card-meta:last-child)
                const shopElem = card.querySelector('.card-meta:last-child span:last-child');
                let shop = shopElem ? shopElem.innerText.trim() : '';
                // Доставка
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
                return { card, price, shop, deliveryDays };
            });
        }

        // Фильтрация и сортировка (перерисовка)
        window.filterAndSort = function() { // делаем глобальной, чтобы можно было вызвать из removeFromFavorites
            let minPrice = priceFrom ? parseInt(priceFrom.value) || 0 : 0;
            let maxPrice = priceTo ? parseInt(priceTo.value) || Infinity : Infinity;
            if (priceTo && priceTo.value === '') maxPrice = Infinity;

            // Выбранные магазины
            let selectedShops = [];
            marketCheckboxes.forEach(cb => {
                if (cb.checked && cb.value !== 'all') selectedShops.push(cb.value);
            });
            const isAllShops = (allCheck && allCheck.checked) || selectedShops.length === 0;

            // Доставка
            let maxDelivery = 9999;
            deliveryRadios.forEach(r => {
                if (r.checked) maxDelivery = parseInt(r.value);
            });

            // Сортировка
            const sortType = sortSelect ? sortSelect.value : 'none';

            // Получаем актуальные данные (без кеша)
            let cardsData = getCurrentCardsData();

            let filtered = cardsData.filter(data => {
                if (data.price < minPrice || data.price > maxPrice) return false;
                if (!isAllShops && !selectedShops.includes(data.shop)) return false;
                if (data.deliveryDays > maxDelivery) return false;
                return true;
            });

            if (sortType === 'asc') filtered.sort((a, b) => a.price - b.price);
            else if (sortType === 'desc') filtered.sort((a, b) => b.price - a.price);
            // none – сохраняем порядок, в котором они шли в cardsData (исходный порядок в DOM)

            // Перерисовка
            favoritesContainer.innerHTML = '';
            if (filtered.length === 0) {
                favoritesContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров, соответствующих фильтрам.</div>';
            } else {
                filtered.forEach(data => favoritesContainer.appendChild(data.card));
            }

            // Заново привязываем обработчики удаления (после перерисовки)
            attachRemoveHandlers(favoritesContainer);
        };

        // Навешиваем обработчики событий на фильтры
        if (priceFrom) priceFrom.addEventListener('input', window.filterAndSort);
        if (priceTo) priceTo.addEventListener('input', window.filterAndSort);
        marketCheckboxes.forEach(cb => cb.addEventListener('change', window.filterAndSort));
        deliveryRadios.forEach(r => r.addEventListener('change', window.filterAndSort));
        if (sortSelect) sortSelect.addEventListener('change', window.filterAndSort);

        // Инициализация дропдаунов (как на главной)
        function setupProfileDropdown(containerId, triggerSelector) {
            const container = document.getElementById(containerId);
            const trigger = container?.querySelector(triggerSelector);
            if (container && trigger) {
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
        }
        setupProfileDropdown('marketMultiSelectProfile', '.multi-select-trigger');
        setupProfileDropdown('deliverySelectProfile', '.delivery-trigger');

        // Обновление текста выбранной доставки
        function updateDeliveryLabel() {
            const selectedSpan = document.getElementById('deliverySelectedLabelProfile');
            if (!selectedSpan) return;
            for (let r of deliveryRadios) {
                if (r.checked) {
                    selectedSpan.innerText = r.parentElement.innerText.trim();
                    break;
                }
            }
        }
        deliveryRadios.forEach(r => r.addEventListener('change', updateDeliveryLabel));
        updateDeliveryLabel();

        // Первоначальная привязка обработчиков удаления к уже существующим карточкам
        attachRemoveHandlers(favoritesContainer);

        // Выполняем фильтрацию (приведёт к сортировке по умолчанию, если нужно)
        window.filterAndSort();
    }
});