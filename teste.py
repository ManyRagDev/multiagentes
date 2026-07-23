# teste.py
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL")
)

response = client.chat.completions.create(
    model=os.getenv("ZAI_MODEL"),
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Diga olá em uma frase"},
    ],
)
print(response.choices[0].message.content)