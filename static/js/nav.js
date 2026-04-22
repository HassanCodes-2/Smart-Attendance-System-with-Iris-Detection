/**
 * nav.js — Active nav highlighting + live clock
 */

(function () {
    var path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        var href = link.getAttribute('href');
        if (href === path || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
})();

(function () {
    var clockEl = document.getElementById('live-clock');
    if (!clockEl) return;

    function updateClock() {
        clockEl.textContent = new Date().toLocaleString(undefined, {
            weekday: 'short', year: 'numeric', month: 'short',
            day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }
    updateClock();
    setInterval(updateClock, 1000);
})();
