# backend/app/main.py
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .recommender import Recommender
from .schemas import UserListResponse  # UserRecommendationsResponse можно не использовать
from .llm_client import generate_explanation

settings = get_settings()

app = FastAPI(
    title="OnlineRetail LLM Recommender",
    version="1.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo-friendly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Recommender instance
recommender = Recommender()

# ---------- STATIC + FRONTEND ----------

BASE_DIR = Path(__file__).resolve().parents[2]  # rec_sys_project_retail
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/retail_static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="retail_static",
)


@app.get("/retail_shop", response_class=HTMLResponse)
def retail_shop():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ---------- SERVICE ENDPOINTS ----------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/users", response_model=UserListResponse)
def list_users(limit: int = 50, offset: int = 0):
    """
    Returns user_ids only for users who still have purchases.
    Used to populate the customer dropdown.
    """
    all_user_ids = recommender.get_all_users_with_purchases()
    sliced = all_user_ids[offset : offset + limit]
    has_more = offset + limit < len(all_user_ids)
    return UserListResponse(users=sliced, has_more=has_more)


@app.get("/api/users/{user_id}/recommendations")
def user_recommendations(user_id: str, top_n: int = 12):
    """
    Main endpoint:
    - gets user purchase history,
    - computes recommendations using embeddings,
    - calls LLM to generate explanations per item,
    - returns everything as JSON.
    """
    # 1. Descriptions of bought products (for 'Previous purchases' and LLM)
    bought_descriptions = recommender.get_bought_descriptions(user_id)

    # 2. Embedding-based recommendations
    base_recs = recommender.recommend_for_user(user_id, top_n=top_n)

    # 3. Product_ids the user purchased (for prompt context)
    bought_items = recommender.get_user_items(user_id)

    # 4. Ask LLM for an explanation for each recommendation
    for rec in base_recs:
        pid = rec.get("product_id")
        desc = rec.get("description", "")

        try:
            explanation = generate_explanation(
                bought_items=bought_items,
                recommended_item=pid,
                bought_descriptions=bought_descriptions,
                rec_description=desc,
                language="en",
            )
        except Exception as e:
            print(f"LLM explanation error for {pid}: {e}")
            explanation = ""

        rec["explanation"] = explanation

    return {
        "user_id": user_id,
        "bought_descriptions": bought_descriptions,
        "recommendations": base_recs,
    }


@app.delete("/api/users/{user_id}/history", status_code=204)
def clear_user_history(user_id: str):
    """
    Clears purchase history for a given user inside the recommender.

    In this demo:
    - acts like 'Reset my profile / delete history' button,
    - after this, user has no purchase history and no personalized recs.
    """
    recommender.clear_user_history(user_id)
    # 204 No Content
    return Response(status_code=204)


@app.get("/api/products/random")
def random_product_page(top_n: int = 8):
    """
    Picks a random product from the catalog and finds
    'frequently bought together' (similar products in embedding space).

    Used on the Product Page view.
    """
    product = recommender.get_random_product()
    if not product:
        raise HTTPException(status_code=500, detail="No products available")

    fbt_items = recommender.similar_products(product["product_id"], top_n=top_n)

    return {
        "product": product,
        "frequently_bought_together": fbt_items,
    }
