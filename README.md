# OnlineRetail LLM Recommender — Retail Prototype
A lightweight, realistic retail storefront prototype that demonstrates:
- **Product recommendations** from real customer purchase history (OnlineRetail dataset)
- **LLM explanations** for “why this item was recommended” (shown as tooltips in UI)
- **Customer switcher** to showcase different recommendation sets per user
The frontend is served by FastAPI at:  
`/retail_shop`
## Features
- **Previous Purchases block** — shows items a customer bought before
- **Frequently Bought Together** — item–item recommendations
- **Cart Add-ons** — cart-aware suggestions based on past baskets
- **Personalized Feed** — Top-N products for selected customer
- **LLM Tooltips** — hover “?” to see natural-language explanation
## Tech Stack
- **Backend:** FastAPI, Uvicorn
- **Recommendations:** precomputed item neighbors + user purchases (JSON)
- **LLM:** Cloud.ru Foundation Models (OpenAI-compatible API)
- **Frontend:** Vanilla HTML/CSS/JS served by FastAPI
# Setup
## 1) Create & activate virtual environment
Windows

python -m venv .venv
.venv\Scripts\activate

Linux / macOS

python3 -m venv .venv
source .venv/bin/activate

## 2) Install dependencies
pip install -r requirements.txt

# Configuration (API key)
The LLM client uses an OpenAI-compatible API (Cloud.ru Foundation Models).
Create a .env file in the project root and add your credentials:
API_KEY=YOUR_KEY_HERE

# Run locally
From the project root: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
## Open in browser:
- Storefront UI: http://127.0.0.1:8000/retail_shop
- Swagger API docs: http://127.0.0.1:8000/docs

# Notes
- Recommendations are precomputed from the dataset and stored in JSON files.
- Explanations are generated on request by the LLM endpoint and shown as tooltips.
- The customer dropdown only lists users who have purchase history.
