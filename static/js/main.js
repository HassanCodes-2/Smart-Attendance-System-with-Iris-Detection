// ── Live clock ────────────────────────────────────────────────────────────────
var clockEl = document.getElementById('live-clock');
if (clockEl) {
    function updateClock() {
        clockEl.textContent = new Date().toLocaleString(undefined, {
            weekday: 'short', year: 'numeric', month: 'short',
            day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(message, type) {
    type = type || 'info';
    var icons = { success: 'fa-circle-check', error: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    var tc = document.querySelector('.toast-container');
    if (!tc) { tc = document.createElement('div'); tc.className = 'toast-container'; document.body.appendChild(tc); }
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = '<i class="fa-solid ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span>';
    tc.appendChild(t);
    setTimeout(function () {
        t.style.animation = 'toastOut 0.3s forwards';
        t.addEventListener('animationend', function () { t.remove(); });
    }, 4500);
}

// ── Camera ────────────────────────────────────────────────────────────────────
var video      = document.getElementById('video');
var canvas     = document.getElementById('canvas');
var captureBtn = document.getElementById('captureBtn');
var stream     = null;

if (video) {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(function (s) { stream = s; video.srcObject = s; })
        .catch(function () { showToast('Camera access denied or unavailable.', 'error'); });
}

function captureImage() {
    if (!video || !video.videoWidth) { showToast('Camera not ready.', 'error'); return null; }
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg');
}

function showAnnotatedPreview(b64, isSuccess) {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;bottom:80px;right:20px;width:160px;z-index:9998;animation:toastIn 0.3s forwards';
    var img  = new Image();
    img.src  = 'data:image/jpeg;base64,' + b64;
    img.style.cssText = 'width:100%;border-radius:10px;border:2px solid ' +
        (isSuccess ? 'var(--success)' : 'var(--error)') +
        ';box-shadow:0 0 20px rgba(0,0,0,0.6);transform:scaleX(-1);display:block';
    wrap.appendChild(img);
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, 4500);
}

// ── Registration progress steps ───────────────────────────────────────────────
function setStep(n) {
    [1,2,3].forEach(function (i) {
        var el = document.getElementById('fp' + i);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (i < n) {
            el.classList.add('done');
            el.querySelector('.fp-dot').innerHTML = '<i class="fa-solid fa-check" style="font-size:0.65rem"></i>';
        }
        if (i === n) el.classList.add('active');
    });
    [1,2].forEach(function (i) {
        var ln = document.getElementById('fp-line' + i);
        if (ln) ln.classList.toggle('done', i < n);
    });
}

// Auto-advance step 1→2 when all text fields are filled
(function () {
    var fields = ['userIdInput','nameInput','departmentInput','passwordInput'].map(function (id) {
        return document.getElementById(id);
    }).filter(Boolean);
    if (!fields.length) return;
    function check() {
        var allFilled = fields.every(function (f) { return f.value.trim().length > 0; });
        var fp1 = document.getElementById('fp1');
        if (allFilled && fp1 && fp1.classList.contains('active')) setStep(2);
    }
    fields.forEach(function (f) { f.addEventListener('input', check); });
})();

// ── Capture button handler ────────────────────────────────────────────────────
if (captureBtn) {
    captureBtn.addEventListener('click', async function () {
        var pageType   = captureBtn.dataset.type;
        var imageData  = captureImage();
        if (!imageData) return;

        // Validate fields for admin-register
        if (pageType === 'admin-register') {
            var uid   = document.getElementById('userIdInput')  ? document.getElementById('userIdInput').value.trim()   : '';
            var name  = document.getElementById('nameInput')    ? document.getElementById('nameInput').value.trim()     : '';
            var dept  = document.getElementById('departmentInput') ? document.getElementById('departmentInput').value.trim() : '';
            var pwd   = document.getElementById('passwordInput')? document.getElementById('passwordInput').value.trim()  : '';
            if (!uid)  { showToast('Student ID is required.',  'error'); return; }
            if (!name) { showToast('Name is required.',        'error'); return; }
            if (!dept) { showToast('Department is required.',  'error'); return; }
            if (!pwd)  { showToast('Password is required.',    'error'); return; }
        }

        var payload = { image: imageData };

        if (pageType === 'admin-register') {
            payload.user_id      = document.getElementById('userIdInput').value.trim();
            payload.name         = document.getElementById('nameInput').value.trim();
            payload.department   = document.getElementById('departmentInput').value.trim();
            payload.parent_email = document.getElementById('parentEmailInput') ? document.getElementById('parentEmailInput').value.trim() : '';
            payload.password     = document.getElementById('passwordInput').value.trim();
        }

        var endpoint = pageType === 'admin-register'    ? '/admin/register'
                     : pageType === 'student-attendance'? '/student/mark-attendance'
                     : '/attendance';

        var origHTML     = captureBtn.innerHTML;
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';

        try {
            var res    = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var result = await res.json();

            if (result.success) {
                var msg = result.message;
                if (result.score) msg += ' (' + Math.min(Math.round((result.score / 50) * 100), 100) + '% match)';
                showToast(msg, 'success');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, true);

                if (pageType === 'admin-register') {
                    setStep(3);
                    setTimeout(function () {
                        ['userIdInput','nameInput','departmentInput','passwordInput','parentEmailInput'].forEach(function (id) {
                            var el = document.getElementById(id);
                            if (el) el.value = '';
                        });
                        setStep(1);
                    }, 3000);
                }

                if (pageType === 'student-attendance') {
                    var rb = document.getElementById('result-box');
                    if (rb) {
                        rb.classList.remove('hidden');
                        rb.style.background  = result.status === 'late' ? 'rgba(245,158,11,0.1)' : 'rgba(34,197,94,0.1)';
                        rb.style.border      = '1px solid ' + (result.status === 'late' ? 'rgba(245,158,11,0.3)' : 'rgba(34,197,94,0.3)');
                        rb.style.color       = result.status === 'late' ? 'var(--warning)' : 'var(--success)';
                        rb.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' + msg;
                        captureBtn.disabled = true;
                    }
                }
            } else {
                showToast(result.message, 'error');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, false);
            }
        } catch (err) {
            showToast('Server connection error.', 'error');
        } finally {
            if (pageType !== 'student-attendance') {
                captureBtn.disabled = false;
            }
            captureBtn.innerHTML = origHTML;
        }
    });
}

// ── Active nav link (landing page) ───────────────────────────────────────────
var path = window.location.pathname;
document.querySelectorAll('.nav-link').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
        link.classList.add('active');
    }
});
