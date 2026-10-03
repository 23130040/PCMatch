document.addEventListener('DOMContentLoaded', function () {
    var pills = document.querySelectorAll('.filter-pill');
    pills.forEach(function (pill) {
        pill.addEventListener('click', function () {
            pills.forEach(function (p) {
                p.classList.remove('is-active');
            });
            pill.classList.add('is-active');
        });
    });
});
