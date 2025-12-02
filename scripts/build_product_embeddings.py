# scripts/build_product_embeddings.py

import os
import json
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set in environment")

BASE_URL = "https://foundation-models.api.cloud.ru/v1"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"

# !!! путь к датасету: оставь тот, который у тебя реально есть
CSV_PATH = Path("backend/data/OnlineRetail.csv")
OUT_PATH = Path("backend/data/product_embeddings.json")

# задержка между запросами, чтобы не спамить API
REQUEST_SLEEP = 0.2  # секунды


def main():
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {CSV_PATH}")

    print(f"Loading dataset from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, encoding="latin1")

    # Берём уникальные товары: product_id + description
    df = df[["StockCode", "Description"]].dropna()
    df = df.drop_duplicates(subset=["StockCode"])
    df = df.rename(columns={"StockCode": "product_id"})

    products = []
    for _, row in df.iterrows():
        pid = str(row["product_id"])
        desc = str(row["Description"]).strip()
        if not desc:
            continue
        products.append({"product_id": pid, "description": desc})

    print(f"Unique products to embed: {len(products)}")

    result: dict[str, dict] = {}

    for i, p in enumerate(products, start=1):
        pid = p["product_id"]
        desc = p["description"]

        print(f"[{i}/{len(products)}] Embedding product {pid!r}")

        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[desc],  # один текст = один запрос
            )
            emb = response.data[0].embedding
        except Exception as e:
            # Логируем ошибку, но не падаем
            print(f"  -> error for product {pid}: {e}")
            continue

        result[pid] = {
            "product_id": pid,
            "description": desc,
            "embedding": emb,
        }

        # Чуть притормозим между запросами
        time.sleep(REQUEST_SLEEP)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f)

    print(
        f"Saved product embeddings for {len(result)} products "
        f"to {OUT_PATH.resolve()}"
    )


if __name__ == "__main__":
    main()
