/**
 * admin.js — Admin dashboard: filters, delete, modal, export, dept colours.
 * Depends on: utils.js
 */

document.addEventListener('DOMContentLoaded', function () {

    // ── Today count ──────────────────────────────────────────────────────────
    var today     = new Date().toISOString().slice(0, 10);
    var allRows   = document.querySelectorAll('#logs-body tr:not(.no-data)');
    var todayCount = 0;
    allRows.forEach(function (r) {
        if (r.cells[4] && r.cells[4].textContent.includes(today)) todayCount++;
    });
    var statToday = document.getElementById('stat-today');
    if (statToday) statToday.textContent = todayCount;

    // ── Dept colour tags ─────────────────────────────────────────────────────
    document.querySelectorAll('[data-dept-label]').forEach(function (el) {
        var dept  = el.dataset.deptLabel;
        var color = getDeptColor(dept);
        el.style.background  = color.bg;
        el.style.color       = color.text;
        el.style.borderColor = color.border;
    });

    // ── Search + dept filter ─────────────────────────────────────────────────
    var searchInput = document.getElementById('log-search');
    var filterCount = document.getElementById('filter-count');
    var activeDept  = '';

    function applyFilters() {
        var q       = searchInput ? searchInput.value.toLowerCase().trim() : '';
        var visible = 0;

        allRows.forEach(function (row) {
            var matchSearch = !q || row.textContent.toLowerCase().includes(q);
            var matchDept   = !activeDept || row.dataset.dept === activeDept;
            var show        = matchSearch && matchDept;
            row.classList.toggle('hidden', !show);
            if (show) visible++;
        });

        if (filterCount) {
            filterCount.textContent = (q || activeDept)
                ? 'Showing ' + visible + ' of ' + allRows.length + ' records'
                : '';
        }
    }

    if (searchInput) searchInput.addEventListener('input', applyFilters);

    document.querySelectorAll('.dept-pill').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.dept-pill').forEach(function (b) { b.classList.remove('active'); });
            this.classList.add('active');
            activeDept = this.dataset.dept;
            applyFilters();
        });
    });

    // ── Delete student ───────────────────────────────────────────────────────
    window.deleteStudent = function (uid, name, btn) {
        if (!confirm('Delete "' + name + '" and all their records?\n\nThis cannot be undone.')) return;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

        fetch('/admin/delete-student/' + uid, { method: 'POST' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    var row = btn.closest('tr');
                    row.style.transition = 'opacity 0.3s, transform 0.3s';
                    row.style.opacity    = '0';
                    row.style.transform  = 'translateX(20px)';
                    setTimeout(function () { row.remove(); }, 300);
                    showToast(name + ' deleted.', 'info');
                } else {
                    showToast(data.message || 'Delete failed.', 'error');
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-trash"></i>';
                }
            })
            .catch(function () {
                showToast('Server error.', 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-trash"></i>';
            });
    };

    // ── Add student modal ────────────────────────────────────────────────────
    window.openAddModal = function () {
        document.getElementById('add-modal').classList.remove('hidden');
        document.getElementById('m-uid').focus();
    };

    window.closeAddModal = function (e) {
        var overlay = document.getElementById('add-modal');
        if (!e || e.target === overlay) {
            overlay.classList.add('hidden');
            ['m-uid','m-name','m-dept','m-email'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.value = '';
            });
            var errEl = document.getElementById('modal-error');
            if (errEl) errEl.classList.add('hidden');
        }
    };

    window.saveStudent = function () {
        var uid   = document.getElementById('m-uid').value.trim();
        var name  = document.getElementById('m-name').value.trim();
        var dept  = document.getElementById('m-dept').value.trim();
        var email = document.getElementById('m-email').value.trim();
        var errEl = document.getElementById('modal-error');
        var btn   = document.getElementById('modal-save-btn');

        if (!uid || !name || !dept) {
            errEl.textContent = 'ID, name, and department are required.';
            errEl.classList.remove('hidden');
            return;
        }
        errEl.classList.add('hidden');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

        fetch('/admin/add-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: uid, name: name, department: dept, parent_email: email })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                showToast(data.message, 'success');
                closeAddModal();
                setTimeout(function () { window.location.reload(); }, 900);
            } else {
                errEl.textContent = data.message || 'Failed to add student.';
                errEl.classList.remove('hidden');
            }
        })
        .catch(function () {
            errEl.textContent = 'Server error. Please try again.';
            errEl.classList.remove('hidden');
        })
        .finally(function () {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Student';
        });
    };

    // ── CSV export ───────────────────────────────────────────────────────────
    window.exportCSV = function () {
        var rows = document.querySelectorAll('#logs-body tr:not(.no-data):not(.hidden)');
        if (!rows.length) { showToast('No records to export.', 'info'); return; }

        var csv = 'No,Name,User ID,Department,Timestamp,Status\n';
        rows.forEach(function (r, i) {
            var cells  = r.querySelectorAll('td');
            var badge  = r.querySelector('.badge');
            var status = badge ? badge.textContent.trim() : '';
            csv += [
                i + 1,
                '"' + (cells[1] ? cells[1].textContent.trim() : '') + '"',
                '"' + (cells[2] ? cells[2].textContent.trim() : '') + '"',
                '"' + (cells[3] ? cells[3].textContent.trim() : '') + '"',
                '"' + (cells[4] ? cells[4].textContent.trim() : '') + '"',
                '"' + status + '"'
            ].join(',') + '\n';
        });

        var a      = document.createElement('a');
        a.href     = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
        a.download = 'attendance_' + new Date().toISOString().slice(0, 10) + '.csv';
        a.click();
    };

});
