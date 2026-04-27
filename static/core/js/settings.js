// settings.js – загрузка и сохранение настроек через API сервера

document.addEventListener('DOMContentLoaded', () => {
    const themeSelect = document.getElementById('themeSelect');
    const languageSelect = document.getElementById('languageSelect');
    const currencySelect = document.getElementById('currencySelect');
    const checkInterval = document.getElementById('checkInterval');
    const activateEmail = document.getElementById('activateEmail');
    const saveBtn = document.getElementById('saveSettingsBtn');

    // Функция загрузки настроек с сервера
    async function loadSettings() {
        try {
            const response = await fetch('/api/settings/');
            if (!response.ok) throw new Error();
            const settings = await response.json();
            if (themeSelect) themeSelect.value = settings.theme || 'dark';
            if (languageSelect) languageSelect.value = settings.language || 'ru';
            if (currencySelect) currencySelect.value = settings.currency || 'RUB';
            if (checkInterval) checkInterval.value = settings.check_interval || '24';
            if (activateEmail) activateEmail.value = settings.email_notifications ? 'true' : 'false';
        } catch (error) {
            console.warn('Не удалось загрузить настройки, используются значения по умолчанию');
            // Устанавливаем дефолтные значения
            if (themeSelect) themeSelect.value = 'dark';
            if (languageSelect) languageSelect.value = 'ru';
            if (currencySelect) currencySelect.value = 'RUB';
            if (checkInterval) checkInterval.value = '24';
            if (activateEmail) activateEmail.value = 'false';
        }
    }

    // Функция сохранения настроек
    async function saveSettings() {
        const payload = {
            theme: themeSelect?.value || 'dark',
            language: languageSelect?.value || 'ru',
            currency: currencySelect?.value || 'RUB',
            check_interval: checkInterval?.value || '24',
            email_notifications: activateEmail?.value === 'true'
        };
        try {
            const response = await fetch('/api/settings/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (response.ok) {
                // Можно показать ненавязчивое уведомление, но без alert
                console.log('Настройки сохранены');
                // Например, изменить стиль кнопки на мгновение
                if (saveBtn) {
                    saveBtn.style.background = '#00c853';
                    setTimeout(() => { saveBtn.style.background = ''; }, 500);
                }
            } else {
                throw new Error();
            }
        } catch (error) {
            console.error('Ошибка сохранения настроек');
            if (saveBtn) {
                saveBtn.style.background = '#ff5e7e';
                setTimeout(() => { saveBtn.style.background = ''; }, 500);
            }
        }
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettings);
    }

    loadSettings();
});