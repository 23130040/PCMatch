// Selection is stored in the Django session; the tray markup comes from HTML templates.
(() => {
    let busy = false;
    let feedbackTimer;
    document.addEventListener('submit', async event => {
        const form = event.target.closest('[data-comparison-form]');
        if (!form || !window.fetch) return;
        event.preventDefault();
        if (busy) return;
        busy = true;
        const buttons = [...document.querySelectorAll('[data-comparison-form] button')];
        buttons.forEach(button => button.disabled = true);
        try {
            const response = await fetch(form.getAttribute('action'), {
                method: 'POST', body: new FormData(form), headers: {Accept: 'application/json'},
            });
            const result = await response.json();
            if (!Array.isArray(result.selected) || typeof result.html !== 'string') throw Error();
            const fragment = new DOMParser().parseFromString(result.html, 'text/html').querySelector('#product-compare-tray');
            if (!fragment) throw Error();
            fragment.hidden = false;
            document.querySelector('#product-compare-tray').replaceWith(fragment);
            document.querySelectorAll('[data-compare-product]').forEach(button => {
                const selected = result.selected.includes(Number(button.dataset.compareProduct));
                button.setAttribute('aria-pressed', String(selected));
                button.querySelector('[data-compare-add-label]').hidden = selected;
                button.querySelector('[data-compare-added-label]').hidden = !selected;
            });
            document.querySelectorAll('[data-compare-count]').forEach(node => node.textContent = result.selected.length);
            const feedback = fragment.querySelector('[data-comparison-feedback]');
            feedback.textContent = result.message;
            feedback.hidden = false;
            feedback.classList.toggle('message--error', result.error);
            feedback.setAttribute('role', result.error ? 'alert' : 'status');
            clearTimeout(feedbackTimer);
            feedbackTimer = setTimeout(() => {
                feedback.hidden = true;
                if (!fragment.querySelector('.compare-tray-inner')) fragment.hidden = true;
            }, result.error ? 7000 : 4000);
        } catch {
            // Submit normally if progressive enhancement is unavailable.
            form.submit();
        } finally {
            buttons.forEach(button => button.disabled = false);
            busy = false;
        }
    });
})();
