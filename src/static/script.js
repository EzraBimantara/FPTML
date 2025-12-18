let priceChart = null;

// Form submission handler
document.getElementById('predictionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const ticker = document.getElementById('ticker').value;
    
    if (!ticker) {
        alert('Pilih ticker saham terlebih dahulu!');
        return;
    }
    
    // Show loading state
    document.getElementById('loading').classList.add('show');
    document.getElementById('predictBtn').disabled = true;
    document.getElementById('resultPlaceholder').style.display = 'none';
    document.getElementById('predictionResult').classList.remove('show');
    
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                ticker: ticker,
                days: 7  // Fixed 7 days
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data);
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
        console.error('Fetch error:', error);
    } finally {
        document.getElementById('loading').classList.remove('show');
        document.getElementById('predictBtn').disabled = false;
    }
});

function displayResults(data) {
    const result = document.getElementById('predictionResult');
    result.classList.add('show');
    
    // Signal Card
    const signal = data.recommendation.signal;
    const signalCard = document.getElementById('signalCard');
    signalCard.textContent = signal + ' - ' + data.recommendation.reason;
    
    if (signal.includes('BUY')) {
        signalCard.className = 'signal-card signal-buy';
    } else if (signal.includes('SELL')) {
        signalCard.className = 'signal-card signal-sell';
    } else {
        signalCard.className = 'signal-card signal-hold';
    }
    
    // Stats boxes
    document.getElementById('currentPrice').textContent = 
        'Rp ' + data.meta.current_price.toLocaleString('id-ID');
    
    const lastForecast = data.forecast_table[data.forecast_table.length - 1];
    document.getElementById('futurePrice').textContent = 
        'Rp ' + lastForecast.price.toLocaleString('id-ID');
    
    const changeValue = lastForecast.change;
    const changeElement = document.getElementById('priceChange');
    changeElement.textContent = changeValue;
    changeElement.className = 'value ' + (changeValue.startsWith('+') ? 'price-up' : 'price-down');
    
    // Update chart
    updateChart(data);
    
    // Update table
    updateTable(data);
}

function updateChart(data) {
    const ctx = document.getElementById('priceChart');
    
    // Destroy previous chart if exists
    if (priceChart) {
        priceChart.destroy();
    }
    
    // Combine dates
    const allDates = [...data.chart_data.history_dates, ...data.chart_data.forecast_dates];
    
    // Prepare datasets
    const historyData = data.chart_data.history_prices;
    const forecastData = new Array(historyData.length).fill(null)
        .concat(data.chart_data.forecast_prices);
    
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Harga Historis',
                    data: historyData.concat(new Array(data.chart_data.forecast_prices.length).fill(null)),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 2,
                    pointHoverRadius: 5
                },
                {
                    label: 'Prediksi 7 Hari',
                    data: forecastData,
                    borderColor: '#eb3349',
                    backgroundColor: 'rgba(235, 51, 73, 0.1)',
                    tension: 0.4,
                    borderDash: [5, 5],
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += 'Rp ' + context.parsed.y.toLocaleString('id-ID');
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return 'Rp ' + value.toLocaleString('id-ID');
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function updateTable(data) {
    const tbody = document.getElementById('forecastBody');
    tbody.innerHTML = '';
    
    data.forecast_table.forEach(row => {
        const tr = document.createElement('tr');
        const changeClass = row.change.startsWith('+') ? 'price-up' : 'price-down';
        
        tr.innerHTML = `
            <td>${row.date}</td>
            <td>Rp ${row.price.toLocaleString('id-ID')}</td>
            <td class="${changeClass}">${row.change}</td>
        `;
        
        tbody.appendChild(tr);
    });
}

// Auto-refresh tickers on page load (optional)
window.addEventListener('DOMContentLoaded', () => {
    console.log('Stock Prediction System loaded');
    console.log('Ready to predict!');

    // Ensure single tab visible on load
    switchTab('single');
});

// Tab switch helper
function switchTab(tabName) {
    // Update button active state
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Show/hide contents
    document.querySelectorAll('.tab-content').forEach(el => {
        if (el.id === tabName + '-tab') {
            el.style.display = '';
            el.classList.add('active');
            if (tabName === 'portfolio') {
                // ensure at least one input row
                const inputs = document.getElementById('portfolioInputs');
                if (inputs && inputs.children.length === 0) addPortfolioRow();
                // refresh ticker options to prevent duplicates
                updateTickerOptions();
            }
        } else {
            el.style.display = 'none';
            el.classList.remove('active');
        }
    });
}

// ====== Portfolio UI ======
let portfolioChart = null;

function getSelectedTickers() {
    return Array.from(document.querySelectorAll('#portfolioInputs select'))
        .map(s => s.value)
        .filter(Boolean);
}

function updateAddButtonState() {
    const addBtn = document.getElementById('addPortfolioBtn');
    if (!addBtn) return;
    const selected = getSelectedTickers();
    addBtn.disabled = (selected.length >= AVAILABLE_TICKERS.length);
}

function updateTickerOptions() {
    const selects = Array.from(document.querySelectorAll('#portfolioInputs select'));
    const selected = getSelectedTickers();

    selects.forEach(sel => {
        const current = sel.value;
        sel.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = '-- Pilih Saham --';
        sel.appendChild(defaultOpt);

        AVAILABLE_TICKERS.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t;
            opt.textContent = t;
            // disable if selected in another row
            if (t !== current && selected.includes(t)) {
                opt.disabled = true;
                opt.textContent = t + ' (dipilih)';
            }
            sel.appendChild(opt);
        });

        sel.value = current;
    });

    updateAddButtonState();
}

