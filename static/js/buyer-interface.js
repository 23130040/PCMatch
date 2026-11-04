// UI only: all content is rendered by Django/HTML and business forms submit normally.
document.documentElement.classList.add('interface-ready');

const header = document.querySelector('.buyer-header');
const nav = document.querySelector('#market-nav');
const dock = document.querySelector('.header-nav-strip');
const menu = document.querySelector('#buyer-menu');
const menuButton = document.querySelector('[data-ui-menu]');

menuButton?.addEventListener('click', () => {
    menu.querySelector('[data-menu-body]').append(nav);
    nav.classList.add('open');
    menuButton.setAttribute('aria-expanded', 'true');
    menu.showModal();
});
document.querySelector('[data-ui-menu-close]')?.addEventListener('click', () => menu.close());
menu?.addEventListener('close', () => {
    dock.append(nav);
    nav.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.focus();
});
matchMedia('(min-width:768px)').addEventListener('change', event => {
    if (event.matches && menu?.open) menu.close();
});
header?.querySelectorAll('.header-dropdown').forEach(dropdown => {
    if (dropdown.querySelector('[aria-current]')) dropdown.classList.add('is-current');
});
window.addEventListener('scroll', () => {
    header?.classList.toggle('header-scrolled', scrollY > 260 && !header.contains(document.activeElement));
}, {passive: true});
header?.addEventListener('focusin', () => header.classList.remove('header-scrolled'));

const search = document.querySelector('#global-search');
const suggestions = document.querySelector('#header-suggestions');
search?.addEventListener('focus', () => {suggestions.hidden = false; search.setAttribute('aria-expanded', 'true');});
document.addEventListener('click', event => {
    if (!event.target.closest('.header-search-wrap') && suggestions) {suggestions.hidden = true; search.setAttribute('aria-expanded', 'false');}
    document.querySelectorAll('.buyer-header details[open], .buyer-menu details[open]').forEach(dropdown => {
        if (!dropdown.contains(event.target)) dropdown.open = false;
    });
});

const filterDrawer = document.querySelector('#filter-drawer');
const filterHome = document.querySelector('#filter-home');
const filterForm = document.querySelector('#catalog-filters');
const filterButton = document.querySelector('[data-ui-filters]');
filterButton?.addEventListener('click', () => {
    filterDrawer.querySelector('[data-drawer-body]').append(filterForm);
    filterButton.setAttribute('aria-expanded', 'true');
    filterDrawer.showModal();
});
document.querySelector('[data-ui-filters-close]')?.addEventListener('click', () => filterDrawer.close());
filterDrawer?.addEventListener('close', () => {
    filterHome.append(filterForm);
    filterButton.setAttribute('aria-expanded', 'false');
    filterButton.focus();
});

document.querySelectorAll('[data-password-toggle]').forEach(button => button.addEventListener('click', () => {
    const field = document.getElementById(button.dataset.passwordToggle);
    field.type = field.type === 'password' ? 'text' : 'password';
    button.setAttribute('aria-label', field.type === 'password' ? 'Hiện mật khẩu' : 'Ẩn mật khẩu');
}));

document.querySelectorAll('[data-home-carousel]').forEach(root => {
    const slides = [...root.querySelectorAll('.home-newest-slide')];
    const dots = [...root.querySelectorAll('[data-newest-index]')];
    let current = 0;
    function show(index) {
        if (!slides.length) return;
        current = (index + slides.length) % slides.length;
        slides.forEach((slide, i) => slide.hidden = i !== current);
        dots.forEach((dot, i) => dot.setAttribute('aria-pressed', String(i === current)));
        root.querySelector('[data-newest-position]').textContent = (current + 1) + ' / ' + slides.length;
    }
    root.querySelectorAll('[data-newest-step]').forEach(button => button.addEventListener('click', () => show(current + Number(button.dataset.newestStep))));
    dots.forEach(dot => dot.addEventListener('click', () => show(Number(dot.dataset.newestIndex))));
    root.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) || event.altKey || event.ctrlKey || event.metaKey) return;
        event.preventDefault();
        show(event.key === 'Home' ? 0 : event.key === 'End' ? slides.length - 1 : current + (event.key === 'ArrowRight' ? 1 : -1));
    });
});
