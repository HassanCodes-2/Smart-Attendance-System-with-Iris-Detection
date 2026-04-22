/**
 * camera.js — Webcam management, iris overlay, status bar, flash effects.
 * Exposes: window.CameraModule
 */

window.CameraModule = (function () {
    var video      = document.getElementById('video');
    var canvas     = document.getElementById('canvas');
    var wrapper    = document.getElementById('camera-wrapper');
    var statusEl   = document.getElementById('camera-status');
    var statusText = document.getElementById('status-text');
    var flashEl    = document.getElementById('camera-flash');
    var stream     = null;

    // ── Init ────────────────────────────────────────────────────────────────

    function init() {
        if (!video) return;
        setStatus('Requesting camera…', 'scanning');
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function (s) {
                stream = s;
                video.srcObject = stream;
                video.onloadedmetadata = function () {
                    setStatus('Ready to scan', 'ready');
                };
            })
            .catch(function () {
                setStatus('Camera unavailable', 'error');
                showToast('Camera access denied or unavailable.', 'error');
            });
    }

    // ── Status ───────────────────────────────────────────────────────────────

    function setStatus(text, type) {
        if (!statusEl || !statusText) return;
        statusEl.className = 'camera-status ' + (type || '');
        statusText.textContent = text;
    }

    // ── Capture ──────────────────────────────────────────────────────────────

    function capture() {
        if (!video || !video.videoWidth || !video.videoHeight) {
            showToast('Camera is not ready yet. Please wait.', 'error');
            return null;
        }
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        return canvas.toDataURL('image/jpeg');
    }

    // ── Flash ────────────────────────────────────────────────────────────────

    function flash(type) {
        if (!flashEl || !wrapper) return;
        // Remove old state classes
        wrapper.classList.remove('state-success', 'state-error');
        flashEl.classList.remove('flash-success', 'flash-error');

        void flashEl.offsetWidth; // reflow to restart animation

        if (type === 'success') {
            wrapper.classList.add('state-success');
            flashEl.classList.add('flash-success');
        } else {
            wrapper.classList.add('state-error');
            flashEl.classList.add('flash-error');
        }

        // Reset border after 2s
        setTimeout(function () {
            wrapper.classList.remove('state-success', 'state-error');
        }, 2000);
    }

    // ── Public API ───────────────────────────────────────────────────────────

    return { init: init, capture: capture, flash: flash, setStatus: setStatus };
})();

// Auto-init on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function () {
    CameraModule.init();
});
