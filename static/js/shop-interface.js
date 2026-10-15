// Presentation only. Authentication and mutations belong to Django views/forms.
document.querySelectorAll('[data-sidebar-toggle]').forEach(button => {
    button.addEventListener('click', () => {
        const shell = document.querySelector('.shop-shell');
        if (!shell) return;
        button.setAttribute('aria-expanded', String(shell.classList.toggle('is-sidebar-open')));
    });
});