function addPortfolioRow() {
    const container = document.getElementById('portfolioInputs');

    // Prevent adding more rows than available unique tickers
    const available = AVAILABLE_TICKERS.filter(t => !getSelectedTickers().includes(t));
    if (available.length === 0) {
        alert('Semua ticker sudah dipilih. Hapus baris yang ada untuk menambahkan lainnya.');
        return;
    }

    const row = document.createElement('div');
    row.className = 'portfolio-row';

    const select = document.createElement('select');
    select.className = 'form-control';
    select.addEventListener('change', updateTickerOptions);

    const defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = '-- Pilih Saham --';
    select.appendChild(defaultOpt);

    available.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        select.appendChild(opt);
    });

    const input = document.createElement('input');
    input.type = 'number';
    input.placeholder = 'Jumlah Investasi (Rp)';
    input.min = 0;
    input.className = 'form-control';

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn-outline';
    removeBtn.textContent = 'Hapus';
    removeBtn.onclick = () => { row.remove(); updateTickerOptions(); };

    row.appendChild(select);
    row.appendChild(input);
    row.appendChild(removeBtn);

    container.appendChild(row);

    updateTickerOptions();
}

async function calculatePortfolio() {
    const rows = Array.from(document.querySelectorAll('#portfolioInputs .portfolio-row'));
    const positions = [];

    for (const r of rows) {
        const ticker = r.querySelector('select').value;
        const amount = parseFloat(r.querySelector('input').value || 0);
        if (!ticker || amount <= 0) continue;
        positions.push({ ticker, amount });
    }

    // Prevent duplicates as a safety check
    const tickers = positions.map(p => p.ticker);
    const unique = [...new Set(tickers)];
    if (unique.length !== tickers.length) {
        alert('Duplikat ticker terdeteksi. Pastikan setiap baris memilih ticker yang berbeda.');
        return;
    }

    if (positions.length === 0) {
        alert('Tambahkan minimal satu saham dengan jumlah investasi yang valid');
        return;
    }

    // Show loading
    document.getElementById('portfolioLoading').classList.add('show');

    try {
        const resp = await fetch('/portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positions, days: 7 })
        });

        const data = await resp.json();
        if (!resp.ok) {
            alert('Error: ' + (data.error || 'Unknown'));
            return;
        }

        renderPortfolioResults(data);

    } catch (err) {
        console.error(err);
        alert('Terjadi kesalahan saat menghitung portfolio');
    } finally {
        document.getElementById('portfolioLoading').classList.remove('show');
    }
}

function renderPortfolioResults(data) {
    // Summary
    document.getElementById('totalCurrent').textContent = 'Rp ' + data.meta.total_current.toLocaleString('id-ID');
    document.getElementById('totalProjected').textContent = 'Rp ' + data.meta.total_projected_end.toLocaleString('id-ID');
    const change = data.meta.total_change >= 0 ? ('+' + data.meta.total_change) : (data.meta.total_change);
    const changeEl = document.getElementById('totalChange');
    changeEl.textContent = change + ' (' + (data.meta.total_change_pct) + '%)';
    changeEl.className = 'value ' + (data.meta.total_change >= 0 ? 'price-up' : 'price-down');

    // Per-ticker table
    const tbody = document.getElementById('portfolioTableBody');
    tbody.innerHTML = '';
    data.positions.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${p.ticker}</td>
            <td>Rp ${p.investment.toLocaleString('id-ID')}</td>
            <td>Rp ${p.forecast_values[p.forecast_values.length - 1].toLocaleString('id-ID')}</td>
            <td>${p.shares}</td>
        `;
        tbody.appendChild(tr);
    });

    // Daily breakdown table
    const dailyBody = document.getElementById('portfolioDailyBody');
    dailyBody.innerHTML = '';
    const chartLabels = [];
    const chartValues = [];

    data.daily_breakdown.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${d.date}</td>
            <td>Rp ${Math.round(d.total).toLocaleString('id-ID')}</td>
        `;
        dailyBody.appendChild(tr);
        chartLabels.push(d.date);
        chartValues.push(d.total);
    });

    // Draw chart
    const ctx = document.getElementById('portfolioChart');
    if (portfolioChart) portfolioChart.destroy();

    portfolioChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Total Portfolio (Rp)',
                data: chartValues,
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46,204,113,0.08)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: { tooltip: { callbacks: { label: (ctx) => 'Rp ' + Math.round(ctx.parsed.y).toLocaleString('id-ID') } } },
            scales: { y: { ticks: { callback: v => 'Rp ' + Math.round(v).toLocaleString('id-ID') } } }
        }
    });

    // Show result
    const result = document.getElementById('portfolioResult');
    result.classList.add('show');
}