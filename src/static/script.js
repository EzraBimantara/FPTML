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
});