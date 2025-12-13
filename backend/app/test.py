from typing import List
from openai import OpenAI


client = OpenAI(
    api_key='MGFiZGI0ZDItMWIzNy00YWViLTk5OGUtN2UxZDZhODJmMTZi.9f96a7350108983c5c0997b67327e5d7',
    base_url='https://foundation-models.api.cloud.ru/v1',
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    max_tokens=2500,
    temperature=0.5,
    presence_penalty=0,
    top_p=0.95,
    messages=[
        {
            "role": "user",
            "content":"Hello?"
        }
    ]
)

print(response.choices[0].message.content)