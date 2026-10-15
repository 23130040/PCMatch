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
