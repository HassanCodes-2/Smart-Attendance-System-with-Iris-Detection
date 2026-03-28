var path = window.location.pathname;
document.querySelectorAll(".nav-link").forEach(function(link) {
    var href = link.getAttribute("href");
    if (href === path || (href !== "/" && path.startsWith(href))) {
        link.classList.add("active");
    }
});

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

var toastContainer = document.createElement("div");
toastContainer.className = "toast-container";
document.body.appendChild(toastContainer);

function showToast(message, type) {
    type = type || "info";
    var icons = { success: "fa-circle-check", error: "fa-triangle-exclamation", info: "fa-circle-info" };
    var toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.innerHTML = "<i class=\"fa-solid " + icons[type] + "\"></i><span>" + message + "</span>";
    toastContainer.appendChild(toast);
    setTimeout(function() {
        toast.style.animation = "toastOut 0.3s forwards";
        toast.addEventListener("animationend", function() { toast.remove(); });
    }, 4500);
}

var video      = document.getElementById("video");
var canvas     = document.getElementById("canvas");
var captureBtn = document.getElementById("captureBtn");
var nameInput  = document.getElementById("nameInput");
var userIdInput = document.getElementById("userIdInput");
var deptInput  = document.getElementById("departmentInput");
var stream     = null;

if (video) {
    navigator.mediaDevices.getUserMedia({ video: true }).then(function(s) {
        stream = s;
        video.srcObject = stream;
    }).catch(function() {
        showToast("Camera access denied or unavailable.", "error");
    });
}

function captureImage() {
    if (!video.videoWidth || !video.videoHeight) {
        showToast("Camera is not ready yet. Please wait.", "error");
        return null;
    }
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg");
}

function showAnnotatedPreview(b64, isSuccess) {
    var wrap = document.createElement("div");
    wrap.style.cssText = "position:fixed;bottom:80px;right:20px;width:160px;z-index:9998;animation:toastIn 0.3s forwards";
    var img = new Image();
    img.src = "data:image/jpeg;base64," + b64;
    img.style.cssText = "width:100%;border-radius:10px;border:2px solid " + (isSuccess ? "var(--success)" : "var(--error)") + ";box-shadow:0 0 20px rgba(0,0,0,0.6);transform:scaleX(-1);display:block";
    wrap.appendChild(img);
    document.body.appendChild(wrap);
    setTimeout(function() { wrap.remove(); }, 4500);
}

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
        if (allFilled && fp1.classList.contains("active")) setStep(2);
    }
    fieldInputs.forEach(function(f) { f.addEventListener("input", checkFields); });
}

if (captureBtn) {
    captureBtn.addEventListener("click", async function() {
        var pageType = captureBtn.dataset.type;

        if (pageType === "register") {
            var uid  = userIdInput ? userIdInput.value.trim() : "";
            var name = nameInput   ? nameInput.value.trim()   : "";
            var dept = deptInput   ? deptInput.value.trim()   : "";
            if (!uid)  { showToast("Please enter your ID.", "error");         return; }
            if (!name) { showToast("Please enter your name.", "error");       return; }
            if (!dept) { showToast("Please enter your department.", "error"); return; }
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
                if (result.score) msg += " (" + Math.min(Math.round((result.score / 50) * 100), 100) + "% match)";
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
            showToast("Server connection error.", "error");
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = originalHTML;
        }
    });
}