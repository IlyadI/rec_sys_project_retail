# backend/app/recommender.py

import json
from typing import List, Dict, Any

import numpy as np

from .config import get_settings


class Recommender:
    """
    Embedding-based recommender:
    - offline: product_embeddings.json (Cloud.ru embeddings)
    - online: user embedding = mean of bought items embeddings
    - ranking: cosine similarity user vs product embeddings
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

        # user_id -> [product_id, ...]
        self.user_purchases: Dict[str, List[str]] = {}

        # product_id -> {"description": str, "embedding": [float, ...]}
        self.product_data: Dict[str, Dict[str, Any]] = {}

        # product ids in the same order as rows in embedding_matrix
        self.product_ids: List[str] = []

        # embedding matrix of shape (num_products, dim)
        self.embedding_matrix: np.ndarray | None = None

        self._load_data()

    def _load_data(self) -> None:
        # user purchases
        with open(self.settings.user_purchases_path, "r", encoding="utf-8") as f:
            self.user_purchases = json.load(f)

        # product embeddings + descriptions
        with open(self.settings.product_embeddings_path, "r", encoding="utf-8") as f:
            self.product_data = json.load(f)

        self.product_ids = list(self.product_data.keys())

        # build embedding matrix
        embs = [self.product_data[pid]["embedding"] for pid in self.product_ids]
        emb_arr = np.array(embs, dtype="float32")

        # normalize so cosine similarity = dot product
        norms = np.linalg.norm(emb_arr, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-8, None)
        self.embedding_matrix = emb_arr / norms

        print(
            f"Loaded {len(self.product_ids)} products, "
            f"{len(self.user_purchases)} users with purchases"
        )

    # --- helper methods ---

    def get_all_users_with_purchases(self) -> List[str]:
        return [u for u, items in self.user_purchases.items() if items]

    def get_user_items(self, user_id: str) -> List[str]:
        return self.user_purchases.get(str(user_id), [])

    def get_product_description(self, product_id: str) -> str | None:
        data = self.product_data.get(product_id)
        if not data:
            return None
        return data.get("description")

    def get_bought_descriptions(self, user_id: str, limit: int = 20) -> List[str]:
        """
        Используется для блока "Previous purchases" и для LLM-объяснений.
        """
        result: List[str] = []
        for pid in self.get_user_items(user_id):
            desc = self.get_product_description(pid)
            if desc:
                result.append(desc)
            if len(result) >= limit:
                break
        return result

    def _build_user_embedding(self, user_id: str) -> np.ndarray | None:
        """
        User embedding = mean of embeddings of all purchased items.
        """
        bought_ids = self.get_user_items(user_id)
        if not bought_ids:
            return None

        vectors = []
        for pid in bought_ids:
            pdata = self.product_data.get(pid)
            if not pdata:
                continue
            vectors.append(pdata["embedding"])

        if not vectors:
            return None

        arr = np.array(vectors, dtype="float32")
        user_vec = arr.mean(axis=0)

        norm = np.linalg.norm(user_vec)
        if norm < 1e-8:
            return None

        return user_vec / norm

    # --- main recommendation method ---

    def recommend_for_user(self, user_id: str, top_n: int = 12) -> List[Dict[str, Any]]:
        """
        Returns top-N recommendations for a user using cosine similarity
        between user embedding and product embeddings.
        """
        if self.embedding_matrix is None:
            return []

        user_vec = self._build_user_embedding(user_id)
        if user_vec is None:
            return []

        bought = set(self.get_user_items(user_id))

        # cosine similarities: (num_products,)
        sims = self.embedding_matrix @ user_vec

        # sort indices by similarity descending
        idx_sorted = np.argsort(sims)[::-1]

        recs: List[Dict[str, Any]] = []
        for idx in idx_sorted:
            pid = self.product_ids[idx]
            if pid in bought:
                continue  # do not recommend already bought items

            pdata = self.product_data.get(pid)
            if not pdata:
                continue

            recs.append(
                {
                    "product_id": pid,
                    "description": pdata.get("description", ""),
                    "score": float(sims[idx]),
                }
            )

            if len(recs) >= top_n:
                break

        return recs