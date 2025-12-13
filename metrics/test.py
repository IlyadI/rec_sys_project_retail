import json
import numpy as np
from pathlib import Path
from tqdm import tqdm

DATA_DIR = Path("backend/data")


def load_product_embeddings():
    path = DATA_DIR / "product_embeddings.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # product_id -> (description, vector)
    embeddings = {}
    for pid, obj in data.items():
        vec = np.array(obj["embedding"], dtype=np.float32)
        # нормализуем
        norm = np.linalg.norm(vec) + 1e-8
        embeddings[pid] = vec / norm
    return embeddings


def load_user_purchases():
    path = DATA_DIR / "user_purchases.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_at_k(k: int = 10, max_users: int | None = 5000):
    prod_emb = load_product_embeddings()
    user_pur = load_user_purchases()

    # заранее подготовим матрицу всех эмбеддингов
    all_pids = list(prod_emb.keys())
    all_mat = np.stack([prod_emb[pid] for pid in all_pids], axis=0)  # [N_items, 1024]

    hits = 0
    total = 0

    users = list(user_pur.keys())
    if max_users is not None:
        users = users[:max_users]

    for user_id in tqdm(users, desc=f"Eval Recall@{k}"):
        items = user_pur[user_id]
        if len(items) < 2:
            continue

        # простой split: последний товар как тест
        test_item = items[-1]
        train_items = items[:-1]

        # у пользователя может быть товар, которого нет в эмбеддингах
        train_vecs = [prod_emb[pid] for pid in train_items if pid in prod_emb]
        if not train_vecs or test_item not in prod_emb:
            continue

        # user embedding = среднее по train-товарам
        user_vec = np.mean(train_vecs, axis=0)
        user_vec = user_vec / (np.linalg.norm(user_vec) + 1e-8)

        # косинусное сходство со всеми товарами
        sims = all_mat @ user_vec  # [N_items]
        # запрещаем рекомендовать то, что уже куплено
        bought_idx = {all_pids.index(pid) for pid in train_items if pid in prod_emb}
        sims[list(bought_idx)] = -1e9

        # берём top-K индексы
        topk_idx = np.argpartition(-sims, k)[:k]
        topk_pids = {all_pids[i] for i in topk_idx}

        total += 1
        if test_item in topk_pids:
            hits += 1

    recall = hits / total if total > 0 else 0.0
    print(f"Recall@{k}: {recall:.4f} (users evaluated: {total})")


if __name__ == "__main__":
    recall_at_k(k=10)
