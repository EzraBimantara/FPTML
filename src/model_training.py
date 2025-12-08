import joblib
import os
import uuid
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import io
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from prefect import task, flow
from prefect.artifacts import create_markdown_artifact

# Set Style agar visualisasi terlihat modern
plt.style.use('ggplot')

DATA_PATH = r"data/raw/stock_data.csv"
TARGET_TICKERS = ["BBRI.JK", "BMRI.JK", "BBNI.JK", "BBTN.JK", "BRIS.JK"]

def prepare_data(df, ticker):
    data = df[df['Ticker'] == ticker].copy()
    data = data.sort_values('Date')
    features = ['Open', 'High', 'Low', 'Close', 'Volume']
    data['Target'] = data['Close'].shift(-1)
    
    # Simpan data terakhir untuk input prediksi
    last_row = data.iloc[[-1]][features].copy()
    
    data = data.dropna()
    return data[features], data['Target'], data['Date'], last_row

def plot_to_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()
    return image_base64

def generate_recommendation(current_price, future_prices):
    max_price = max(future_prices)
    min_price = min(future_prices)
    
    upside = (max_price - current_price) / current_price * 100
    downside = (min_price - current_price) / current_price * 100
    
    if upside > 2.0:
        signal = "🟢 STRONG BUY"
        reason = f"Potensi Profit: +{upside:.2f}% dalam 7 hari."
    elif downside < -2.0:
        signal = "🔴 STRONG SELL"
        reason = f"Risiko Jatuh: {downside:.2f}% dalam 7 hari."
    else:
        signal = "⚪ WAIT & HOLD"
        reason = "Pasar Sideways (Datar), tunggu sinyal lebih kuat."
        
    return signal, reason, upside, downside

