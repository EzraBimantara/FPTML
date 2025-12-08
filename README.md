---
title: Stock Prediction API
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# Stock Prediction API

This is a Flask-based Stock Prediction API deployed using Docker.

## Endpoints

- `GET  /available-tickers`  : List available tickers"
- `GET /health`: Check API status
- `POST /predict`: Get stock predictions
  - Body: `{"ticker": "BBRI.JK", "days": 7}`