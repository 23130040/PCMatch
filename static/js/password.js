document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.eye-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var targetId = btn.getAttribute('data-target');
            var input = document.getElementById(targetId);
            var icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });

    var newPasswordInput = document.getElementById('new-password');
    var bars = [
        document.getElementById('bar-1'),
        document.getElementById('bar-2'),
        document.getElementById('bar-3'),
        document.getElementById('bar-4')
    ];
    var criteria = {
        length: document.getElementById('crit-length'),
        upper: document.getElementById('crit-upper'),
        lower: document.getElementById('crit-lower'),
        number: document.getElementById('crit-number'),
        special: document.getElementById('crit-special')
    };

    function setCriterion(el, met) {
        var icon = el.querySelector('i');
        if (met) {
            el.classList.add('met');
            icon.className = 'fa-solid fa-circle-check';
        } else {
            el.classList.remove('met');
            icon.className = 'fa-solid fa-circle-xmark';
        }
    }

    function updateStrength(val) {
        var hasLength = val.length >= 8;
        var hasUpper = /[A-Z]/.test(val);
        var hasLower = /[a-z]/.test(val);
        var hasNumber = /[0-9]/.test(val);
        var hasSpecial = /[^A-Za-z0-9]/.test(val);

        setCriterion(criteria.length, hasLength);
        setCriterion(criteria.upper, hasUpper);
        setCriterion(criteria.lower, hasLower);
        setCriterion(criteria.number, hasNumber);
        setCriterion(criteria.special, hasSpecial);

        var score = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length;
        var level = val.length === 0 ? 0 : score <= 1 ? 1 : score <= 2 ? 2 : score <= 3 ? 3 : 4;

        bars.forEach(function (bar, idx) {
            bar.className = 'strength-bar';
            if (idx < level) {
                bar.classList.add('active-' + level);
            }
        });
    }

    newPasswordInput.addEventListener('input', function () {
        updateStrength(this.value);
    });

    document.getElementById('clear-form-btn').addEventListener('click', function () {
        document.getElementById('change-password-form').reset();
        updateStrength('');
    });

    document.getElementById('change-password-form').addEventListener('submit', function (e) {
        e.preventDefault();
    });
});
