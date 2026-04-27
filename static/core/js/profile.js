// profile.js – только кнопка выхода (избранное будет через Django без JS)

document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            window.location.href = '/logout/';
        });
    }
});