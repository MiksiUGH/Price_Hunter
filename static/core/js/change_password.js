// change_password.js – AJAX отправка формы смены пароля

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('changePasswordForm');
    const submitBtn = document.getElementById('submitBtn');
    const successModal = document.getElementById('successModal');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        document.querySelectorAll('.error-text').forEach(el => el.innerText = '');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';

        const formData = new FormData(form);
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    successModal.style.display = 'flex';
                    setTimeout(() => {
                        window.location.href = '/hunter/profile/';
                    }, 3000);
                } else {
                    if (data.errors) {
                        displayErrors(data.errors);
                    }
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-save"></i> Сменить пароль';
                }
            } else if (response.status === 400) {
                const data = await response.json();
                if (data.errors) displayErrors(data.errors);
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-save"></i> Сменить пароль';
            } else {
                throw new Error();
            }
        } catch (error) {
            console.error(error);
            alert('Ошибка соединения. Попробуйте позже.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Сменить пароль';
        }
    });

    function displayErrors(errors) {
        for (const [field, messages] of Object.entries(errors)) {
            const errorDiv = document.getElementById(`error-${field}`);
            if (errorDiv) {
                errorDiv.innerText = messages.join(', ');
            }
        }
    }
});