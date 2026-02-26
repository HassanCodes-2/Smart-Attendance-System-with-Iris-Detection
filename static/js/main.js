/* IrisSecure - Main JS */

// Active nav highlight
(function () {
    var path = window.location.pathname;
    document.querySelectorAll(".nav-link").forEach(function(link) {
        var href = link.getAttribute("href");
        var isHome  = href === "/" && path === "/";
        var isOther = href !== "/" && path.startsWith(href);
        if (isHome || isOther) link.classList.add("active");
    });
})();

// Hamburger / mobile nav
var hamburger    = document.getElementById("hamburger");
var mobileOverlay = document.getElementById("mobile-overlay");

if (hamburger && mobileOverlay) {
    document.querySelectorAll("#main-nav .nav-link").forEach(function(link) {
        mobileOverlay.appendChild(link.cloneNode(true));
    });

    hamburger.addEventListener("click", function() {
        var open = mobileOverlay.classList.toggle("open");
        hamburger.classList.toggle("open", open);
        document.body.style.overflow = open ? "hidden" : "";
    });

    mobileOverlay.querySelectorAll(".nav-link").forEach(function(l) {
        l.addEventListener("click", function() {
            mobileOverlay.classList.remove("open");
            hamburger.classList.remove("open");
            document.body.style.overflow = "";
        });
    });
}

// Live clock
var clockEl = document.getElementById("live-clock");
if (clockEl) {
    function updateClock() {
        clockEl.textContent = new Date().toLocaleString(undefined, {
            weekday: "short", year: "numeric", month: "short",
            day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit"
        });
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// Toast
var toastContainer = document.createElement("div");
toastContainer.className = "toast-container";
document.body.appendChild(toastContainer);

function showToast(message, type) {
    type = type || "info";
    var toast = document.createElement("div");
    toast.className = "toast " + type;
    var icons = { success: "fa-circle-check", error: "fa-triangle-exclamation", info: "fa-circle-info" };
    var icon  = icons[type] || icons.info;
    toast.innerHTML = "<i class=\"fa-solid " + icon + "\"></i><span>" + message + "</span>";
    toastContainer.appendChild(toast);
    setTimeout(function() {
        toast.style.animation = "toastOut 0.3s forwards";
        toast.addEventListener("animationend", function() { toast.remove(); });
    }, 4500);
}

// Camera
var video         = document.getElementById("video");
var canvas        = document.getElementById("canvas");
var captureBtn    = document.getElementById("captureBtn");
var nameInput     = document.getElementById("nameInput");
var userIdInput   = document.getElementById("userIdInput");
var deptInput     = document.getElementById("departmentInput");
var stream        = null;

function startCamera() {
    navigator.mediaDevices.getUserMedia({ video: true }).then(function(s) {
        stream = s;
        if (video) video.srcObject = stream;
    }).catch(function(err) {
        console.error("Camera error:", err);
        showToast("Camera access denied or unavailable.", "error");
    });
}

if (video) startCamera();

function captureImage() {
    if (!video.videoWidth || !video.videoHeight) {
        showToast("Camera is not ready yet. Please wait.", "error");
        return null;
    }
    var ctx = canvas.getContext("2d");
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg");
}

function showAnnotatedPreview(b64, isSuccess) {
    var wrap = document.createElement("div");
    wrap.style.cssText = "position:fixed;bottom:80px;right:20px;width:160px;z-index:9998;animation:toastIn 0.3s forwards";
    var img = new Image();
    img.src = "data:image/jpeg;base64," + b64;
    var borderColor = isSuccess ? "var(--success)" : "var(--error)";
    img.style.cssText = "width:100%;border-radius:10px;border:2px solid " + borderColor + ";box-shadow:0 0 20px rgba(0,0,0,0.6);transform:scaleX(-1);display:block";
    wrap.appendChild(img);
    document.body.appendChild(wrap);
    setTimeout(function() { wrap.remove(); }, 4500);
}

// Form progress stepper (register page only)
function setStep(stepNum) {
    var steps = [null,
        document.getElementById("fp1"),
        document.getElementById("fp2"),
        document.getElementById("fp3")
    ];
    var lines = [null,
        document.getElementById("fp-line1"),
        document.getElementById("fp-line2")
    ];
    steps.forEach(function(el, i) {
        if (!el) return;
        el.classList.remove("active", "done");
        if (i < stepNum) {
            el.classList.add("done");
            el.querySelector(".fp-dot").innerHTML = "<i class=\"fa-solid fa-check\" style=\"font-size:0.65rem\"></i>";
        }
        if (i === stepNum) el.classList.add("active");
    });
    lines.forEach(function(el, i) {
        if (!el) return;
        el.classList.toggle("done", i < stepNum);
    });
}

if (document.getElementById("fp1")) {
    var fieldInputs = [userIdInput, nameInput, deptInput].filter(Boolean);
    function checkFields() {
        var allFilled = fieldInputs.every(function(f) { return f.value.trim().length > 0; });
        var fp1 = document.getElementById("fp1");
        if (allFilled && fp1 && fp1.classList.contains("active")) setStep(2);
        if (!allFilled && fp1 && !fp1.classList.contains("active") && !fp1.classList.contains("done")) setStep(1);
    }
    fieldInputs.forEach(function(f) { f.addEventListener("input", checkFields); });
}

// Capture button
if (captureBtn) {
    captureBtn.addEventListener("click", async function() {
        var pageType = captureBtn.dataset.type;

        if (pageType === "register") {
            var uid  = userIdInput ? userIdInput.value.trim() : "";
            var name = nameInput   ? nameInput.value.trim()   : "";
            var dept = deptInput   ? deptInput.value.trim()   : "";
            if (!uid)  { showToast("Please enter your ID.", "error");         if (userIdInput) userIdInput.focus();   return; }
            if (!name) { showToast("Please enter your name.", "error");       if (nameInput)   nameInput.focus();     return; }
            if (!dept) { showToast("Please enter your department.", "error"); if (deptInput)   deptInput.focus();     return; }
        }

        var imageData = captureImage();
        if (!imageData) return;

        var payload = { image: imageData };
        if (pageType === "register") {
            payload.user_id    = userIdInput.value.trim();
            payload.name       = nameInput.value.trim();
            payload.department = deptInput.value.trim();
        }

        var originalHTML = captureBtn.innerHTML;
        captureBtn.disabled = true;
        captureBtn.innerHTML = "<i class=\"fa-solid fa-spinner fa-spin\"></i> Processing...";

        try {
            var res = await fetch(pageType === "register" ? "/register" : "/attendance", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            var result = await res.json();

            if (result.success) {
                var msg = result.message;
                if (result.score) {
                    var pct = Math.min(Math.round((result.score / 50) * 100), 100);
                    msg += " (" + pct + "% match)";
                }
                showToast(msg, "success");
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, true);
                if (pageType === "register") {
                    setStep(3);
                    setTimeout(function() {
                        if (userIdInput) userIdInput.value = "";
                        if (nameInput)   nameInput.value   = "";
                        if (deptInput)   deptInput.value   = "";
                        setStep(1);
                    }, 3000);
                }
            } else {
                showToast(result.message, "error");
                if (result.annotated_image) showAnnotatedPreview(result.annotated_image, false);
            }
        } catch (err) {
            console.error(err);
            showToast("Server connection error.", "error");
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = originalHTML;
        }
    });
}
