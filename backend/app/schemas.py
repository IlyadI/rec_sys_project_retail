from typing import List
from pydantic import BaseModel


class ProductExplanation(BaseModel):
    product_id: str
    description: str
    score: float
    explanation: str


class UserRecommendationsResponse(BaseModel):
    user_id: str
    bought_items: List[str]
    bought_descriptions: List[str]
    recommendations: List[ProductExplanation]


class UserListResponse(BaseModel):
    users: List[str]
