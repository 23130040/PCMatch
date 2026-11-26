
document.addEventListener('DOMContentLoaded', function () {

    const form = document.getElementById('change-password-form');

    if (!form) return;

    const currentPassword = document.getElementById('current-password');
    const newPassword = document.getElementById('new-password');
    const confirmPassword = document.getElementById('confirm-password');

    const submitButton = document.getElementById('submit-btn');
    const clearButton = document.getElementById('clear-form-btn');

    const bars = [
        document.getElementById('bar-1'),
        document.getElementById('bar-2'),
        document.getElementById('bar-3'),
        document.getElementById('bar-4')
    ];

    const criteria = {
        length: document.getElementById('crit-length'),
        upper: document.getElementById('crit-upper'),
        lower: document.getElementById('crit-lower'),
        number: document.getElementById('crit-number'),
        special: document.getElementById('crit-special')
    };

    document.querySelectorAll('.eye-toggle').forEach(function (button) {

        button.addEventListener('click', function () {

            const targetId = button.dataset.target;
            const input = document.getElementById(targetId);
            const icon = button.querySelector('i');

            if (!input || !icon) return;

            const isHidden = input.type === 'password';

            input.type = isHidden ? 'text' : 'password';

            icon.classList.toggle('fa-eye', !isHidden);
            icon.classList.toggle('fa-eye-slash', isHidden);

        });

    });

    function setCriterion(element, met) {

        if (!element) return;

        const icon = element.querySelector('i');

        element.classList.toggle('met', met);

        if (icon) {

            icon.className = met
                ? 'fa-solid fa-circle-check'
                : 'fa-solid fa-circle-xmark';

        }

    }

    function checkStrength(value) {

        return {
            length: value.length >= 8,
            upper: /[A-Z]/.test(value),
            lower: /[a-z]/.test(value),
            number: /[0-9]/.test(value),
            special: /[^A-Za-z0-9]/.test(value)
        };

    }

    function updateStrength() {

        const value = newPassword.value;

        const result = checkStrength(value);

        Object.keys(criteria).forEach(function (key) {

            setCriterion(criteria[key], result[key]);

        });

        const score = Object.values(result).filter(Boolean).length;

        const level = value.length === 0
            ? 0
            : Math.min(4, Math.ceil(score * 4 / 5));

        bars.forEach(function (bar, index) {

            if (!bar) return;

            bar.className = 'strength-bar';

            if (index < level) {
                bar.classList.add('active-' + level);
            }

        });

        return score === 5;

    }

    function checkConfirmation() {

        const feedback = document.getElementById(
            'confirm-password-feedback'
        );

        const hasConfirmation = confirmPassword.value.length > 0;

        const matches = (
            hasConfirmation &&
            confirmPassword.value === newPassword.value
        );

        if (feedback) {

            if (!hasConfirmation) {
                feedback.textContent = '';
            } else if (!matches) {
                feedback.textContent = 'Mật khẩu xác nhận không khớp.';
            } else {
                feedback.textContent = 'Mật khẩu xác nhận trùng khớp.';
            }

            feedback.classList.toggle('is-error', hasConfirmation && !matches);
            feedback.classList.toggle('is-success', matches);

        }

        return matches;

    }

    function updateSubmitButton() {

        const strong = updateStrength();

        const confirmed = checkConfirmation();

        const hasCurrentPassword = currentPassword.value.length > 0;

        submitButton.disabled = !(
            hasCurrentPassword &&
            strong &&
            confirmed
        );

    }

    currentPassword.addEventListener('input', updateSubmitButton);
    newPassword.addEventListener('input', updateSubmitButton);
    confirmPassword.addEventListener('input', updateSubmitButton);

    clearButton.addEventListener('click', function () {

        form.reset();

        updateSubmitButton();

        currentPassword.type = 'password';
        newPassword.type = 'password';
        confirmPassword.type = 'password';

        document.querySelectorAll('.eye-toggle i').forEach(function (icon) {

            icon.className = 'fa-regular fa-eye';

        });

    });

    form.addEventListener('submit', function (event) {

        updateSubmitButton();

        if (submitButton.disabled) {

            event.preventDefault();

            return;

        }

        submitButton.disabled = true;

        submitButton.innerHTML =
            '<i class="fa-solid fa-spinner fa-spin"></i> Đang cập nhật...';

    });

    updateSubmitButton();

});
