// Presentation only. Django renders every page and handles authentication/data.
const shell = document.getElementById('shop-shell');
const toggle = document.querySelector('[data-sidebar-toggle]');

function setSidebar(open) {
    shell?.classList.toggle('is-sidebar-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
}

toggle?.addEventListener('click', () => setSidebar(!shell.classList.contains('is-sidebar-open')));
document.getElementById('shop-overlay')?.addEventListener('click', () => setSidebar(false));
document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    setSidebar(false);
    document.querySelectorAll('.sa-user-dropdown[open]').forEach(menu => menu.removeAttribute('open'));
});

document.querySelectorAll('[data-password-toggle]').forEach(button => {
    button.addEventListener('click', () => {
        const input = document.getElementById(button.dataset.passwordToggle);
        if (!input) return;
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        button.setAttribute('aria-label', show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
        button.setAttribute('aria-pressed', String(show));
    });
});

document.querySelectorAll('[data-select-all]').forEach(checkbox => {
    const table = checkbox.closest('table');
    const rows = Array.from(table.querySelectorAll('[data-select-row]'));
    checkbox.addEventListener('change', () => rows.forEach(row => { row.checked = checkbox.checked; }));
    rows.forEach(row => row.addEventListener('change', () => {
        const selected = rows.filter(item => item.checked).length;
        checkbox.checked = rows.length > 0 && selected === rows.length;
        checkbox.indeterminate = selected > 0 && selected < rows.length;
    }));
});
