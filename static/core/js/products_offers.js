// product_offers.js – только фильтры (избранное уже в common.js)

document.addEventListener('DOMContentLoaded', () => {
    // ----- Фильтры -----
    const applyFilters = () => {
        const params = new URLSearchParams();
        const priceFrom = document.getElementById('priceFrom')?.value;
        const priceTo = document.getElementById('priceTo')?.value;
        if (priceFrom) params.set('price_min', priceFrom);
        if (priceTo) params.set('price_max', priceTo);

        const selectedMarkets = [];
        document.querySelectorAll('#marketMultiSelect .multi-dropdown input[type="checkbox"]').forEach(cb => {
            if (cb.checked && cb.value !== 'all') selectedMarkets.push(cb.value);
        });
        if (selectedMarkets.length) params.set('marketplaces', selectedMarkets.join(','));

        let deliveryDays = 9999;
        document.querySelectorAll('input[name="deliveryRadio"]').forEach(r => {
            if (r.checked) deliveryDays = r.value;
        });
        if (deliveryDays != 9999) params.set('delivery_days', deliveryDays);

        const sortPrice = document.getElementById('sortPrice')?.value;
        if (sortPrice && sortPrice !== 'none') params.set('sort_price', sortPrice);

        window.location.search = params.toString();
    };

    document.querySelectorAll('.multi-dropdown input, .delivery-dropdown input, #sortPrice, .price-range input').forEach(el => {
        el.addEventListener('change', applyFilters);
    });

    // ----- Инициализация кнопок избранного в контейнере офферов -----
    const offersContainer = document.getElementById('offersContainer');
    if (offersContainer && typeof bindFavoriteButtons === 'function') {
        bindFavoriteButtons(offersContainer);
    }
});