@task(name="Train & Forecast")
def train_model(data_path, ticker, params):
    print(f"🚀 Processing: {ticker}...")
    
    df_raw = pd.read_csv(data_path)
    df_raw['Date'] = pd.to_datetime(df_raw['Date'])
    
    X, y, dates, last_row_features = prepare_data(df_raw, ticker)
    
    if len(X) < 50:
        print(f"Skipping {ticker} (Data kurang)")
        return None

    # --- 1. TRAINING ---
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    dates_test = dates.iloc[split_idx:]
    
    model = RandomForestRegressor(random_state=42, **params)
    model.fit(X_train, y_train)
    
    # Evaluasi
    predictions = model.predict(X_test)
    mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
    r2 = r2_score(y_test, predictions)
    
    # --- 2. FORECASTING MASA DEPAN (7 HARI) ---
    future_days = 7
    future_predictions = []
    future_dates = []
    
    current_input = last_row_features.values
    feature_names = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    last_real_date = df_raw[df_raw['Ticker'] == ticker]['Date'].iloc[-1]
    last_real_price = df_raw[df_raw['Ticker'] == ticker]['Close'].iloc[-1]
    
    for i in range(future_days):
        current_input_df = pd.DataFrame(current_input, columns=feature_names)
        pred_price = model.predict(current_input_df)[0]
        pred_price_rounded = round(pred_price, 0)  # ✅ DI-ROUND!
        future_predictions.append(pred_price_rounded)
        
        
        next_date = last_real_date + timedelta(days=i+1)
        future_dates.append(next_date)
        
        # Recursive update: Close hari ini jadi input besok
        current_input[0, 3] = pred_price # Update Close
        current_input[0, 0] = pred_price # Asumsi Open = Close sebelumnya
        current_input[0, 1] = pred_price * 1.01   # High ✅
        current_input[0, 2] = pred_price * 0.99

    signal, reason, upside, downside = generate_recommendation(last_real_price, future_predictions)

    # ==========================================
    # 📊 VISUALISASI UTAMA (4 CHARTS)
    # ==========================================

    # 1. FORECAST CHART (Untuk End User - Fokus Tren)
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    # Plot history (zoom in 45 hari terakhir)
    ax1.plot(dates_test[-45:], y_test[-45:], label='Harga Historis', color='#34495e', linewidth=2)
    # Plot forecast
    ax1.plot(future_dates, future_predictions, label='Prediksi AI (7 Hari)', color='#e74c3c', marker='o', linestyle='--', linewidth=2)
    # Highlight area forecast
    ax1.fill_between(future_dates, min(future_predictions), max(future_predictions), color='#e74c3c', alpha=0.1)
    
    ax1.set_title(f"PROYEKSI HARGA: {ticker}", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Tanggal")
    ax1.set_ylabel("Harga (Rp)")
    ax1.legend()
    chart_forecast = plot_to_base64(fig1)
    plt.close(fig1)

    # 2. FEATURE IMPORTANCE (Untuk Data Engineer - Explainability)
    # Menjelaskan KENAPA model memprediksi demikian
    importances = model.feature_importances_
    indices = np.argsort(importances)
    
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.barh(range(len(indices)), importances[indices], color='#2ecc71', align='center')
    ax2.set_yticks(range(len(indices)))
    ax2.set_yticklabels([feature_names[i] for i in indices])
    ax2.set_xlabel('Tingkat Kepentingan (Importance)')
    ax2.set_title('Faktor Apa yang Paling Mempengaruhi AI?')
    chart_features = plot_to_base64(fig2)
    plt.close(fig2)

    # 3. ACTUAL VS PREDICTED (Untuk Validasi - Trust)
    # Membuktikan akurasi model di masa lalu
    fig3, ax3 = plt.subplots(figsize=(6, 6))
    ax3.scatter(y_test, predictions, alpha=0.5, color='#9b59b6')
    
    # Garis diagonal sempurna
    lims = [np.min([ax3.get_xlim(), ax3.get_ylim()]), np.max([ax3.get_xlim(), ax3.get_ylim()])]
    ax3.plot(lims, lims, 'r-', alpha=0.75, zorder=0, linestyle='dashed')
    
    ax3.set_xlabel('Harga Sebenarnya')
    ax3.set_ylabel('Prediksi AI')
    ax3.set_title(f'Uji Validitas Model (R2 Score: {r2:.2f})')
    chart_scatter = plot_to_base64(fig3)
    plt.close(fig3)

    # 4. RESIDUALS / ERROR (Untuk Debugging)
    # Memastikan model tidak bias (error harus tersebar acak di sekitar 0)
    residuals = y_test - predictions
    fig4, ax4 = plt.subplots(figsize=(8, 3))
    ax4.plot(dates_test, residuals, color='#e67e22', linewidth=1)
    ax4.axhline(0, color='black', linestyle='--')
    ax4.set_title('Analisis Error (Residuals) Sepanjang Waktu')
    ax4.set_ylabel('Selisih (Rp)')
    chart_residuals = plot_to_base64(fig4)
    plt.close(fig4)

    # ==========================================
    # 📝 REPORTING (MARKDOWN ARTIFACT)
    # ==========================================
    
    forecast_rows = ""
    for d, p in zip(future_dates, future_predictions):
        d_str = d.strftime('%d-%b-%Y')
        trend_icon = "📈 NAIK" if p > last_real_price else "📉 TURUN"
        diff = p - last_real_price
        color = "green" if diff > 0 else "red"
        forecast_rows += f"| {d_str} | **Rp {p:,.0f}** | <span style='color:{color}'>{trend_icon} (Rp {diff:+,.0f})</span> |\n"

    markdown_report = f"""
# 🚀 Analisis Cerdas: {ticker}

### Rekomendasi AI: **{signal}**
> **"{reason}"**

---

## 1. 🔮 Prediksi Minggu Depan (Untuk Investor)
Harga Saat Ini: **Rp {last_real_price:,.0f}**

| Tanggal | Prediksi Harga | Tren vs Hari Ini |
|:--------|:---------------|:-----------------|
{forecast_rows}

**Visualisasi Tren:**
![Forecast Chart](data:image/png;base64,{chart_forecast})

---

## 2. 🧠 Mengapa AI Memprediksi Demikian? (Explainability)
Grafik ini menunjukkan data pasar apa yang paling diperhatikan oleh Robot saat mengambil keputusan.
![Features](data:image/png;base64,{chart_features})

---

## 3. 🛡️ Uji Kelayakan Model (Untuk Engineer)
Seberapa akurat model ini saat diuji dengan data masa lalu?

| Metric | Nilai | Status |
|:-------|:------|:-------|
| **MAPE (Error)** | `{mape:.2f}%` | {'✅ Sangat Baik' if mape < 2 else '⚠️ Perlu Tuning'} |
| **R2 Score** | `{r2:.2f}` | (Mendekati 1.0 = Sempurna) |

**Sebaran Akurasi (Titik harus di garis merah):**
![Scatter](data:image/png;base64,{chart_scatter})

**Stabilitas Error (Harus acak di garis 0):**
![Residuals](data:image/png;base64,{chart_residuals})
    """
    
    create_markdown_artifact(
        key=f"analysis-{ticker.lower().replace('.', '-')}-{str(uuid.uuid4())[:8]}",
        markdown=markdown_report,
        description=f"{signal} for {ticker}"
    )
    
    # Simpan Model
    model_dir = os.path.abspath("models")
    os.makedirs(model_dir, exist_ok=True)
    safe_ticker_name = ticker.replace(".", "_")
    model_filename = os.path.join(model_dir, f"model_{safe_ticker_name}.pkl")
    joblib.dump(model, model_filename)
    print(f"💾 Model Saved: {model_filename}")

@flow(name="Stock-Prediction-System")
def main_flow():
    # Parameter sedikit lebih kompleks untuk hasil lebih baik
    params = {
        'n_estimators': 200, 
        'max_depth': 15,
        'min_samples_split': 5
    }
    
    print("\n=== MULAI ANALISIS PASAR ===")
    for ticker in TARGET_TICKERS:
        train_model(DATA_PATH, ticker, params)

if __name__ == "__main__":
    main_flow()