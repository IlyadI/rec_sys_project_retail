# backend/scripts/build_user_purchases.py

import json
from pathlib import Path

import pandas as pd

CSV_PATH = Path("backend/data/OnlineRetail.csv")            # при необходимости поменяй путь
OUT_PATH = Path("backend/data/user_purchases.json")


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {CSV_PATH}")

    print(f"Loading dataset from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, encoding="latin1")

    # Берём нужные колонки
    df = df[["CustomerID", "StockCode", "Quantity", "InvoiceNo"]]

    # Фильтруем: только валидные CustomerID/StockCode
    df = df.dropna(subset=["CustomerID", "StockCode"])

    # Убираем отменённые/возвратные инвойсы (InvoiceNo, начинающийся с 'C')
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df = df[~df["InvoiceNo"].str.startswith("C")]

    # Только положительное количество
    df = df[df["Quantity"] > 0]

    # Приводим к строкам
    df["CustomerID"] = df["CustomerID"].astype(int).astype(str)
    df["StockCode"] = df["StockCode"].astype(str)

    # Делаем список уникальных товаров на пользователя
    df = df.drop_duplicates(subset=["CustomerID", "StockCode"])

    user_purchases = (
        df.groupby("CustomerID")["StockCode"].apply(list).to_dict()
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(user_purchases, f)

    print(
        f"Saved user purchases to {OUT_PATH.resolve()} "
        f"(users: {len(user_purchases)})"
    )


if __name__ == "__main__":
    main()
