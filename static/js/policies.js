document.addEventListener('DOMContentLoaded', function () {
    var items = document.querySelectorAll('.policy-list-item');
    var pills = document.querySelectorAll('.pill');

    items.forEach(function (item) {
        item.addEventListener('click', function () {
            items.forEach(function (i) {
                i.classList.remove('active');
                i.setAttribute('aria-pressed', 'false');
            });
            item.classList.add('active');
            item.setAttribute('aria-pressed', 'true');
        });
        item.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                item.click();
            }
        });
    });

    pills.forEach(function (pill) {
        pill.addEventListener('click', function () {
            pills.forEach(function (p) {
                p.classList.remove('active');
            });
            pill.classList.add('active');
        });
    });
});
