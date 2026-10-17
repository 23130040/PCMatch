// Django renders product details. JavaScript only opens the corresponding HTML drawer.
(() => {
    document.querySelectorAll('[data-admin-product-filter]').forEach(select => {
        select.addEventListener('change', () => document.getElementById('admin-product-filters')?.requestSubmit());
    });
    const backdrop = document.querySelector('.product-drawer-backdrop');
    let activeDrawer = null;
    const close = () => {
        if (!activeDrawer) return;
        activeDrawer.classList.remove('is-open');
        activeDrawer.hidden = true;
        activeDrawer.setAttribute('aria-hidden', 'true');
        backdrop.classList.remove('is-open');
        backdrop.hidden = true;
        document.body.classList.remove('has-product-drawer');
        activeDrawer = null;
    };
    const open = row => {
        close();
        const drawer = document.getElementById('product-drawer-' + row.dataset.productId);
        if (!drawer) return;
        activeDrawer = drawer;
        drawer.hidden = false;
        drawer.setAttribute('aria-hidden', 'false');
        backdrop.hidden = false;
        document.body.classList.add('has-product-drawer');
        requestAnimationFrame(() => {drawer.classList.add('is-open'); backdrop.classList.add('is-open');});
    };
    document.querySelectorAll('.product-table tbody tr[data-product-id]').forEach(row => {
        row.classList.add('product-row-clickable');
        row.addEventListener('click', event => {if (!event.target.closest('input, button, a, select')) open(row);});
        row.querySelector('.product-detail')?.addEventListener('click', () => open(row));
    });
    document.querySelectorAll('[data-product-drawer-close]').forEach(button => button.addEventListener('click', close));
    backdrop?.addEventListener('click', close);
    document.addEventListener('keydown', event => {if (event.key === 'Escape') close();});
})();
