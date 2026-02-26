/* =====================================================
   IrisSecure – Main JS
   ===================================================== */

// Active nav link
(function () {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        const isHome = href === '/' && path === '/';
        const isOther = href !== '/' && path.startsWith(href);
        if (isHome || isOther) link.classList.add('active');
    });
})();

// Hamburger / mobile nav
const hamburger = document.getElementById('hamburger');
const mobileOverlay = document.getElementById('mobile-overlay');

if (hamburger && mobileOverlay) {
    // Clone nav links into mobile overlay
    document.querySelectorAll('#main-nav .nav-link').forEach(link => {
        const clone = link.cloneNode(true);
        mobileOverlay.appendChild(clone);
    });

    hamburger.addEventListener('click', () => {
        const open = mobileOverlay.classList.toggle('open');
        hamburger.classList.toggle('open', open);
        document.body.style.overflow = open ? 'hidden' : '';
    });

    // Close on link click
    mobileOverlay.querySelectorAll('.nav-link').forEach(l => {
        l.addEventListener('click', () => {
            mobileOverlay.classList.remove('open');
            hamburger.classList.remove('open');
            document.body.style.overflow = '';
        });
    });
}

// Live clock (attendance page)
const clockEl = document.getElementById('live-clock');
if (clockEl) {
    const updateClock = () => {
        clockEl.textContent = new Date().toLocaleString(undefined, {
            weekday: 'short', year: 'numeric', month: 'short',
            day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    };
    updateClock();
    setInterval(updateClock, 1000);
}

// Toast notification system
const toastContainer = document.createElement('div');
toastContainer.className = 'toast-container';
document.body.appendChild(toastContainer);

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: 'fa-circle-check', error: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    const icon = icons[type] || icons.info;

    toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s forwards';
        toast.addEventListener('animationend', () => toast.remove());
    }, 4500);
}

// Camera helpers
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const nameInput = document.getElementById('nameInput');
const userIdInput = document.getElementById('userIdInput');
const departmentInput = document.getElementById('departmentInput');

let stream = null;

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (video) video.srcObject = stream;
    } catch (err) {
        console.error('Camera error:', err);
        showToast('Camera access denied or unavailable.', 'error');
    }
}

if (video) startCamera();

function captureImage() {
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
}

function showAnnotatedPreview(b64, isSuccess) {
    const container = Object.assign(document.createElement('div'), {
        style: 'position:fixed;bottom:80px;right:20px;width:160px;z-index:9998;animation:toastIn 0.3s forwards'
    });
    const img = new Image();
    img.src = 'data:image/jpeg;base64,' + b64;
    img.style.cssText = `width:100%;border-radius:10px;border:2px solid var(--${isSuccess ? 'success' : 'error'});
        box-shadow:0 0 20px rgba(0,0,0,0.6);transform:scaleX(-1);display:block`;
    container.appendChild(img);
    document.body.appendChild(container);
    setTimeout(() => container.remove(), 4500);
}

// Capture button
if (captureBtn) {
    captureBtn.addEventListener('click', async () => {
        const pageType = captureBtn.dataset.type;

        if (pageType === 'register') {
            const userId = userIdInput?.value.trim();
            const name = nameInput?.value.trim();
            const dept = departmentInput?.value.trim();
            if (!userId) { showToast('Please enter your ID.', 'error'); userIdInput?.focus(); return; }
            if (!name)   { showToast('Please enter your name.', 'error'); nameInput?.focus(); return; }
            if (!dept)   { showToast('Please enter your department.', 'error'); departmentInput?.focus(); return; }
        }

        const imageData = captureImage();
        if (!imageData) return;

        const payload = { image: imageData };
        if (pageType === 'register') {
            payload.user_id   = userIdInput.value.trim();
            payload.name       = nameInput.value.trim();
            payload.department = departmentInput.value.trim();
        }

        const originalHTML = captureBtn.innerHTML;
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';

        try {
            const res = await fetch(pageType === 'register' ? '/register' : '/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await res.json();

            if (result.success) {
                let msg = result.message;
                if (result.score) {
                    const pct = Math.min(Math.round((result.score / 50) * 100), 100);
                    msg += ` (${pct}% match)`;
                }
                showToast(msg, 'success');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, true);
                if (pageType === 'register') {
                    userIdInput.value = '';
                    nameInput.value = '';
                    departmentInput.value = '';
                }
            } else {
                showToast(result.message, 'error');
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, false);
            }
        } catch (err) {
            console.error(err);
            showToast('Server connection error.', 'error');
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = originalHTML;
        }
    });
}
