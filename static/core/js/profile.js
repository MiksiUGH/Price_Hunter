// profile.js – удаление из избранного, кнопка выхода + модальное окно для ошибок

document.addEventListener('DOMContentLoaded', () => {
    // ---------- Модальное окно ошибки ----------
    function createModal() {
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
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // ---------- Выход ----------
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

    // ---------- Удаление из избранного ----------
    async function removeFromFavorites(btn) {
        const offerId = btn.getAttribute('data-id');
        if (!offerId) return;

        try {
            const response = await fetch(`/hunter/favorites/${offerId}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
            });
            if (response.status === 401) {
                if (typeof showAuthModal === 'function') showAuthModal();
                else alert('Пожалуйста, войдите в аккаунт.');
                return;
            }
            if (!response.ok) throw new Error('Ошибка сервера');

            // Удаляем карточку из исходного списка
            const card = btn.closest('.product-card');
            if (card) {
                const index = window.allCardsData.findIndex(item => item.card === card);
                if (index !== -1) window.allCardsData.splice(index, 1);
                card.remove();
            }

            // Обновляем счётчик
            const countSpan = document.getElementById('favoritesCount');
            if (countSpan) {
                const remaining = document.querySelectorAll('.favorites-section .product-card').length;
                countSpan.innerText = remaining;
            }

            // Если не осталось карточек – показываем сообщение
            const container = document.getElementById('favoritesContainer');
            if (container && container.querySelectorAll('.product-card').length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров.</div>';
                window.allCardsData = [];
            }

            // Переприменяем фильтры (чтобы обновить отображение)
            if (typeof window.filterAndSort === 'function') window.filterAndSort();
        } catch (error) {
            console.error(error);
            showErrorModal('Не удалось удалить товар из избранного. Попробуйте позже.');
        }
    }

    function handleRemoveClick(e) {
        e.preventDefault();
        removeFromFavorites(e.currentTarget);
    }

    function attachRemoveHandlers(container) {
        const btns = container.querySelectorAll('.remove-fav-btn');
        btns.forEach(btn => {
            btn.removeEventListener('click', handleRemoveClick);
            btn.addEventListener('click', handleRemoveClick);
        });
    }

    // ---------- Клиентские фильтры и сортировка ----------
    const favoritesContainer = document.getElementById('favoritesContainer');
    if (favoritesContainer) {
        const priceFrom = document.getElementById('priceFromProfile');
        const priceTo = document.getElementById('priceToProfile');
        const marketCheckboxes = document.querySelectorAll('#marketDropdownProfile input[type="checkbox"]');
        const allCheck = document.getElementById('marketAllProfile');
        const deliveryRadios = document.querySelectorAll('input[name="deliveryRadioProfile"]');
        const sortSelect = document.getElementById('sortPriceProfile');

        // Функция для извлечения данных из карточки (без кэширования)
        function getCardData(card) {
            // Цена (минимальная из диапазона)
            let price = 0;
            const priceElem = card.querySelector('.card-price');
            if (priceElem) {
                const priceText = priceElem.innerText;
                const match = priceText.match(/(\d[\d\s]*?)\s*[–-]/);
                if (match) {
                    price = parseInt(match[1].replace(/\s/g, '')) || 0;
                } else {
                    price = parseInt(priceText.replace(/[^\d]/g, '')) || 0;
                }
            }

            // Магазин – из второго блока .card-meta
            let shop = '';
            const shopBlocks = card.querySelectorAll('.card-meta');
            if (shopBlocks.length >= 2) {
                const shopSpan = shopBlocks[1].querySelector('span');
                if (shopSpan) {
                    shop = shopSpan.innerText.replace(/[🏷️]/g, '').trim();
                }
            }

            // Доставка – из первого блока .card-meta, второй span
            let deliveryDays = 9999;
            if (shopBlocks.length >= 1) {
                const deliverySpans = shopBlocks[0].querySelectorAll('span');
                if (deliverySpans.length >= 2) {
                    const deliveryText = deliverySpans[1].innerText;
                    if (deliveryText.includes('Завтра')) deliveryDays = 1;
                    else if (deliveryText.includes('Послезавтра')) deliveryDays = 2;
                    else {
                        const match = deliveryText.match(/(\d+)\s*дн/);
                        if (match) deliveryDays = parseInt(match[1]);
                    }
                }
            }

            return { card, price, shop, deliveryDays };
        }

        // Сохраняем исходный список карточек (будет обновляться при удалении)
        function refreshAllCardsData() {
            const cards = Array.from(favoritesContainer.querySelectorAll('.product-card'));
            window.allCardsData = cards.map(card => getCardData(card));
        }

        // Инициализируем исходные данные
        refreshAllCardsData();

        // Фильтрация и сортировка (перерисовка из исходного списка)
        window.filterAndSort = function() {
            let minPrice = priceFrom ? parseInt(priceFrom.value) || 0 : 0;
            let maxPrice = priceTo ? parseInt(priceTo.value) || Infinity : Infinity;
            if (priceTo && priceTo.value === '') maxPrice = Infinity;

            let selectedShops = [];
            marketCheckboxes.forEach(cb => {
                if (cb.checked && cb.value !== 'all') selectedShops.push(cb.value);
            });
            const isAllShops = (allCheck && allCheck.checked) || selectedShops.length === 0;

            let maxDelivery = 9999;
            deliveryRadios.forEach(r => {
                if (r.checked) maxDelivery = parseInt(r.value);
            });

            const sortType = sortSelect ? sortSelect.value : 'none';

            let filtered = window.allCardsData.filter(data => {
                if (data.price < minPrice || data.price > maxPrice) return false;
                if (!isAllShops && !selectedShops.includes(data.shop)) return false;
                if (data.deliveryDays > maxDelivery) return false;
                return true;
            });

            if (sortType === 'asc') filtered.sort((a, b) => a.price - b.price);
            else if (sortType === 'desc') filtered.sort((a, b) => b.price - a.price);

            favoritesContainer.innerHTML = '';
            if (filtered.length === 0) {
                favoritesContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров, соответствующих фильтрам.</div>';
            } else {
                filtered.forEach(data => favoritesContainer.appendChild(data.card));
            }

            attachRemoveHandlers(favoritesContainer);
        };

        // Навешиваем обработчики на элементы фильтров
        if (priceFrom) priceFrom.addEventListener('input', window.filterAndSort);
        if (priceTo) priceTo.addEventListener('input', window.filterAndSort);
        marketCheckboxes.forEach(cb => cb.addEventListener('change', window.filterAndSort));
        deliveryRadios.forEach(r => r.addEventListener('change', window.filterAndSort));
        if (sortSelect) sortSelect.addEventListener('change', window.filterAndSort);

        // Инициализация дропдаунов (бургеров)
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

        attachRemoveHandlers(favoritesContainer);
        window.filterAndSort(); // применяем начальные фильтры (ничего не фильтруют)
    }

    // ---------- Удаление аккаунта с модальным подтверждением ----------
    function createDeleteConfirmModal() {
        if (document.getElementById('deleteConfirmModal')) return;

        const modalHTML = `
            <div id="deleteConfirmModal" class="modal-overlay" style="display: none;">
                <div class="modal-content delete-modal">
                    <div class="modal-icon">⚠️</div>
                    <h3>Удаление аккаунта</h3>
                    <p>Вы действительно хотите удалить свой аккаунт?<br>Это действие <strong>необратимо</strong> – все ваши данные будут потеряны.</p>
                    <div class="modal-buttons">
                        <button id="confirmDeleteBtn" class="save-btn danger-btn">Да, удалить</button>
                        <button id="cancelDeleteBtn" class="cancel-btn">Отмена</button>
                    </div>
                </div>
            </div>
            <style>
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.7);
                    backdrop-filter: blur(5px);
                    z-index: 10001;
                    justify-content: center;
                    align-items: center;
                }
                .modal-content {
                    background: var(--card-bg);
                    border-radius: 32px;
                    padding: 2rem;
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                    border: 1px solid var(--danger);
                    animation: modalPop 0.3s ease;
                }
                .delete-modal .modal-icon {
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }
                .modal-buttons {
                    display: flex;
                    gap: 1rem;
                    justify-content: center;
                    margin-top: 1.5rem;
                }
                .danger-btn { background: var(--danger); border: none; color: white; padding: 0.6rem 1.2rem; border-radius: 60px; cursor: pointer; }
                .cancel-btn { background: rgba(255,255,255,0.2); border: 1px solid var(--text-muted); color: var(--text-white); padding: 0.6rem 1.2rem; border-radius: 60px; cursor: pointer; }
                @keyframes modalPop { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
            </style>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const modal = document.getElementById('deleteConfirmModal');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        const cancelBtn = document.getElementById('cancelDeleteBtn');

        function closeModal() { modal.style.display = 'none'; }

        confirmBtn.addEventListener('click', async () => {
            closeModal();
            const deleteBtn = document.getElementById('deleteAccountBtn');
            const originalText = deleteBtn.innerHTML;
            deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Удаление...';
            deleteBtn.disabled = true;

            try {
                const response = await fetch('/hunter/delete_user/', {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'success') window.location.href = '/hunter/';
                    else alert('Ошибка при удалении аккаунта');
                } else if (response.status === 401) alert('Вы не авторизованы');
                else alert('Ошибка сервера. Попробуйте позже.');
            } catch (error) {
                console.error(error);
                alert('Не удалось выполнить запрос');
            } finally {
                deleteBtn.innerHTML = originalText;
                deleteBtn.disabled = false;
            }
        });

        cancelBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    }

    const deleteAccountBtn = document.getElementById('deleteAccountBtn');
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', () => {
            createDeleteConfirmModal();
            const modal = document.getElementById('deleteConfirmModal');
            if (modal) modal.style.display = 'flex';
        });
    }
});