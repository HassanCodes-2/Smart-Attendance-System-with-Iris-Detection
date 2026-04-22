/**
 * counters.js — Animated count-up for .stat-value elements.
 * Runs on DOMContentLoaded.
 */

(function () {
    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    function animateCounter(el, from, to, duration, suffix) {
        suffix = suffix || '';
        var start = null;

        function step(timestamp) {
            if (!start) start = timestamp;
            var elapsed  = timestamp - start;
            var progress = Math.min(elapsed / duration, 1);
            var value    = Math.round(from + (to - from) * easeOutCubic(progress));
            el.textContent = value + suffix;
            if (progress < 1) requestAnimationFrame(step);
        }

        requestAnimationFrame(step);
    }

    function initCounters() {
        document.querySelectorAll('.stat-value').forEach(function (el) {
            var raw    = el.textContent.trim();
            var num    = parseFloat(raw);
            // Only animate numeric values (skip '—', empty, etc.)
            if (isNaN(num) || num === 0) return;
            var suffix = raw.replace(/[\d.]/g, '');
            el.textContent = '0' + suffix;
            animateCounter(el, 0, num, 1100, suffix);
        });
    }

    document.addEventListener('DOMContentLoaded', initCounters);
})();
