import requests
import os
from dotenv import load_dotenv

load_dotenv()
giphy_key = os.getenv("GIPHY_API_KEY")

GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"
GIPHY_TRENDING_URL = "https://api.giphy.com/v1/gifs/trending"


def search_gif(query, limit=20, pos=None):
    if not query:
        return {"gifs": [], "next": None}

    offset = int(pos) if pos else 0
    params = {
        "api_key": giphy_key,
        "q": query,
        "limit": limit,
        "offset": offset,
        "rating": "pg-13",
    }

    response = requests.get(GIPHY_SEARCH_URL, params=params)
    if response.status_code != 200:
        return {"gifs": [], "next": None}

    data = response.json().get("data", [])
    gifs = [item["images"]["downsized"]["url"] for item in data]
    next_offset = offset + limit if len(gifs) == limit else None

    return {"gifs": gifs, "next": next_offset}


def featured_gifs(limit=20):
    params = {
        "api_key": giphy_key,
        "limit": limit,
        "rating": "pg-13",
    }

    response = requests.get(GIPHY_TRENDING_URL, params=params)
    if response.status_code != 200:
        return []

    return [item["images"]["downsized"]["url"] for item in response.json().get("data", [])]
