from prefect import flow
from src.data_ingestion import ingest_task
from src.model_training import train_model

@flow(name="Stock-Prediction-Pipeline-v1", log_prints=True)
def main_flow(tickers: list = ["BBRI.JK", "BMRI.JK", "BBNI.JK", "BBTN.JK", "BRIS.JK"]):
    
    
    
    csv_path = ingest_task(tickers=tickers)
    
    
    train_params = {'n_estimators': 100, 'max_depth': 10} 
    
    results = []
    for ticker in tickers:
        
        res = train_model(data_path=csv_path, ticker=ticker, params=train_params)
        
        
        if res is not None:
            results.append(res)
        
    print("\n=== PIPELINE SELESAI ===")
    print("Rekapitulasi Rekomendasi AI:")
    
    
    for ticker, signal in results:
        print(f"🎯 {ticker}: {signal}")

if __name__ == "__main__":
    main_flow()