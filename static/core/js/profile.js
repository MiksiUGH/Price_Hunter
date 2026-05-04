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

    // Удаление из избранного (с удалением карточки)
    async function removeFromFavorites(btn) {
        const offerId = btn.getAttribute('data-id');
        if (!offerId) return;

        try {
            const response = await fetch(`/hunter/favorites/${offerId}/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
            });
            if (response.status === 401) {
                // Показываем красивое модальное окно для авторизации (из common.js)
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
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров. Добавьте их на главной странице.</div>';
            }
        } catch (error) {
            console.error(error);
            showErrorModal('Не удалось удалить товар из избранного. Попробуйте позже.');
        }
    }

    // Навешиваем обработчики на кнопки .remove-fav-btn в профиле
    document.querySelectorAll('.remove-fav-btn').forEach(btn => {
        btn.removeEventListener('click', profileRemoveHandler);
        function profileRemoveHandler(e) {
            e.preventDefault();
            removeFromFavorites(btn);
        }
        btn.addEventListener('click', profileRemoveHandler);
        btn._profileRemoveHandler = profileRemoveHandler;
    });

    // ----- Клиентские фильтры и сортировка для избранных товаров -----
    function initProfileFilters() {
        const container = document.getElementById('favoritesContainer');
        if (!container) return;

        // Сохраняем исходные карточки
        let allCards = Array.from(container.querySelectorAll('.product-card'));
        if (allCards.length === 0) return;

        // Извлекаем данные из каждой карточки
        let cardsData = allCards.map(card => {
            // Цена
            const priceElem = card.querySelector('.card-price');
            let price = 0;
            if (priceElem) {
                const priceText = priceElem.innerText.replace(/[^\d]/g, '');
                price = parseInt(priceText) || 0;
            }
            // Магазин
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

        // Элементы фильтров
        const priceFrom = document.getElementById('priceFromProfile');
        const priceTo = document.getElementById('priceToProfile');
        const marketCheckboxes = document.querySelectorAll('#marketDropdownProfile input[type="checkbox"]');
        const allCheck = document.getElementById('marketAllProfile');
        const deliveryRadios = document.querySelectorAll('input[name="deliveryRadioProfile"]');
        const sortSelect = document.getElementById('sortPriceProfile');

        function filterAndSort() {
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

            let filtered = cardsData.filter(data => {
                if (data.price < minPrice || data.price > maxPrice) return false;
                if (!isAllShops && !selectedShops.includes(data.shop)) return false;
                if (data.deliveryDays > maxDelivery) return false;
                return true;
            });

            if (sortType === 'asc') filtered.sort((a, b) => a.price - b.price);
            else if (sortType === 'desc') filtered.sort((a, b) => b.price - a.price);
            // none – сохраняем исходный порядок

            // Перерисовка
            container.innerHTML = '';
            if (filtered.length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров, соответствующих фильтрам.</div>';
            } else {
                filtered.forEach(data => container.appendChild(data.card));
            }

            // Заново привязать обработчики удаления (если используем profile.js)
            document.querySelectorAll('.remove-fav-btn').forEach(btn => {
                btn.removeEventListener('click', profileRemoveHandler);
                function profileRemoveHandler(e) {
                    e.preventDefault();
                    removeFromFavorites(btn);
                }
                btn.addEventListener('click', profileRemoveHandler);
                btn._profileRemoveHandler = profileRemoveHandler;
            });
        }

        // Навешиваем события
        if (priceFrom) priceFrom.addEventListener('input', filterAndSort);
        if (priceTo) priceTo.addEventListener('input', filterAndSort);
        marketCheckboxes.forEach(cb => cb.addEventListener('change', filterAndSort));
        deliveryRadios.forEach(r => r.addEventListener('change', filterAndSort));
        if (sortSelect) sortSelect.addEventListener('change', filterAndSort);

        // Инициализация дропдауна для маркетплейсов (как на главной)
        const marketContainer = document.getElementById('marketMultiSelectProfile');
        const marketTrigger = marketContainer?.querySelector('.multi-select-trigger');
        if (marketContainer && marketTrigger) {
            marketTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                document.querySelectorAll('.filter-card.open').forEach(card => {
                    if (card !== marketContainer) card.classList.remove('open');
                });
                marketContainer.classList.toggle('open');
            });
            document.addEventListener('click', (e) => {
                if (!marketContainer.contains(e.target)) marketContainer.classList.remove('open');
            });
        }

        const deliveryContainer = document.getElementById('deliverySelectProfile');
        const deliveryTrigger = deliveryContainer?.querySelector('.delivery-trigger');
        if (deliveryContainer && deliveryTrigger) {
            deliveryTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                document.querySelectorAll('.filter-card.open').forEach(card => {
                    if (card !== deliveryContainer) card.classList.remove('open');
                });
                deliveryContainer.classList.toggle('open');
            });
            document.addEventListener('click', (e) => {
                if (!deliveryContainer.contains(e.target)) deliveryContainer.classList.remove('open');
            });
        }

        // Обновление текста выбранной доставки
        function updateDeliveryLabel() {
            const selectedSpan = document.getElementById('deliverySelectedLabelProfile');
            for (let r of deliveryRadios) {
                if (r.checked) {
                    selectedSpan.innerText = r.parentElement.innerText.trim();
                    break;
                }
            }
        }
        deliveryRadios.forEach(r => r.addEventListener('change', updateDeliveryLabel));
        updateDeliveryLabel();

        filterAndSort(); // применить начальные фильтры (сортировка по умолчанию)
    }

    // Запускаем после загрузки DOM
    if (document.getElementById('favoritesContainer')) {
        initProfileFilters();
    }
});