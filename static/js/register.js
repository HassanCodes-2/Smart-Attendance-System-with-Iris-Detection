/**
 * register.js — Registration form: step progress + iris capture + submit.
 * Depends on: utils.js, camera.js
 */

(function () {
    var userIdInput      = document.getElementById('userIdInput');
    var nameInput        = document.getElementById('nameInput');
    var deptInput        = document.getElementById('departmentInput');
    var parentEmailInput = document.getElementById('parentEmailInput');
    var captureBtn       = document.getElementById('captureBtn');

    if (!captureBtn) return;

    // ── Step progress ────────────────────────────────────────────────────────

    function setStep(n) {
        var steps = [null,
            document.getElementById('fp1'),
            document.getElementById('fp2'),
            document.getElementById('fp3')
        ];
        var lines = [null,
            document.getElementById('fp-line1'),
            document.getElementById('fp-line2')
        ];

        steps.forEach(function (el, i) {
            if (!el) return;
            el.classList.remove('active', 'done');
            if (i < n) {
                el.classList.add('done');
                el.querySelector('.fp-dot').innerHTML =
                    '<i class="fa-solid fa-check" style="font-size:0.65rem"></i>';
            }
            if (i === n) el.classList.add('active');
        });

        lines.forEach(function (el, i) {
            if (!el) return;
            el.classList.toggle('done', i < n);
        });
    }

    // Advance to step 2 when all required fields are filled
    var requiredFields = [userIdInput, nameInput, deptInput].filter(Boolean);
    requiredFields.forEach(function (f) {
        f.addEventListener('input', function () {
            var filled = requiredFields.every(function (f) { return f.value.trim().length > 0; });
            var fp1 = document.getElementById('fp1');
            if (filled && fp1 && fp1.classList.contains('active')) setStep(2);
            if (!filled && document.getElementById('fp2') && document.getElementById('fp2').classList.contains('active')) setStep(1);
        });
    });

    // ── Submit ───────────────────────────────────────────────────────────────

    captureBtn.addEventListener('click', async function () {
        var uid  = userIdInput  ? userIdInput.value.trim()  : '';
        var name = nameInput    ? nameInput.value.trim()    : '';
        var dept = deptInput    ? deptInput.value.trim()    : '';

        if (!uid)  { showToast('Please enter your ID.',         'error'); return; }
        if (!name) { showToast('Please enter your name.',       'error'); return; }
        if (!dept) { showToast('Please enter your department.', 'error'); return; }

        var imageData = CameraModule.capture();
        if (!imageData) return;

        CameraModule.setStatus('Processing…', 'scanning');
        var orig = captureBtn.innerHTML;
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';

        try {
            var res = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image:        imageData,
                    user_id:      uid,
                    name:         name,
                    department:   dept,
                    parent_email: parentEmailInput ? parentEmailInput.value.trim() : ''
                })
            });
            var result = await res.json();

            if (result.success) {
                CameraModule.flash('success');
                CameraModule.setStatus('Registered successfully!', 'success');
                showToast(result.message, 'success');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, true);
                setStep(3);
                setTimeout(function () {
                    [userIdInput, nameInput, deptInput].forEach(function (f) { if (f) f.value = ''; });
                    if (parentEmailInput) parentEmailInput.value = '';
                    setStep(1);
                    CameraModule.setStatus('Ready to scan', 'ready');
                }, 3000);
            } else {
                CameraModule.flash('error');
                CameraModule.setStatus(result.message || 'Detection failed', 'error');
                showToast(result.message, 'error');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, false);
                setTimeout(function () { CameraModule.setStatus('Ready to scan', 'ready'); }, 3000);
            }
        } catch (err) {
            CameraModule.flash('error');
            CameraModule.setStatus('Server error', 'error');
            showToast('Server connection error.', 'error');
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = orig;
        }
    });
})();
