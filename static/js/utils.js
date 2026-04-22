/**
 * utils.js — Shared utilities: toast, annotated preview, dept color
 */

// ── Toast ─────────────────────────────────────────────────────────────────

(function () {
    var tc = document.createElement('div');
    tc.className = 'toast-container';
    document.body.appendChild(tc);
    window._toastContainer = tc;
})();

function showToast(message, type) {
    type = type || 'info';
    var icons = {
        success: 'fa-circle-check',
        error:   'fa-triangle-exclamation',
        info:    'fa-circle-info'
    };
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = '<i class="fa-solid ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span>';
    window._toastContainer.appendChild(t);
    setTimeout(function () {
        t.style.animation = 'toastOut 0.3s forwards';
        t.addEventListener('animationend', function () { t.remove(); });
    }, 4500);
}

// ── Annotated Preview ─────────────────────────────────────────────────────

function showAnnotatedPreview(b64, isSuccess) {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;bottom:80px;right:20px;width:155px;z-index:9998;animation:toastIn 0.3s forwards';
    var img = new Image();
    img.src = 'data:image/jpeg;base64,' + b64;
    img.style.cssText = [
        'width:100%',
        'border-radius:10px',
        'border:2px solid ' + (isSuccess ? 'var(--success)' : 'var(--error)'),
        'box-shadow:0 0 20px rgba(0,0,0,0.6)',
        'transform:scaleX(-1)',
        'display:block'
    ].join(';');
    wrap.appendChild(img);
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, 4500);
}

// ── Department Color ──────────────────────────────────────────────────────

var DEPT_COLORS = [
    { bg: 'rgba(99,102,241,0.12)',  text: '#818cf8', border: 'rgba(99,102,241,0.3)'  },
    { bg: 'rgba(168,85,247,0.12)', text: '#c084fc', border: 'rgba(168,85,247,0.3)' },
    { bg: 'rgba(236,72,153,0.12)', text: '#f472b6', border: 'rgba(236,72,153,0.3)' },
    { bg: 'rgba(245,158,11,0.12)', text: '#fbbf24', border: 'rgba(245,158,11,0.3)' },
    { bg: 'rgba(34,197,94,0.12)',   text: '#4ade80', border: 'rgba(34,197,94,0.3)'   },
    { bg: 'rgba(14,165,233,0.12)',  text: '#38bdf8', border: 'rgba(14,165,233,0.3)'  },
    { bg: 'rgba(239,68,68,0.12)',   text: '#f87171', border: 'rgba(239,68,68,0.3)'   },
    { bg: 'rgba(20,184,166,0.12)',  text: '#2dd4bf', border: 'rgba(20,184,166,0.3)'  },
];

function getDeptColor(dept) {
    var hash = 0;
    for (var i = 0; i < dept.length; i++) {
        hash = (hash * 31 + dept.charCodeAt(i)) & 0x7fffffff;
    }
    return DEPT_COLORS[hash % DEPT_COLORS.length];
}

function applyDeptColors() {
    document.querySelectorAll('[data-dept-label]').forEach(function (el) {
        var dept  = el.dataset.deptLabel;
        var color = getDeptColor(dept);
        el.style.background   = color.bg;
        el.style.color        = color.text;
        el.style.borderColor  = color.border;
    });
}
