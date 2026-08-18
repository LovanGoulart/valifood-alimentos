const searchInput = document.getElementById('search-input');
if (searchInput) {
    let timeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const q = e.target.value.trim();
            if (q.length > 0) window.location.href = '/products?q=' + encodeURIComponent(q);
            else window.location.href = '/products';
        }, 800);
    });
}
