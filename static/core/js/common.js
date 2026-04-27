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
    if (coopBtn) coopBtn.addEventListener('click', () => alert('Сотрудничество: partnership@pricehunter.ru'));
    if (reportBtn) reportBtn.addEventListener('click', () => alert('Сообщить об ошибке: bugs@pricehunter.ru'));
}

// Запуск при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    initBurgerMenu();
    initFooterButtons();
});