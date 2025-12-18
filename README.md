---
title: Stock Prediction API
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# Stock Prediction ML System

Ringkasan singkat: aplikasi Flask untuk prediksi harga saham (7 hari) menggunakan model terlatih dan data CSV. README ini berfokus pada instruksi instalasi dan cara menjalankan aplikasi secara cepat.

---

## 1) Prasyarat
- Python 3.10+ (Windows/macOS/Linux)
- Git
- DVC (opsional, bila menggunakan remote data)
- (Opsional) Docker, bila ingin menjalankan sebagai container

## 2) Instalasi — lingkungan pengembangan (Windows PowerShell)
1. Clone repo
   ```powershell
   git clone <repo-url>
   cd TML_MLOPS
   ```
2. Buat virtual environment dan aktifkan
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependensi
   ```powershell
   pip install -r requirements.txt
   ```

## 3) Ambil data model / file besar (DVC)
- Jika ingin menggunakan data dan model yang disimpan di dvc oleh pembuat cukup jalankan:
  ```powershell
  dvc pull
  ```
- Jika ingin melakukan download data secara manual , melakukan training, dan menyimpan model jalankan file main_flow.py
  ```powershell
  python -m src.main_flow  
  ```   
- CATATAN : Jika ingin melihat hasil training dan visualisasi metrik training dan akurasi, anda perlu login ke prefect cloud atau set local prefect server 
  ```powershell
  prefect cloud login
  ```  
  ATAU GUNAKAN 

  ```powershell
  prefect server strat
  ```  
   ```powershell
  prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
  ```  


## 4) Menjalankan aplikasi (development)
- Jalankan server Flask (debug mode)
  ```powershell
  python src/app.py
  ```
  Server berjalan di http://localhost:5000

## 5) Menjalankan dengan Docker (opsional)
1. Build image
   ```powershell
   docker build -t stock-prediction:latest .
   ```
2. Run container
   ```powershell
   docker run -p 5000:5000 --env DATA_PATH="data/raw/stock_data.csv" stock-prediction:latest
   ```

## 6) Endpoint & contoh pemakaian
- Health check
  ```bash
  Invoke-RestMethod -Uri 'http://localhost:5000/health' -Method GET
  ```
- Daftar ticker yang tersedia
  ```bash
  Invoke-RestMethod -Uri 'http://localhost:5000/available-tickers' -Method GET
  ```
- Mendapatkan prediksi untuk ticker
  ```bash
  Invoke-RestMethod -Uri 'http://localhost:5000/predict' -Method POST -ContentType 'application/json' -Body '{"ticker":"BBRI.JK","days":7}'
  ```
- Portfolio (POST)
  ```bash
  Invoke-RestMethod -Uri 'http://localhost:5000/portfolio' -Method POST -ContentType 'application/json' -Body '{"positions":[{"ticker":"BBRI.JK","amount":1000000},{"ticker":"BBNI.JK","amount":500000}],"days":7}'
  ```

## 7) Catatan & troubleshooting singkat
- Jika `dvc pull` gagal karena kredensial, itu artinya akses ke drive dimatikan oleh owner. Anda bisa set up sendiri dengan melakukan `dvc init` dan mengikuti langkah lankgah set up yang muncul  atau gunakan data lokal di `data/raw/stock_data.csv` dan model lokal di `model` yang diperoleh dari menjalankan main_flow.py  .
- Jika model untuk ticker tertentu belum tersedia, endpoint `/predict` akan mengembalikan 404 dengan saran untuk men-train model.
- Periksa log aplikasi (console) untuk pesan error dan stacktrace saat debugging.

---
