
(() => {
    document.addEventListener('submit', async (event) => {
        const form = event.target.closest('[data-cart-add-form]');
        if (!form || !window.fetch) return;

        event.preventDefault();

        const button = form.querySelector('button[type="submit"]');
        const feedback = document.querySelector('#cart-add-feedback');

        if (!feedback || form.dataset.busy === 'true') return;

        form.dataset.busy = 'true';
        if (button) button.disabled = true;

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { Accept: 'application/json' }
            });

            const result = await response.json();

            feedback.textContent = result.message;
            feedback.hidden = false;
            feedback.classList.toggle('message--error', !response.ok);
            feedback.setAttribute(
                'role',
                response.ok ? 'status' : 'alert'
            );

            if (response.ok) {
                setTimeout(() => {
                    feedback.hidden = true;
                }, 4000);
            }
        } catch (error) {
            form.removeAttribute('data-busy');
            form.submit();
            return;
        } finally {
            delete form.dataset.busy;
            if (button) button.disabled = false;
        }
    });
})();
