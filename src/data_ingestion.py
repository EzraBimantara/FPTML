import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURASI ---
BASE_DIR = r"C:\Users\HP\TML_MLOPS"
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "stock_data.csv")

# Daftar Bank BUMN (Himbara + Syariah)
TICKERS = ["BBRI.JK", "BMRI.JK", "BBNI.JK", "BBTN.JK", "BRIS.JK"]

def download_data():
    print(f">> Memulai proses ingestion untuk {len(TICKERS)} saham...")
    
    # Hitung tanggal 5 tahun lalu dari hari ini
    end_date = datetime.today()
    start_date = end_date - timedelta(days=5*365)
    
    all_data = []

    for ticker in TICKERS:
        print(f"   Downloading: {ticker}...")
        
        # Menggunakan Ticker object untuk akses actions (Dividends/Splits) lebih akurat
        t = yf.Ticker(ticker)
        
        # auto_adjust=False agar kita dapat OHLC mentah + Adj Close terpisah
        # actions=True untuk memastikan Dividends & Splits terambil
        df = t.history(start=start_date, end=end_date, auto_adjust=False, actions=True)
        
        if df.empty:
            print(f"   !! Peringatan: Data kosong untuk {ticker}")
            continue
            
        # Bersihkan Index Tanggal
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.tz_localize(None)
        
        # Tambah kolom nama saham (PENTING untuk membedakan data)
        df['Ticker'] = ticker
        
        all_data.append(df)

    if not all_data:
        print("!! Gagal: Tidak ada data yang berhasil diunduh.")
        return

    # Gabungkan semua data bank menjadi satu DataFrame panjang
    final_df = pd.concat(all_data, ignore_index=True)

    # Pastikan kolom yang diminta ada & urutannya rapi
    expected_cols = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
    
    # Filter hanya kolom yang tersedia (jaga-jaga jika ada yang hilang)
    cols_to_save = [c for c in expected_cols if c in final_df.columns]
    final_df = final_df[cols_to_save]

    # Simpan ke CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    final_df.to_csv(OUTPUT_FILE, index=False)
    
    print(f">> SUKSES! Data {len(final_df)} baris tersimpan di: {OUTPUT_FILE}")
    print(f">> Periode: {start_date.date()} s/d {end_date.date()}")

if __name__ == "__main__":
    download_data()