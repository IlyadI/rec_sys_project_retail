from typing import List
from openai import OpenAI

from .config import get_settings

settings = get_settings()

if not settings.foundation_models_api_key:
    print("⚠️ WARNING: API_KEY (Cloud.ru Foundation Models) is not set.")

client = OpenAI(
    api_key=settings.foundation_models_api_key,
    base_url=settings.foundation_models_base_url,
)


def generate_explanation(
    bought_items: List[str],
    recommended_item: str,
    bought_descriptions: List[str],
    rec_description: str,
    language: str = "en",
) -> str:
    """
    Generates a short explanation of why the recommended_item is suggested.
    """
    user_message = f"""
You are a recommendation system for an online store.

The user has previously purchased the following items:
{", ".join(f'"{d}"' for d in bought_descriptions) if bought_descriptions else "no purchase history available"}

You are now recommending the following product:
"{rec_description}"

Explain in one short sentence in English why it makes sense to recommend this product to this user.
Do not mention any technical details such as "algorithm", "model", or similar.
"""

    response = client.chat.completions.create(
        model=settings.foundation_models_chat_model,  # 👈 ТУТ КОНКРЕТНО gpt-oss
        max_tokens=300,
        temperature=0.3,
        top_p=0.95,
        presence_penalty=0.0,
        messages=[
            {
                "role": "user",
                "content": user_message.strip(),
            }
        ],
    )

    return response.choices[0].message.content.strip()
