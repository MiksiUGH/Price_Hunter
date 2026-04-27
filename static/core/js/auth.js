// auth.js – переключение табов на странице входа/регистрации

document.addEventListener('DOMContentLoaded', () => {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const loginPane = document.getElementById('loginPane');
    const registerPane = document.getElementById('registerPane');
    const switchToLogin = document.getElementById('switchToLogin');

    function switchTab(tabId) {
        if(tabId === 'login') {
            loginPane.classList.add('active-pane');
            registerPane.classList.remove('active-pane');
            tabBtns[0].classList.add('active');
            tabBtns[1].classList.remove('active');
        } else {
            loginPane.classList.remove('active-pane');
            registerPane.classList.add('active-pane');
            tabBtns[0].classList.remove('active');
            tabBtns[1].classList.add('active');
        }
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            switchTab(tab);
        });
    });

    if (switchToLogin) {
        switchToLogin.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab('login');
        });
    }
});