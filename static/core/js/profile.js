// profile.js – удаление из избранного, кнопка выхода

document.addEventListener('DOMContentLoaded', () => {
    // Выход
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            window.location.href = '/logout/';  // TODO: реальный URL выхода
        });
    }

    // Удаление из избранного
    async function removeFromFavorites(btn) {
        const productId = btn.getAttribute('data-id');
        if (!productId) return;

        try {
            // TODO: заменить на реальный эндпоинт удаления
            const response = await fetch('/api/favorites/remove/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: productId })
            });
            if (!response.ok) throw new Error('Ошибка сервера');

            // Удаляем карточку из DOM
            const card = btn.closest('.product-card');
            if (card) card.remove();

            // Обновляем счётчик избранного
            const countSpan = document.getElementById('favoritesCount');
            if (countSpan) {
                const remaining = document.querySelectorAll('.favorites-section .product-card').length;
                countSpan.innerText = remaining;
            }

            // Если избранных не осталось – показываем сообщение
            const container = document.getElementById('favoritesContainer');
            if (container && container.querySelectorAll('.product-card').length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">⭐ Нет избранных товаров. Добавьте их на главной странице.</div>';
            }
        } catch (error) {
            console.error(error);
            alert('Не удалось удалить товар из избранного');
        }
    }

    // Навешиваем обработчики на кнопки удаления
    document.querySelectorAll('.remove-fav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            removeFromFavorites(btn);
        });
    });
});