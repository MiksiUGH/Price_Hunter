// main.js – логика главной страницы (только поиск продуктов и переключение режимов)

document.addEventListener('DOMContentLoaded', () => {
    const nameSection = document.getElementById('searchByNameSection');
    const urlSection = document.getElementById('searchByUrlSection');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const searchInput = document.getElementById('productNameSearch');
    const searchBtn = document.getElementById('executeNameSearch');
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    const urlField = document.getElementById('urlField');
    const urlResultArea = document.getElementById('urlResultArea');
    const productsContainer = document.getElementById('productsContainer');

    async function performSearch() {
        if (!productsContainer) return;
        const query = searchInput?.value.trim();
        if (!query) {
            productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;">Введите название товара.</div>';
            return;
        }

        productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem;"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';

        const params = new URLSearchParams();
        params.append('query', query);
        params.append('limit', 20);

        try {
            const response = await fetch(`/hunter/query_search?${params.toString()}`);
            if (!response.ok) throw new Error();
            const html = await response.text();
            productsContainer.innerHTML = html;
        } catch (error) {
            productsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem; color:#ffaa66;">⚠️ Ошибка при загрузке товаров. Попробуйте позже.</div>';
            console.error(error);
        }
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            performSearch();
        });
    }
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    // Переключение режимов
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (mode === 'name') {
                nameSection?.classList.add('active-section');
                urlSection?.classList.remove('active-section');
            } else {
                nameSection?.classList.remove('active-section');
                urlSection?.classList.add('active-section');
            }
        });
    });

    // Поиск по URL
    if (fetchUrlBtn && urlField && urlResultArea) {
        fetchUrlBtn.addEventListener('click', async () => {
            const urlValue = urlField.value.trim();
            if (!urlValue) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Введите URL товара</div>';
                return;
            }
            urlResultArea.innerHTML = '<div style="text-align:center;"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
            try {
                const params = new URLSearchParams();
                params.append('url', urlValue);
                const response = await fetch(`/hunter/url_search?${params.toString()}`);
                if (!response.ok) throw new Error();
                const html = await response.text();
                urlResultArea.innerHTML = html;
                if (typeof bindFavoriteButtons === 'function') bindFavoriteButtons(urlResultArea);
            } catch (error) {
                urlResultArea.innerHTML = '<div style="color:#ffaa66;">⚠️ Не удалось загрузить товар. Проверьте URL.</div>';
                console.error(error);
            }
        });
    }
});