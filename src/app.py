import os
import joblib
import subprocess
import pandas as pd
from datetime import timedelta
from flask import Flask, request, jsonify, render_template

def init_dvc_runtime():
    """
    Mendownload data terbaru dari DVC (Google Drive) saat aplikasi Start-up.
    """
    print("\n🔄 [INIT] Memulai DVC Runtime Pull...")
    
    
    creds_content = os.getenv("GDRIVE_CREDENTIALS_DATA")
    
    if not creds_content:
        print("⚠️  Warning: Secret GDRIVE_CREDENTIALS_DATA tidak ditemukan.")
        print("    Menggunakan data lokal yang sudah ada (jika tersedia).")
        return

    try:
        
        creds_path = "gdrive_user_credentials.json"
        with open(creds_path, "w") as f:
            f.write(creds_content)
        
        
        commands = [
            
            ["dvc", "remote", "modify", "--local", "gdrive_storage", "--unset", "gdrive_use_service_account"],
            
            ["dvc", "remote", "modify", "--local", "gdrive_storage", "gdrive_user_credentials_file", creds_path],
            
            ["dvc", "pull"] 
        ]

        for cmd in commands:
            subprocess.run(cmd, check=True)
            
        print("✅ [INIT] DVC Pull Berhasil! Data terbaru siap digunakan.")
        
        if os.path.exists(creds_path):
            os.remove(creds_path)

    except Exception as e:
        print(f"❌ [INIT] Gagal melakukan DVC Pull: {e}")

init_dvc_runtime()

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
        signal = "STRONG BUY"
        reason = f"Potensi Profit: +{upside:.2f}% dalam 7 hari."
    elif downside < -2.0:
        signal = "STRONG SELL"
        reason = f"Risiko Jatuh: {downside:.2f}% dalam 7 hari."
    else:
        signal = "WAIT & HOLD"
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
    


@app.route('/portfolio', methods=['POST'])
def portfolio():
    """API endpoint to evaluate a portfolio over the next N days.
    Request JSON: { "positions": [{"ticker": "BBRI.JK", "amount": 1000000}, ...], "days": 7 }
    Response: daily breakdown + per-ticker forecasts and summary totals
    """
    try:
        payload = request.get_json() or {}
        positions = payload.get('positions', [])
        days = int(payload.get('days', 7))

        if not positions or not isinstance(positions, list):
            return jsonify({"error": "Request must include 'positions' as a non-empty list."}), 400

        summary = {}
        total_current_value = 0.0
        dates = None
        per_ticker = {}

        for pos in positions:
            ticker = pos.get('ticker')
            amount = float(pos.get('amount', 0) or 0)

            if not ticker or amount <= 0:
                return jsonify({"error": "Each position must include a valid 'ticker' and positive 'amount'.", "position": pos}), 400

            input_features, current_price, last_date, history_df = get_latest_market_data_from_csv(ticker, DATA_PATH)
            if input_features is None:
                return jsonify({"error": f"Ticker {ticker} not found in data."}), 400

            
            shares = float(amount) / float(current_price) if float(current_price) > 0 else 0.0

            
            safe_ticker = ticker.replace('.', '_')
            model_path = os.path.join(MODEL_DIR, f"model_{safe_ticker}.pkl")

            if os.path.exists(model_path):
                model = joblib.load(model_path)
                forecast_prices, forecast_dates = recursive_forecast(model, input_features, current_price, last_date, days=days)
            else:
                
                hist_prices = history_df['Close'].astype(float).tolist()
                if len(hist_prices) >= 2:
                    import numpy as _np
                    x = _np.arange(len(hist_prices))
                    y = _np.array(hist_prices)
                    coeff = _np.polyfit(x, y, 1)
                    slope = coeff[0]
                    forecast_prices = []
                    for i in range(1, days + 1):
                        forecast_val = y[-1] + slope * i
                        forecast_prices.append(round(float(forecast_val), 0))
                else:
                    forecast_prices = [round(current_price, 0)] * days

                forecast_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, days + 1)]

            # Per-day value for this position
            forecast_values = [round(shares * float(p), 2) for p in forecast_prices]
            current_value = round(shares * float(current_price), 2)
            total_current_value += current_value

            per_ticker[ticker] = {
                'ticker': ticker,
                'investment': round(amount, 2),
                'shares': round(shares, 8),
                'current_price': float(current_price),
                'current_value': current_value,
                'forecast_dates': forecast_dates,
                'forecast_prices': [float(p) for p in forecast_prices],
                'forecast_values': forecast_values
            }

            dates = forecast_dates

        
        total_per_day = [0.0 for _ in range(days)]
        for t in per_ticker.values():
            for i, v in enumerate(t['forecast_values']):
                total_per_day[i] += v

        total_projected_end = total_per_day[-1] if total_per_day else total_current_value
        total_change = round(total_projected_end - total_current_value, 2)
        total_change_pct = round((total_change / total_current_value * 100) if total_current_value > 0 else 0.0, 2)

        daily_breakdown = [{'date': d, 'total': round(v, 2)} for d, v in zip(dates, total_per_day)]

        
        daily_breakdown_horizontal = {
            'dates': dates,
            'totals': [round(v, 2) for v in total_per_day]
        }

        
        try:
            print('\n' + '='*60)
            print('PORTFOLIO SUMMARY')
            print(f"  Total Investasi Saat Ini: Rp {total_current_value:,.2f}")
            print(f"  Estimasi Total (akhir {days} hari): Rp {total_projected_end:,.2f}")
            print(f"  Return (Rp): {total_change:,.2f}  |  Percent: {total_change_pct:+.2f}%")

            print('\nDAILY BREAKDOWN (horizontal, chunked)')
            dates = daily_breakdown_horizontal['dates']
            totals = daily_breakdown_horizontal['totals']

            
            chunk_size = 6
            lines = []
            for i in range(0, len(dates), chunk_size):
                d_chunk = dates[i:i+chunk_size]
                t_chunk = totals[i:i+chunk_size]
                dates_line = ' | '.join(d_chunk)
                values_line = ' | '.join([f"Rp {v:,.2f}" for v in t_chunk])
                print('Dates : ' + dates_line)
                print('Totals: ' + values_line)

                
                lines.append(('Dates : ' + dates_line, 'Totals: ' + values_line))

            print('='*60 + '\n')

            
            parts = []
            for dl, vl in lines:
                parts.append(dl)
                parts.append(vl)
            daily_str = '\n'.join(parts)
        except Exception:
            
            daily_str = ''
            pass

        response = {
            'meta': {
                'days': days,
                'total_current': round(total_current_value, 2),
                'total_projected_end': round(total_projected_end, 2),
                'total_change': total_change,
                'total_change_pct': total_change_pct
            },
            'positions': list(per_ticker.values()),
            'daily_breakdown': daily_breakdown,
            'daily_breakdown_horizontal': daily_breakdown_horizontal,
            'daily_breakdown_str': daily_str
        }

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error', 'details': str(e)}), 500


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
    print("   - POST /portfolio            : Get live prediction for portfolio")
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