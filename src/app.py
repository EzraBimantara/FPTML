import os
import joblib
import pandas as pd
from datetime import timedelta
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Konfig-
MODEL_DIR = os.getenv("MODEL_DIR", "models")
DATA_PATH = os.getenv("DATA_PATH", "data/raw/stock_data.csv")

# Data

def get_latest_market_data_from_csv(ticker, data_path):
   
    try:
        
        if not os.path.exists(data_path):
            print(f"File tidak ditemukan: {data_path}")
            return None, None, None, None
        
        df = pd.read_csv(data_path)
        df['Date'] = pd.to_datetime(df['Date'])
        
        
        df_ticker = df[df['Ticker'] == ticker].copy()
        
        if df_ticker.empty:
            print(f"Ticker {ticker} tidak ditemukan di CSV")
            return None, None, None, None
        
    
        df_ticker = df_ticker.sort_values('Date').reset_index(drop=True)
        
        
        last_date = df_ticker['Date'].iloc[-1]
        last_close = df_ticker['Close'].iloc[-1]
        
        
        feature_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        last_row_features = df_ticker.iloc[[-1]][feature_cols].copy()
        
        
        last_row_features = last_row_features.fillna(method='ffill').fillna(0)
        
        
        history_df = df_ticker.tail(30)[['Date', 'Close']].copy()
        history_df['Date'] = history_df['Date'].dt.strftime('%Y-%m-%d')
        history_prices = history_df['Close'].values.flatten().tolist()
        
        history_final = pd.DataFrame({
            'Date': history_df['Date'].values,
            'Close': history_prices
        })
        
        print(f"✅ Data loaded from CSV: {ticker}")
        print(f"   Last Date: {last_date.strftime('%Y-%m-%d')}")
        print(f"   Last Price: Rp {last_close:,.0f}")
        
        return last_row_features, last_close, last_date, history_final
        
    except Exception as e:
        print(f"❌ Error loading data from CSV: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None

def recursive_forecast(model, last_row_features, current_price, last_date, days=7):
    """
    Forecasting logic - IDENTIK dengan model_training.py
    """
    future_predictions = []
    future_dates = []
    
    current_input = last_row_features.values.copy()
    feature_names = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    curr_date_obj = last_date
    
    for i in range(days):
        # A. Prediksi
        current_input_df = pd.DataFrame(current_input, columns=feature_names)
        pred_price = model.predict(current_input_df)[0]
        
        # B. Bulatkan
        pred_price_rounded = round(pred_price, 0)
        future_predictions.append(pred_price_rounded)
        
        # C. Tanggal
        curr_date_obj = curr_date_obj + timedelta(days=1)
        future_dates.append(curr_date_obj.strftime('%Y-%m-%d'))
        
        # D. Recursive Update (IDENTIK dengan model_training.py)
        current_input[0, 3] = pred_price          # Close
        current_input[0, 0] = pred_price          # Open
        current_input[0, 1] = pred_price * 1.01   # High
        current_input[0, 2] = pred_price * 0.99   # Low
        # Volume tidak diubah
    
    return future_predictions, future_dates

def generate_recommendation(current_price, future_prices):
    """
    Membuat sinyal rekomendasi (IDENTIK dengan model_training.py)
    """
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
        
    return signal, reason

# --- ENDPOINTS ---

@app.route('/')
def index():
    """Homepage dengan UI"""
    try:
        if os.path.exists(DATA_PATH):
            df = pd.read_csv(DATA_PATH)
            tickers = sorted(df['Ticker'].unique().tolist())
        else:
            tickers = []
        
        return render_template('index.html', tickers=tickers)
    except Exception as e:
        return f"Error loading page: {str(e)}", 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    csv_exists = os.path.exists(DATA_PATH)
    return jsonify({
        "status": "healthy", 
        "service": "Stock Prediction API",
        "data_source": "Local CSV",
        "csv_path": DATA_PATH,
        "csv_available": csv_exists
    }), 200

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # 1. Parse Request
        data = request.get_json()
        ticker = data.get('ticker')
        days = data.get('days', 7)
        
        if not ticker:
            return jsonify({"error": "Ticker wajib diisi (misal: BBRI.JK)"}), 400

        print(f"\n{'='*60}")
        print(f"📡 API Request: {ticker} for {days} days")
        print(f"{'='*60}")

        # 2. Load Model
        safe_ticker = ticker.replace(".", "_")
        model_path = os.path.join(MODEL_DIR, f"model_{safe_ticker}.pkl")
        
        if not os.path.exists(model_path):
            return jsonify({
                "error": f"Model untuk {ticker} belum tersedia.",
                "suggestion": "Silakan jalankan training pipeline terlebih dahulu."
            }), 404
            
        model = joblib.load(model_path)
        print(f"✅ Model loaded: {model_path}")
        
        
        input_features, current_price, last_date, history_df = get_latest_market_data_from_csv(
            ticker, DATA_PATH
        )
        
        if input_features is None:
            return jsonify({
                "error": f"Gagal mengambil data untuk {ticker} dari CSV",
                "details": f"Pastikan ticker ada di file: {DATA_PATH}"
            }), 500

        # 4. Forecasting menggunakan fungsi yang IDENTIK
        future_predictions, future_dates = recursive_forecast(
            model,
            input_features,
            current_price,
            last_date,
            days=days
        )
        
        print(f"\n📊 Forecast Results:")
        print(f"   Current Price: Rp {current_price:,.0f}")
        print(f"   {days}-Day Forecast: Rp {future_predictions[-1]:,.0f}")
        print(f"   Change: {((future_predictions[-1] - current_price)/current_price)*100:+.2f}%")

        # 5. Rekomendasi
        signal, reason = generate_recommendation(current_price, future_predictions)
        print(f"   Signal: {signal}")

        # 6. Response JSON
        response = {
            "meta": {
                "ticker": ticker,
                "current_price": float(current_price),
                "last_updated": last_date.strftime('%Y-%m-%d'),
                "prediction_horizon": f"{days} Days",
                "data_source": "Local CSV (stock_data.csv)"
            },
            "chart_data": {
                "history_dates": history_df['Date'].tolist(),
                "history_prices": history_df['Close'].tolist(),
                "forecast_dates": future_dates,
                "forecast_prices": future_predictions
            },
            "forecast_table": [
                {
                    "date": d, 
                    "price": p, 
                    "change": f"{((p - current_price)/current_price)*100:.2f}%"
                } 
                for d, p in zip(future_dates, future_predictions)
            ],
            "recommendation": {
                "signal": signal,
                "reason": reason,
                "action": "BUY" if "BUY" in signal else ("SELL" if "SELL" in signal else "HOLD")
            },
            "model_info": {
                "algorithm": "Random Forest Regressor",
                "features": ["Open", "High", "Low", "Close", "Volume"],
                "note": "Prediksi menggunakan data dari CSV lokal, IDENTIK dengan training pipeline"
            }
        }

        print(f"{'='*60}\n")
        return jsonify(response)

    except Exception as e:
        print(f"\n❌ Server Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/available-tickers', methods=['GET'])
def available_tickers():
    
    try:
        if not os.path.exists(DATA_PATH):
            return jsonify({"error": f"CSV tidak ditemukan: {DATA_PATH}"}), 404
        
        df = pd.read_csv(DATA_PATH)
        tickers = df['Ticker'].unique().tolist()
        
        # Cek model availability
        ticker_info = []
        for ticker in tickers:
            safe_ticker = ticker.replace(".", "_")
            model_path = os.path.join(MODEL_DIR, f"model_{safe_ticker}.pkl")
            model_exists = os.path.exists(model_path)
            
            ticker_info.append({
                "ticker": ticker,
                "model_available": model_exists,
                "status": "✅ Ready" if model_exists else "⚠️ Need Training"
            })
        
        return jsonify({
            "total_tickers": len(tickers),
            "tickers": ticker_info,
            "csv_path": DATA_PATH
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Stock Prediction API Server (CSV-Based)")
    print("="*60)
    print(f"📂 Data Source: {DATA_PATH}")
    print(f"📁 Model Directory: {MODEL_DIR}")
    print("\n📍 Endpoints:")
    print("   - POST /predict            : Get stock prediction")
    print("   - GET  /available-tickers  : List available tickers")
    print("   - GET  /health            : Health check")
    print("="*60 + "\n")
    
    # Validasi file CSV exists
    if not os.path.exists(DATA_PATH):
        print(f"⚠️  WARNING: CSV file not found at {DATA_PATH}")
        print(f"   Run training pipeline first: python main_flow.py\n")
    else:
        df = pd.read_csv(DATA_PATH)
        print(f"✅ CSV loaded: {len(df)} rows, {df['Ticker'].nunique()} tickers\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)