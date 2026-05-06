// common.js – общие функции для всех страниц PriceHunter

// Бургер-меню
function initBurgerMenu() {
    const burger = document.getElementById('burgerBtn');
    const sideMenu = document.getElementById('sideMenu');
    const closeMenu = document.getElementById('closeMenuBtn');
    if (burger && sideMenu && closeMenu) {
        burger.addEventListener('click', () => sideMenu.classList.toggle('open'));
        closeMenu.addEventListener('click', () => sideMenu.classList.remove('open'));
        document.addEventListener('click', (e) => {
            if (!sideMenu.contains(e.target) && !burger.contains(e.target) && sideMenu.classList.contains('open')) {
                sideMenu.classList.remove('open');
            }
        });
    }
}

// Кнопки футера
function initFooterButtons() {
    const coopBtn = document.getElementById('coopBtn');
    const reportBtn = document.getElementById('reportBugBtn');
    if (coopBtn) coopBtn.addEventListener('click', () => {
        window.location.href = 'mailto:supporthunter67@gmail.com?subject=Сотрудничество';
    });
    if (reportBtn) reportBtn.addEventListener('click', () => {
        window.location.href = 'mailto:supporthunter67@gmail.com?subject=Сообщение об ошибке';
    });
}

// Запуск при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    initBurgerMenu();
    initFooterButtons();
    bindFavoriteButtons();
    loadAndApplyTheme();
});

// ----- Модальное окно для 401 (неавторизован) -----
function createAuthModal() {
    if (document.getElementById('authModal')) return;
    const modalHTML = `
        <div id="authModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 10001; justify-content: center; align-items: center;">
            <div style="background: linear-gradient(135deg, #1e2a3a, #0f1722); max-width: 380px; width: 90%; border-radius: 28px; box-shadow: 0 25px 40px rgba(0,0,0,0.4); padding: 28px 24px 24px; text-align: center; border: 1px solid rgba(0,255,136,0.2); animation: modalFadeIn 0.2s ease;">
                <div style="font-size: 56px; margin-bottom: 12px;">🔐</div>
                <h3 style="margin: 0 0 8px; font-size: 24px; font-weight: 700; color: #ffaa66;">Требуется авторизация</h3>
                <p style="margin: 12px 0 24px; color: #b0c4de; font-size: 15px;">Войдите в аккаунт, чтобы добавлять товары в избранное.</p>
                <a href="/hunter/login/" id="authModalLoginBtn" style="background: #00c853; border: none; color: white; font-weight: 600; padding: 10px 28px; border-radius: 40px; cursor: pointer; font-size: 15px; text-decoration: none; display: inline-block;">Войти</a>
                <button id="closeAuthModalBtn" style="background: transparent; border: none; color: #8aa0b5; margin-top: 16px; display: block; width: 100%; cursor: pointer;">Закрыть</button>
            </div>
        </div>
        <style>
            @keyframes modalFadeIn {
                from { opacity: 0; transform: scale(0.96); }
                to { opacity: 1; transform: scale(1); }
            }
        </style>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('authModal');
    const closeBtn = document.getElementById('closeAuthModalBtn');
    const loginLink = document.getElementById('authModalLoginBtn');
    function closeModal() { modal.style.display = 'none'; }
    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
}

function showAuthModal() {
    createAuthModal();
    const modal = document.getElementById('authModal');
    if (modal) modal.style.display = 'flex';
}

// ----- Работа с избранным (общие функции) -----
async function addToFavorites(offerId, btn) {
    try {
        const response = await fetch(`/hunter/favorites/${offerId}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
        });
        if (response.status === 401) {
            showAuthModal();
            return;
        }
        if (!response.ok) throw new Error();
        // Меняем кнопку
        btn.classList.remove('fav-btn');
        btn.classList.add('remove-fav-btn');
        btn.innerHTML = '<i class="fas fa-trash-alt"></i> Удалить';
        btn.setAttribute('data-action', 'remove');
    } catch (error) {
        console.error(error);
        alert('Не удалось добавить в избранное. Попробуйте позже.');
    }
}

async function removeFromFavorites(offerId, btn) {
    try {
        const response = await fetch(`/hunter/favorites/${offerId}/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
        });
        if (response.status === 401) {
            showAuthModal();
            return;
        }
        if (!response.ok) throw new Error();
        btn.classList.remove('remove-fav-btn');
        btn.classList.add('fav-btn');
        btn.innerHTML = '<i class="far fa-heart"></i> Изб.';
        btn.setAttribute('data-action', 'add');
    } catch (error) {
        console.error(error);
        alert('Не удалось удалить из избранного. Попробуйте позже.');
    }
}

function handleFavoriteClick(e) {
    const btn = e.currentTarget;
    const offerId = btn.getAttribute('data-id');
    if (!offerId) return;
    const isRemove = btn.classList.contains('remove-fav-btn');
    if (isRemove) {
        removeFromFavorites(offerId, btn);
    } else {
        addToFavorites(offerId, btn);
    }
}

function bindFavoriteButtons(container = document) {
    const btns = container.querySelectorAll('.fav-btn, .remove-fav-btn');
    btns.forEach(btn => {
        if (btn.getAttribute('data-fav-bound')) return;
        btn.setAttribute('data-fav-bound', 'true');
        btn.addEventListener('click', handleFavoriteClick);
    });
}

// ----- Управление темой (светлая/тёмная) -----
function applyTheme(theme) {
    if (theme === 'light') {
        document.documentElement.classList.add('light-theme');
    } else {
        document.documentElement.classList.remove('light-theme');
    }
}

async function loadAndApplyTheme() {
    try {
        const response = await fetch('/hunter/settings/?format=json');
        if (response.ok) {
            const settings = await response.json();
            const theme = settings.theme || 'dark';
            applyTheme(theme);
        } else {
            applyTheme('dark');
        }
    } catch (error) {
        console.warn('Не удалось загрузить тему, используется тёмная');
        applyTheme('dark');
    }
}