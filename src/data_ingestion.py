import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from prefect import task


DEFAULT_TICKERS = ["BBRI.JK", "BMRI.JK", "BBNI.JK", "BBTN.JK", "BRIS.JK"]

@task(name="Ingest Data", retries=3, retry_delay_seconds=5)
def ingest_task(tickers=None, output_path="data/raw/stock_data.csv"):
    if tickers is None:
        tickers = DEFAULT_TICKERS
        
    print(f" Memulai Ingestion untuk: {tickers}")
    
    end_date = datetime.today()
    start_date = end_date - timedelta(days=5*365)
    
    all_data = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            df = t.history(start=start_date, end=end_date, auto_adjust=False, actions=True)
            if not df.empty:
                df.reset_index(inplace=True)
                df['Date'] = df['Date'].dt.tz_localize(None)
                df['Ticker'] = ticker
                all_data.append(df)
        except Exception as e:
            print(f" Error downloading {ticker}: {e}")

    if not all_data:
        raise RuntimeError("Data Ingestion Gagal: Tidak ada data yang terunduh.")

    final_df = pd.concat(all_data, ignore_index=True)
    

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path, index=False)
    
    print(f" Data tersimpan di: {output_path}")
    return output_path