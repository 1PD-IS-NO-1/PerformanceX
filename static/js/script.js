document.addEventListener('DOMContentLoaded', function() {
    // Existing performance dashboard elements
    const emailSelector = document.getElementById('email-selector');
    const loadDataBtn = document.getElementById('load-data');
    const getBehaviorBtn = document.getElementById('get-behavior');
    const downloadPdfBtn = document.getElementById('download-pdf');
    const insightsText = document.getElementById('insights-text');
    const behaviorInsights = document.getElementById('behavior-insights');
    
    // Weekly performance elements
    const weekSelector = document.getElementById('week-selector');
    const transferBtn = document.getElementById('transfer-btn');
    const transferResult = document.getElementById('transfer-result');
    
    let currentEmail = '';
    let currentPdfData = '';
    let attendanceTable = null;
    let summaryTable = null;

    // Check if we're on the weekly page
    const isWeeklyPage = document.getElementById('attendance-table') !== null;

    // Initialize DataTables only once
    if (isWeeklyPage) {
        // Destroy existing DataTables instances if they exist
        if ($.fn.DataTable.isDataTable('#attendance-table')) {
            $('#attendance-table').DataTable().destroy();
        }
        if ($.fn.DataTable.isDataTable('#summary-table')) {
            $('#summary-table').DataTable().destroy();
        }

        // Initialize fresh DataTables instances
        attendanceTable = $('#attendance-table').DataTable({
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
            pageLength: 10,
            responsive: true,
            initComplete: function() {
                // Hide loading message after initialization
                $('#attendance-table tbody').html('<tr><td colspan="8" class="text-center">No data available</td></tr>');
            }
        });

        summaryTable = $('#summary-table').DataTable({
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
            pageLength: 10,
            order: [[4, 'desc']],
            responsive: true,
            initComplete: function() {
                // Hide loading message after initialization
                $('#summary-table tbody').html('<tr><td colspan="6" class="text-center">No data available</td></tr>');
            }
        });
    }

    // Existing event listeners
    if (loadDataBtn) loadDataBtn.addEventListener('click', loadPerformanceData);
    if (getBehaviorBtn) getBehaviorBtn.addEventListener('click', getBehavioralInsights);
    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', downloadInsightsPdf);
    
    // Weekly performance event listeners
    if (weekSelector) weekSelector.addEventListener('change', loadWeeklyData);
    if (transferBtn) transferBtn.addEventListener('click', transferAttendance);

    // Existing functions (keep all your existing functions unchanged)
    function loadPerformanceData() {
        currentEmail = emailSelector.value;
        if (!currentEmail) {
            alert('Please select an intern');
            return;
        }

        fetch('/get_performance_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: currentEmail })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            // Render charts
            Plotly.newPlot('bar-chart', JSON.parse(data.bar_graph));
            Plotly.newPlot('pie-chart', JSON.parse(data.pie_graph));
            Plotly.newPlot('radar-chart', JSON.parse(data.radar_chart));
            Plotly.newPlot('timeline-chart', JSON.parse(data.timeline_chart));
            Plotly.newPlot('comparison-chart', JSON.parse(data.comparison_chart));

            // Display insights
            insightsText.textContent = data.insights;
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load performance data');
        });
    }

    function getBehavioralInsights() {
        if (!currentEmail) {
            alert('Please load performance data first');
            return;
        }

        fetch('/get_behavior_insights', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: currentEmail })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            behaviorInsights.textContent = data.insights;
            currentPdfData = data.pdf_data;
            downloadPdfBtn.style.display = 'inline-block';
            downloadPdfBtn.onclick = function() {
                downloadInsightsPdf(data.pdf_data, currentEmail);
            };
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to get behavioral insights');
        });
    }

    function downloadInsightsPdf() {
        if (!currentPdfData) return;
        
        fetch('/download_insights', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                pdf_data: currentPdfData,
                email: currentEmail
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to download');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentEmail}_insights.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to download PDF');
        });
    }

    // Weekly performance functions
    function loadWeeklyData() {
        const weekOption = weekSelector.value;
        showLoading();
        
        fetch('/api/weekly-performance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ week_option: weekOption })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.error) {
                showError(data.error);
            } else {
                updateWeeklyUI(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Failed to load weekly data');
        });
    }

    function showLoading() {
        if (attendanceTable) {
            attendanceTable.clear().draw();
            $('#attendance-table tbody').html('<tr><td colspan="8" class="text-center">Loading data...</td></tr>');
        }
        if (summaryTable) {
            summaryTable.clear().draw();
            $('#summary-table tbody').html('<tr><td colspan="6" class="text-center">Loading data...</td></tr>');
        }
        $('.summary-card .card-value').text('...');
    }

    function showError(message) {
        if (attendanceTable) {
            attendanceTable.clear().draw();
            $('#attendance-table tbody').html(`<tr><td colspan="8" class="text-center text-danger">${message}</td></tr>`);
        }
        if (summaryTable) {
            summaryTable.clear().draw();
            $('#summary-table tbody').html(`<tr><td colspan="6" class="text-center text-danger">${message}</td></tr>`);
        }
        $('.summary-card .card-value').text('N/A');
    }

    function updateWeeklyUI(data) {
        // Update summary cards
        $('#active-interns').text(data.total_interns || 0);
        $('#avg-hours').text((data.avg_hours ? data.avg_hours.toFixed(1) : '0') + ' hrs');
        $('#task-completion').text((data.task_completion ? data.task_completion.toFixed(1) : '0') + '%');

        // Update attendance table
        if (attendanceTable) {
            attendanceTable.clear();
            if (data.attendance_records && data.attendance_records.length > 0) {
                data.attendance_records.forEach(record => {
                    attendanceTable.row.add([
                        record.Email || '',
                        record.Name || '',
                        record.Date || '',
                        record.Present || '',
                        record['Hours Worked'] || '',
                        record['Tasks Assigned'] || '',
                        record['Task Status'] || '',
                        record['Additional Task'] || ''
                    ]);
                });
            } else {
                attendanceTable.row.add(['No data available', '', '', '', '', '', '', '']).draw();
            }
            attendanceTable.draw();
        }

        // Update summary table
        if (summaryTable) {
            summaryTable.clear();
            if (data.summary && data.summary.length > 0) {
                data.summary.forEach(item => {
                    summaryTable.row.add([
                        item.Email || '',
                        item.Name || '',
                        item['Days Present'] || '',
                        item['Total Days'] || '',
                        item['Attendance %'] ? item['Attendance %'].toFixed(1) + '%' : '0%',
                        item['Total Hours Worked'] ? item['Total Hours Worked'].toFixed(1) : '0'
                    ]);
                });
            } else {
                summaryTable.row.add(['No data available', '', '', '', '', '']).draw();
            }
            summaryTable.draw();

            // Apply color gradient
            $('#summary-table tbody td:nth-child(5)').each(function() {
                const text = $(this).text().replace('%', '');
                const value = parseFloat(text) || 0;
                $(this).css('background-color', getColorForValue(value, 0, 100));
            });
        }
    }

    function getColorForValue(value, min, max) {
        const ratio = (value - min) / (max - min);
        const hue = ratio * 120; // 0 (red) to 120 (green)
        return `hsl(${hue}, 100%, 85%)`;
    }

    function transferAttendance() {
        transferResult.innerHTML = '<div class="alert alert-info">Transferring attendance data...</div>';
        
        fetch('/api/transfer-attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.success) {
                transferResult.innerHTML = '<div class="alert alert-success">✅ Attendance transferred to Google Sheet!</div>';
            } else {
                transferResult.innerHTML = `<div class="alert alert-danger">❌ Error: ${data.error || 'Unknown error'}</div>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            transferResult.innerHTML = `<div class="alert alert-danger">❌ Error occurred: ${error.message}</div>`;
        });
    }

    // Initial load for weekly page
    if (weekSelector) {
        loadWeeklyData();
    }
});