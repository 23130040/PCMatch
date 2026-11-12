// Presentation widgets clone their markup from HTML; no business operation is simulated.
document.querySelectorAll('[data-time-filter]').forEach(button => {
    const template = document.querySelector('#ui-time-popover');
    if (!template) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'time-filter';
    button.before(wrapper);
    wrapper.append(button, template.content.cloneNode(true));
    button.classList.add('time-filter-trigger');
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', () => button.setAttribute('aria-expanded', String(wrapper.classList.toggle('is-open'))));
    wrapper.querySelectorAll('[data-ui-period]').forEach(option => option.addEventListener('click', () => {
        wrapper.querySelectorAll('[data-ui-period]').forEach(node => node.classList.toggle('is-active', node === option));
    }));
    wrapper.querySelectorAll('[data-ui-time-mode]').forEach(option => option.addEventListener('click', () => {
        wrapper.querySelectorAll('[data-ui-time-mode]').forEach(node => node.classList.toggle('is-active', node === option));
        wrapper.querySelector('[data-ui-date]').type = option.dataset.uiTimeMode;
    }));
    document.addEventListener('click', event => {
        if (!wrapper.contains(event.target)) {wrapper.classList.remove('is-open'); button.setAttribute('aria-expanded', 'false');}
    });
});
document.querySelectorAll('table[data-selectable-table]').forEach(table => {
    const template = document.querySelector('#ui-bulk-toolbar');
    const master = table.querySelector('thead input[type=checkbox]');
    const boxes = [...table.querySelectorAll('tbody input[type=checkbox]')];
    if (!template || !master || !boxes.length) return;
    const toolbar = template.content.firstElementChild.cloneNode(true);
    const scrollWrapper = table.closest('.table-scroll, .table-wrap');
    if (scrollWrapper) scrollWrapper.before(toolbar); else table.before(toolbar);
    function refresh() {
        const checked = boxes.filter(box => box.checked);
        toolbar.hidden = checked.length === 0;
        toolbar.querySelector('[data-ui-selected-count]').textContent = checked.length;
        master.checked = checked.length === boxes.length;
        master.indeterminate = checked.length > 0 && checked.length < boxes.length;
        boxes.forEach(box => box.closest('tr').classList.toggle('is-row-selected', box.checked));
    }
    master.addEventListener('change', () => {boxes.forEach(box => box.checked = master.checked); refresh();});
    boxes.forEach(box => box.addEventListener('change', refresh));
    toolbar.querySelector('[data-ui-clear-selection]').addEventListener('click', () => {boxes.forEach(box => box.checked = false); refresh();});
});

const orderDetailDrawer = document.querySelector('#order-detail-drawer');
const orderDetailContent = document.querySelector('#order-detail-content');
let orderDetailRequest;

if (orderDetailDrawer && orderDetailContent) {
    const orderDetailTitle = document.querySelector('#order-detail-title');
    const orderDetailCreated = document.querySelector('#order-detail-created');
    const openDrawer = () => {
        orderDetailDrawer.hidden = false;
        orderDetailDrawer.setAttribute('aria-hidden', 'false');
        document.body.classList.add('has-order-drawer');
    };
    const closeDrawer = () => {
        orderDetailRequest?.abort();
        orderDetailDrawer.hidden = true;
        orderDetailDrawer.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('has-order-drawer');
    };
    document.querySelectorAll('[data-order-detail-url]').forEach(button => {
        button.addEventListener('click', async () => {
            orderDetailRequest?.abort();
            orderDetailRequest = new AbortController();
            orderDetailContent.innerHTML = '<p class="order-detail-drawer__loading">Đang tải chi tiết đơn hàng…</p>';
            if (orderDetailTitle) orderDetailTitle.textContent = `Đơn ${button.dataset.orderCode || ''}`.trim();
            if (orderDetailCreated) orderDetailCreated.textContent = button.dataset.orderCreated || '';
            openDrawer();

            try {
                const response = await fetch(button.dataset.orderDetailUrl, {
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    signal: orderDetailRequest.signal,
                });
                if (!response.ok || response.redirected) throw new Error('Không tải được chi tiết đơn hàng.');
                orderDetailContent.innerHTML = await response.text();
            } catch (error) {
                if (error.name === 'AbortError') return;
                orderDetailContent.innerHTML = '<p class="order-detail-drawer__error" role="alert">Không tải được chi tiết đơn hàng. Vui lòng thử lại.</p>';
            }
        });
    });

    orderDetailDrawer.querySelectorAll('[data-order-detail-close]').forEach(button => {
        button.addEventListener('click', closeDrawer);
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !orderDetailDrawer.hidden) closeDrawer();
    });
}

const orderSelectAll = document.querySelector('#order-select-all');
const orderSelectionRows = [...document.querySelectorAll('.row-check')];
const orderBulkActions = document.querySelector('#order-bulk-actions');
const selectedOrderCount = document.querySelector('#selected-order-count');
const openSelectedOrder = document.querySelector('#open-selected-order');
const clearOrderSelection = document.querySelector('#clear-order-selection');

if (orderSelectAll && orderSelectionRows.length && orderBulkActions && selectedOrderCount && openSelectedOrder && clearOrderSelection) {
    const selectedOrders = () => orderSelectionRows.filter(box => box.checked);
    const refreshOrderSelection = () => {
        const selected = selectedOrders();
        orderBulkActions.hidden = selected.length === 0;
        selectedOrderCount.textContent = selected.length;
        orderSelectAll.checked = selected.length === orderSelectionRows.length;
        orderSelectAll.indeterminate = selected.length > 0 && selected.length < orderSelectionRows.length;
        openSelectedOrder.disabled = selected.length !== 1;
        openSelectedOrder.title = selected.length === 1 ? '' : 'Chọn một đơn để xem chi tiết.';
        orderSelectionRows.forEach(box => box.closest('tr').classList.toggle('is-row-selected', box.checked));
    };

    orderSelectAll.addEventListener('change', () => {
        orderSelectionRows.forEach(box => { box.checked = orderSelectAll.checked; });
        refreshOrderSelection();
    });
    orderSelectionRows.forEach(box => box.addEventListener('change', refreshOrderSelection));
    clearOrderSelection.addEventListener('click', () => {
        orderSelectionRows.forEach(box => { box.checked = false; });
        refreshOrderSelection();
    });
    openSelectedOrder.addEventListener('click', () => {
        const row = selectedOrders()[0]?.closest('tr');
        row?.querySelector('[data-order-detail-url]')?.click();
    });
    refreshOrderSelection();
}
