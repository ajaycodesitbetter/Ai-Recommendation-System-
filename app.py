from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import logging
from rapidfuzz import fuzz, process
import ftfy
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

app = FastAPI(title="MoviesMate API", description="AI-Powered Movie Recommendations by Ajay Mathuriya, IIT Ropar")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TMDB Configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '55fcc2429d81d7ed94dc77fd99dc4619')
TMDB_BASE_URL = os.getenv('TMDB_BASE_URL', 'https://api.themoviedb.org/3')

class MovieOut(BaseModel):
    id: int
    title: str
    release_date: Optional[str]
    adult: Optional[bool]
    overview: Optional[str]
    vote_average: Optional[float]
    poster_path: Optional[str]

@app.get("/")
def read_root():
    return {"message": "MoviesMate API is running!", "created_by": "Ajay Mathuriya, IIT Ropar"}

@app.get("/model/status")
async def get_model_status():
    return {
        "status": "success",
        "model_info": {
            "status": "ready",
            "type": "tmdb_direct",
            "message": "Using TMDB API directly for fast deployment"
        }
    }

@app.get("/search")
async def search_movies(query: str = Query(...)):
    try:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'en-US',
            'page': 1,
            'include_adult': False
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = data.get('results', [])[:10]  # Limit to 10 results
        
        return results
        
    except Exception as e:
        logging.error(f"Search error: {e}")
        return []

@app.get("/recommendations")
async def get_recommendations(movie_id: int = Query(...)):
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': 1
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = data.get('results', [])[:10]
        
        return results
        
    except Exception as e:
        logging.error(f"Recommendations error: {e}")
        return []

@app.get("/trending")
async def get_trending():
    try:
        url = f"{TMDB_BASE_URL}/trending/movie/day"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = data.get('results', [])[:10]
        
        return results
        
    except Exception as e:
        logging.error(f"Trending error: {e}")
        return []

@app.get("/top-rated")
async def get_top_rated():
    try:
        url = f"{TMDB_BASE_URL}/movie/top_rated"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': 1
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = data.get('results', [])[:10]
        
        return results
        
    except Exception as e:
        logging.error(f"Top rated error: {e}")
        return []

@app.post("/recommendations/user")
async def recommend_for_user(payload: dict):
    try:
        # For now, return popular movies based on mood
        mood = payload.get("mood", "happy").lower()
        
        # Map moods to genres
        mood_genre_map = {
            "happy": "35",      # Comedy
            "excited": "28",    # Action
            "relaxed": "18",    # Drama
            "adventurous": "12", # Adventure
            "romantic": "10749", # Romance
            "mysterious": "9648" # Mystery
        }
        
        genre_id = mood_genre_map.get(mood, "35")
        
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'with_genres': genre_id,
            'sort_by': 'popularity.desc',
            'language': 'en-US',
            'page': 1
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = data.get('results', [])[:10]
        
        return results
        
    except Exception as e:
        logging.error(f"User recommendations error: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
