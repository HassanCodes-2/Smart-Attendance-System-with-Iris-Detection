/**
 * charts.js — Admin dashboard charts using Chart.js
 * Reads data from the existing logs table DOM — zero backend changes.
 */

document.addEventListener('DOMContentLoaded', function () {
    if (typeof Chart === 'undefined') return;

    Chart.defaults.color       = '#64748b';
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.font.size   = 12;

    var ACCENT      = '#6366f1';
    var DEPT_COLORS = ['#6366f1','#a855f7','#ec4899','#f59e0b','#22c55e','#0ea5e9','#ef4444','#14b8a6'];

    // Read data straight from the table DOM
    var rows    = document.querySelectorAll('#logs-body tr:not(.no-data)');
    var present = 0, late = 0;
    var deptMap = {}, dayMap = {};

    rows.forEach(function (row) {
        var badge  = row.querySelector('.badge');
        var status = badge ? badge.textContent.trim().toLowerCase() : '';
        if (status.includes('present')) present++;
        if (status.includes('late'))    late++;

        var dept = row.dataset.dept || '';
        if (dept) deptMap[dept] = (deptMap[dept] || 0) + 1;

        var tsCell = row.cells[4];
        if (tsCell) {
            var d = tsCell.textContent.trim().slice(0, 10);
            if (d) dayMap[d] = (dayMap[d] || 0) + 1;
        }
    });

    // Build last-7-days arrays
    var last7 = [], last7Labels = [];
    for (var i = 6; i >= 0; i--) {
        var d = new Date(); d.setDate(d.getDate() - i);
        var key   = d.toISOString().slice(0, 10);
        var label = d.toLocaleDateString(undefined, { weekday:'short', month:'short', day:'numeric' });
        last7.push(dayMap[key] || 0);
        last7Labels.push(label);
    }

    var deptLabels = Object.keys(deptMap);
    var deptCounts = deptLabels.map(function (k) { return deptMap[k]; });

    // Shared tooltip style
    function tooltipDefaults() {
        return {
            backgroundColor: 'rgba(8,13,26,0.92)',
            borderColor: 'rgba(99,102,241,0.3)',
            borderWidth: 1,
            padding: 10,
            titleColor: '#f1f5f9',
            bodyColor: '#94a3b8',
            cornerRadius: 8
        };
    }

    // Chart 1: Donut
    var donutCtx = document.getElementById('chart-donut');
    if (donutCtx) {
        if (present + late > 0) {
            new Chart(donutCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Present','Late'],
                    datasets: [{
                        data: [present, late],
                        backgroundColor: ['rgba(34,197,94,0.75)','rgba(245,158,11,0.75)'],
                        borderColor:     ['#22c55e','#f59e0b'],
                        borderWidth: 2,
                        hoverOffset: 8
                    }]
                },
                options: {
                    cutout: '68%',
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding:16, usePointStyle:true, pointStyleWidth:10 }
                        },
                        tooltip: {
                            ...tooltipDefaults(),
                            callbacks: {
                                label: function (ctx) {
                                    var total = ctx.dataset.data.reduce(function(a,b){return a+b;},0);
                                    var pct   = total ? Math.round((ctx.parsed/total)*100) : 0;
                                    return '  '+ctx.label+': '+ctx.parsed+' ('+pct+'%)';
                                }
                            }
                        }
                    },
                    animation: { animateRotate:true, duration:900 }
                }
            });
        } else {
            donutCtx.parentElement.innerHTML =
                '<p style="text-align:center;color:var(--muted);padding:3rem 0;font-size:0.85rem">No records yet</p>';
        }
    }

    // Chart 2: Horizontal Bar by Department
    var barCtx = document.getElementById('chart-bar');
    if (barCtx) {
        if (deptLabels.length > 0) {
            var bColors = deptLabels.map(function(_,i){ return DEPT_COLORS[i%DEPT_COLORS.length]; });
            new Chart(barCtx, {
                type: 'bar',
                data: {
                    labels: deptLabels,
                    datasets: [{
                        label: 'Check-ins',
                        data: deptCounts,
                        backgroundColor: bColors.map(function(c){ return c+'bb'; }),
                        borderColor: bColors,
                        borderWidth: 2,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    plugins: {
                        legend: { display:false },
                        tooltip: tooltipDefaults()
                    },
                    scales: {
                        x: {
                            grid:  { color:'rgba(255,255,255,0.05)' },
                            ticks: { color:'#64748b', stepSize:1 },
                            beginAtZero: true
                        },
                        y: {
                            grid:  { display:false },
                            ticks: { color:'#94a3b8' }
                        }
                    },
                    animation: { duration:900, easing:'easeOutQuart' }
                }
            });
        } else {
            barCtx.parentElement.innerHTML =
                '<p style="text-align:center;color:var(--muted);padding:3rem 0;font-size:0.85rem">No department data</p>';
        }
    }

    // Chart 3: Line — 7-day trend
    var lineCtx = document.getElementById('chart-line');
    if (lineCtx) {
        new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: last7Labels,
                datasets: [{
                    label: 'Check-ins',
                    data: last7,
                    borderColor: ACCENT,
                    backgroundColor: 'rgba(99,102,241,0.1)',
                    fill: true,
                    tension: 0.42,
                    pointBackgroundColor: ACCENT,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display:false },
                    tooltip: tooltipDefaults()
                },
                scales: {
                    x: {
                        grid:  { color:'rgba(255,255,255,0.04)' },
                        ticks: { color:'#64748b', maxRotation:30 }
                    },
                    y: {
                        grid:  { color:'rgba(255,255,255,0.06)' },
                        ticks: { color:'#64748b', stepSize:1 },
                        beginAtZero: true
                    }
                },
                animation: { duration:1000, easing:'easeOutCubic' }
            }
        });
    }
});
