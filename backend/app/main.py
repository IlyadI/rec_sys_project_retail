# backend/app/main.py
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .recommender import Recommender
from .schemas import UserListResponse, UserRecommendationsResponse  # если есть такие Pydantic-схемы
from .llm_client import generate_explanation

settings = get_settings()

app = FastAPI(
    title="OnlineRetail LLM Recommender",
    version="1.0.0"
)

# CORS (можно оставить allow_origins=["*"], но уже не обязательно, так как фронт на том же origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на курсовую ок, потом можно ужать
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем рекомендатель
recommender = Recommender()

# ---------- STATIC + FRONTEND ----------

# Путь к директории frontend (на уровень выше backend/)
BASE_DIR = Path(__file__).resolve().parents[2]  # rec_sys_project
FRONTEND_DIR = BASE_DIR / "frontend"

# смонтируем статику (app.js)
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
    Возвращаем список user_id только тех пользователей, у которых есть покупки.
    """
    all_user_ids = recommender.get_all_users_with_purchases()
    sliced = all_user_ids[offset: offset + limit]
    has_more = offset + limit < len(all_user_ids)
    return UserListResponse(users=sliced, has_more=has_more)

@app.get("/api/users/{user_id}/recommendations")
def user_recommendations(user_id: str, top_n: int = 12):
    """
    Основной эндпоинт:
    - достаёт историю покупок пользователя,
    - считает рекомендации по эмбеддингам,
    - вызывает LLM для генерации объяснений по каждому товару,
    - возвращает всё одним JSON.
    """

    # 1. Описания купленных товаров (для блока "Previous purchases" и LLM)
    bought_descriptions = recommender.get_bought_descriptions(user_id)

    # 2. Рекомендации по эмбеддингам
    base_recs = recommender.recommend_for_user(user_id, top_n=top_n)

    # 3. Список product_id, которые пользователь уже покупал (для промпта можно передать)
    bought_items = recommender.get_user_items(user_id)

    # 4. Для каждой рекомендации просим LLM сделать объяснение
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

    # 5. Возвращаем обычный dict — FastAPI сам сделает JSON
    return {
        "user_id": user_id,
        "bought_descriptions": bought_descriptions,
        "recommendations": base_recs,
    }
