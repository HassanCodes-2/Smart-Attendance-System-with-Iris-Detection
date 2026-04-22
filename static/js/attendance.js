/**
 * attendance.js — Iris capture + attendance submission.
 * Depends on: utils.js, camera.js
 */

(function () {
    var captureBtn = document.getElementById('captureBtn');
    if (!captureBtn) return;

    captureBtn.addEventListener('click', async function () {
        var imageData = CameraModule.capture();
        if (!imageData) return;

        CameraModule.setStatus('Scanning iris…', 'scanning');
        var orig = captureBtn.innerHTML;
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating…';

        try {
            var res = await fetch('/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData })
            });
            var result = await res.json();

            if (result.success) {
                var pct = result.score
                    ? ' (' + Math.min(Math.round((result.score / 50) * 100), 100) + '% match)'
                    : '';
                CameraModule.flash('success');
                CameraModule.setStatus(result.message, 'success');
                showToast(result.message + pct, 'success');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, true);
            } else {
                CameraModule.flash('error');
                CameraModule.setStatus(result.message || 'No match found', 'error');
                showToast(result.message || 'No match found.', 'error');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, false);
            }
        } catch (err) {
            CameraModule.flash('error');
            CameraModule.setStatus('Server error', 'error');
            showToast('Server connection error.', 'error');
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = orig;
            setTimeout(function () { CameraModule.setStatus('Ready to scan', 'ready'); }, 3000);
        }
    });
})();
