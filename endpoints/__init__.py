from pathlib import Path
from cachetools import TTLCache
import google.generativeai as genai
from langchain.retrievers import AzureCognitiveSearchRetriever
import importlib, json, os

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Cache variables
cache_10s = TTLCache(maxsize=100, ttl=10)
cache_30s = TTLCache(maxsize=100, ttl=30)
cache_300s = TTLCache(maxsize=100, ttl=300)

# Stove API
auth_index = 0
stove_api_tokens = load_json('./config/stove_api.json')

# Azure
azure_config = load_json('./config/azure_config.json')
os.environ.update(azure_config)
retriever = AzureCognitiveSearchRetriever(content_key="content")

# Genai
genai_api_token = load_json('./config/genai_api.json')['api_key']
genai.configure(api_key=genai_api_token)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"temperature": 0.3, "top_p": 1, "top_k": 1, "max_output_tokens": 4096},
    safety_settings={category: "BLOCK_NONE" for category in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]}
)

# Crawler cache
SUATkey = load_json('./config/crawl_cache.json')["SUAT"]

# Itemlist
itemlist = load_json('./data/itemlist.json')

# Game data
english_class = load_json('./data/english_class.json')
gold_reward_low = load_json('./data/gold_reward_low.json')
gold_reward_high = load_json('./data/gold_reward_high.json')

# Appending endpoints
__all__ = []

for file in Path(__file__).parent.glob("*.py"):
    if file.name != "__init__.py" and file.suffix == ".py":
        module_name = file.stem
        importlib.import_module(f".{module_name}", package="endpoints")
        __all__.append(module_name)