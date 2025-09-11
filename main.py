"""
MoviesMate - AI-Powered Movie Recommendation System
FastAPI Backend Server

Author: Ajay Mathuriya
Institution: Minor in AI from IIT Ropar (iitrprai_24081389)

This backend server provides AI-powered movie recommendations using:
- Content-based filtering with cosine similarity
- Real-time search with fuzzy matching
- Multi-language support and safety filtering
- Integration with The Movie Database (TMDB) API
"""

from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.responses import JSONResponse
import requests
import logging
from rapidfuzz import fuzz, process
import ftfy  # fixes Hindi and other Unicode issues
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Body
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from functools import lru_cache
import pickle
import os
from collections import defaultdict
import threading
from contextlib import asynccontextmanager

class Genre(BaseModel):
    name: str

class MovieOut(BaseModel):
    id: int
    title: str
    release_date: Optional[str]
    runtime: Optional[int]
    adult: Optional[bool]
    overview: Optional[str]
    vote_average: Optional[float]
    poster_path: Optional[str]
    genres: List[Genre]


app = FastAPI()

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="."), name="static")

# CORS: allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize cache and pre-warm with popular movies"""
    try:
        # Pre-warm cache in background
        asyncio.create_task(prewarm_cache())
        logging.info("Application startup completed")
    except Exception as e:
        logging.error(f"Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    try:
        global _session_pool
        if _session_pool:
            await _session_pool.close()
        _executor.shutdown(wait=True)
        logging.info("Application shutdown completed")
    except Exception as e:
        logging.error(f"Shutdown error: {e}")

# Import configuration
from config import config

# Initialize data storage
movies_df = None
movie_embeddings = None

# Try to load local data files if they exist
try:
    if os.path.exists(config.MOVIES_DATA_FILE):
        movies_df = pd.read_feather(config.MOVIES_DATA_FILE)
        logging.info(f"Loaded {len(movies_df)} movies from local database")
    if os.path.exists(config.EMBEDDINGS_FILE):
        movie_embeddings = np.load(config.EMBEDDINGS_FILE)
        logging.info(f"Loaded movie embeddings with shape {movie_embeddings.shape}")
except Exception as e:
    logging.warning(f"Could not load local data files: {e}")
    logging.info("Will use TMDB API as primary data source")

# TMDB configuration from config
TMDB_API_KEY = config.TMDB_API_KEY
TMDB_API_URL = config.TMDB_BASE_URL
IMAGE_BASE_URL = config.IMAGE_BASE_URL
TMDB_BATCH_SIZE = config.TMDB_BATCH_SIZE
TMDB_TIMEOUT_SEC = config.API_TIMEOUT_SEC
TMDB_MAX_PER_HOST = config.TMDB_MAX_PER_HOST
TMDB_RETRY_ATTEMPTS = config.API_MAX_RETRIES

# Helper: Fetch movie details from TMDB using ID
from functools import lru_cache

def get_movies_df():
    """Get movies dataframe, create from TMDB if not available locally"""
    global movies_df
    if movies_df is not None:
        return movies_df
    
    # If no local data, create a minimal dataframe for TMDB-only mode
    logging.info("No local movie database found, using TMDB API mode")
    return pd.DataFrame()

def get_movie_embeddings():
    """Get movie embeddings, return None if not available"""
    global movie_embeddings
    return movie_embeddings

# Dummy functions for batch processing when no local data is available
async def batch_tmdb_requests(movie_ids):
    """Batch fetch TMDB data for multiple movies"""
    tmdb_data = {}
    for movie_id in movie_ids:
        data = get_tmdb_data_cached(movie_id)
        if data:
            tmdb_data[movie_id] = data
    return tmdb_data

def enrich_movies_batch(movies_data, tmdb_data):
    """Enrich movies with TMDB data"""
    enriched = []
    for movie in movies_data:
        movie_id = movie.get('id')
        if movie_id and movie_id in tmdb_data:
            tmdb_movie = tmdb_data[movie_id]
            # Merge local and TMDB data
            enriched_movie = {**movie, **tmdb_movie}
            enriched.append(enriched_movie)
        else:
            enriched.append(movie)
    return enriched

@lru_cache(maxsize=10000)
def get_tmdb_data_cached(movie_id: int):
    try:
        url = f"{TMDB_API_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"TMDB fetch failed: {e}")
    return {}


# Root endpoint - serve the frontend HTML
@app.get("/")
def read_root():
    return FileResponse('index.html')

# API status endpoint
@app.get("/api")
def api_status():
    return {"message": "MoviesMate API is running!", "created_by": "Ajay Mathuriya, IIT Ropar"}

@app.get("/model/status")
async def get_model_status():
    """Get the status of the local model"""
    try:
        return {
            "status": "success",
            "model_info": {
                "status": "ready",
                "type": "local",
                "message": "Using local model files"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Search endpoint
def normalize(text):
    if not isinstance(text, str):
        return ""
    return ftfy.fix_text(text).strip().lower()

async def search_movies_tmdb_only(query: str):
    """Search movies directly using TMDB API when no local data is available"""
    try:
        url = f"{TMDB_API_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'en-US',
            'page': 1,
            'include_adult': False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    movies = data.get('results', [])
                    
                    # Format results to match expected structure
                    formatted_results = []
                    for movie in movies[:12]:  # Limit to 12 results
                        formatted_movie = {
                            'id': movie.get('id'),
                            'title': movie.get('title'),
                            'release_date': movie.get('release_date'),
                            'overview': movie.get('overview'),
                            'poster_path': movie.get('poster_path'),
                            'backdrop_path': movie.get('backdrop_path'),
                            'vote_average': movie.get('vote_average'),
                            'vote_count': movie.get('vote_count'),
                            'adult': movie.get('adult'),
                            'genre_ids': movie.get('genre_ids', []),
                            'original_language': movie.get('original_language'),
                            'popularity': movie.get('popularity')
                        }
                        formatted_results.append(formatted_movie)
                    
                    return JSONResponse(content=formatted_results)
                else:
                    logging.error(f"TMDB search failed with status {response.status}")
                    return JSONResponse(content=[])
    except Exception as e:
        logging.error(f"TMDB search error: {e}")
        return JSONResponse(content=[])

async def get_trending_movies_tmdb(limit: int, safe_mode: bool):
    """Get trending movies from TMDB API"""
    try:
        url = f"{TMDB_API_URL}/trending/movie/week"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    movies = data.get('results', [])
                    
                    # Filter and format results
                    formatted_results = []
                    for movie in movies[:limit]:
                        if safe_mode and movie.get('adult', False):
                            continue
                        
                        formatted_movie = {
                            'id': movie.get('id'),
                            'title': movie.get('title'),
                            'release_date': movie.get('release_date'),
                            'overview': movie.get('overview'),
                            'poster_path': movie.get('poster_path'),
                            'backdrop_path': movie.get('backdrop_path'),
                            'vote_average': movie.get('vote_average'),
                            'vote_count': movie.get('vote_count'),
                            'adult': movie.get('adult'),
                            'genre_ids': movie.get('genre_ids', []),
                            'original_language': movie.get('original_language'),
                            'popularity': movie.get('popularity')
                        }
                        formatted_results.append(formatted_movie)
                    
                    return JSONResponse(content=formatted_results)
                else:
                    logging.error(f"TMDB trending failed with status {response.status}")
                    return JSONResponse(content=[])
    except Exception as e:
        logging.error(f"TMDB trending error: {e}")
        return JSONResponse(content=[])

async def get_top_rated_movies_tmdb(limit: int, safe_mode: bool):
    """Get top-rated movies from TMDB API"""
    try:
        url = f"{TMDB_API_URL}/movie/top_rated"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    movies = data.get('results', [])
                    
                    # Filter and format results
                    formatted_results = []
                    for movie in movies[:limit]:
                        if safe_mode and movie.get('adult', False):
                            continue
                        
                        formatted_movie = {
                            'id': movie.get('id'),
                            'title': movie.get('title'),
                            'release_date': movie.get('release_date'),
                            'overview': movie.get('overview'),
                            'poster_path': movie.get('poster_path'),
                            'backdrop_path': movie.get('backdrop_path'),
                            'vote_average': movie.get('vote_average'),
                            'vote_count': movie.get('vote_count'),
                            'adult': movie.get('adult'),
                            'genre_ids': movie.get('genre_ids', []),
                            'original_language': movie.get('original_language'),
                            'popularity': movie.get('popularity')
                        }
                        formatted_results.append(formatted_movie)
                    
                    return JSONResponse(content=formatted_results)
                else:
                    logging.error(f"TMDB top-rated failed with status {response.status}")
                    return JSONResponse(content=[])
    except Exception as e:
        logging.error(f"TMDB top-rated error: {e}")
        return JSONResponse(content=[])

@app.get("/search")
async def search_movies(query: str = Query(...)):
    try:
        df = get_movies_df()
        
        # If no local data, search directly via TMDB API
        if df.empty:
            return await search_movies_tmdb_only(query)
        
        # Use local data if available
        df = df.dropna(subset=["title"]).copy()
        query_norm = normalize(query)

        # STEP 1: Substring match (fast) - use pre-computed title_clean
        substring_results = df[df["title_clean"].str.contains(query_norm)].head(12)

        if not substring_results.empty:
            results = substring_results
        else:
            # STEP 2: Fallback to fuzzy matching on subset (optimize by filtering long titles first)
            titles_to_check = df[df["title_length"] >= len(query_norm) - 1]
            title_map = {title: idx for idx, title in enumerate(titles_to_check["title_clean"])}

            fuzzy_matches = process.extract(query_norm, title_map.keys(), scorer=fuzz.token_set_ratio, limit=20)
            matched_indices = [
                title_map[title] for title, score, _ in fuzzy_matches if score >= 70
            ]
            results = titles_to_check.iloc[matched_indices].head(10)

        # Convert to list of dicts for batch processing
        movies_data = []
        for _, row in results.iterrows():
            movie = {}
            for k, v in row.items():
                if isinstance(v, (np.integer, np.floating)):
                    movie[k] = v.item()
                elif isinstance(v, np.ndarray):
                    movie[k] = v.tolist()
                else:
                    movie[k] = v
            movies_data.append(movie)

        # Batch fetch TMDB data for all movies
        movie_ids = [int(movie["id"]) for movie in movies_data]
        tmdb_data = await batch_tmdb_requests(movie_ids)
        
        # Batch enrich all movies
        enriched_results = enrich_movies_batch(movies_data, tmdb_data)

        return JSONResponse(content=enriched_results)

    except Exception as e:
        logging.exception("Error in /search")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Recommendation endpoint
@app.get("/recommendations")
async def recommend_by_movie_id(
    movie_id: int = Query(...),
    limit: int = Query(10, ge=1, le=50),
    safe_mode: bool = Query(False),
    languages: Optional[str] = Query(None)
):
    try:
        # Find movie by ID
        movies_df = get_movies_df()
        movie_embeddings = get_movie_embeddings()
        
        matched_movie = movies_df[movies_df["id"] == movie_id]
        if matched_movie.empty:
            return JSONResponse(status_code=404, content={"error": "Movie not found"})

        idx = matched_movie.index[0]
        query_embedding = movie_embeddings[idx].reshape(1, -1)

        # Compute cosine similarity
        similarities = cosine_similarity(query_embedding, movie_embeddings)[0]
        # Over-select then filter to ensure we can return up to 'limit'
        top_indices = similarities.argsort()[::-1][1:201]

        recommended = movies_df.iloc[top_indices].copy()

        # Apply optional language filter
        if languages:
            lang_list = [l.strip() for l in languages.split(',') if l.strip()]
            if 'all_languages' in recommended.columns and lang_list:
                recommended = recommended[recommended['all_languages'].apply(lambda langs: any(lang in langs for lang in lang_list))]

        # Apply safe mode filter
        if safe_mode and 'adult' in recommended.columns:
            recommended = recommended[recommended['adult'] != True]

        recommended = recommended.head(limit)

        # Convert to list of dicts for batch processing
        movies_data = []
        for _, row in recommended.iterrows():
            movie = {}
            for k, v in row.items():
                if isinstance(v, (np.integer, np.floating)):
                    movie[k] = v.item()
                elif isinstance(v, np.ndarray):
                    movie[k] = v.tolist()
                else:
                    movie[k] = v
            movies_data.append(movie)

        # Batch fetch TMDB data for all movies
        movie_ids = [int(movie["id"]) for movie in movies_data]
        tmdb_data = await batch_tmdb_requests(movie_ids)
        
        # Batch enrich all movies
        enriched_results = enrich_movies_batch(movies_data, tmdb_data)

        return JSONResponse(content=enriched_results)

    except Exception as e:
        logging.exception("Error in /recommendations endpoint")
        return JSONResponse(status_code=500, content={"error": str(e)})

    
@app.get("/trending")
async def get_trending_movies(
    limit: int = Query(10, ge=1, le=50),
    safe_mode: bool = Query(False),
    languages: Optional[str] = Query(None)
):
    try:
        movies_df = get_movies_df()
        
        # If no local data, use TMDB trending
        if movies_df.empty:
            return await get_trending_movies_tmdb(limit, safe_mode)
        
        trending = movies_df.sort_values("popularity_norm", ascending=False)
        # Over-select to allow filtering while still filling the limit
        trending = trending.head(max(limit * 5, 50))
        if languages:
            lang_list = [l.strip() for l in languages.split(',') if l.strip()]
            if 'all_languages' in trending.columns and lang_list:
                trending = trending[trending['all_languages'].apply(lambda langs: any(lang in langs for lang in lang_list))]
        if safe_mode and 'adult' in trending.columns:
            trending = trending[trending['adult'] != True]
        trending = trending.head(limit)
        
        # Convert to list of dicts for batch processing
        movies_data = []
        for _, row in trending.iterrows():
            movie = {}
            for k, v in row.items():
                # Safely convert all NumPy types
                if isinstance(v, (np.integer, np.floating)):
                    movie[k] = v.item()
                elif isinstance(v, np.ndarray):
                    movie[k] = v.tolist()
                else:
                    movie[k] = v
            movies_data.append(movie)

        # Batch fetch TMDB data for all movies
        movie_ids = [int(movie["id"]) for movie in movies_data]
        tmdb_data = await batch_tmdb_requests(movie_ids)
        
        # Batch enrich all movies
        results = enrich_movies_batch(movies_data, tmdb_data)

        return JSONResponse(content=results)
    except Exception as e:
        logging.exception("Error in /trending")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/top-rated")
async def get_top_rated_movies(
    limit: int = Query(10, ge=1, le=50),
    safe_mode: bool = Query(False),
    languages: Optional[str] = Query(None)
):
    try:
        movies_df = get_movies_df()
        
        # If no local data, use TMDB top-rated
        if movies_df.empty:
            return await get_top_rated_movies_tmdb(limit, safe_mode)
        
        top_rated = movies_df.sort_values("vote_average_5", ascending=False)
        top_rated = top_rated.head(max(limit * 5, 50))
        if languages:
            lang_list = [l.strip() for l in languages.split(',') if l.strip()]
            if 'all_languages' in top_rated.columns and lang_list:
                top_rated = top_rated[top_rated['all_languages'].apply(lambda langs: any(lang in langs for lang in lang_list))]
        if safe_mode and 'adult' in top_rated.columns:
            top_rated = top_rated[top_rated['adult'] != True]
        top_rated = top_rated.head(limit)
        
        # Convert to list of dicts for batch processing
        movies_data = []
        for _, row in top_rated.iterrows():
            movie = {}
            for k, v in row.items():
                if isinstance(v, (np.integer, np.floating)):
                    movie[k] = v.item()
                elif isinstance(v, np.ndarray):
                    movie[k] = v.tolist()
                else:
                    movie[k] = v
            movies_data.append(movie)

        # Batch fetch TMDB data for all movies
        movie_ids = [int(movie["id"]) for movie in movies_data]
        tmdb_data = await batch_tmdb_requests(movie_ids)
        
        # Batch enrich all movies
        results = enrich_movies_batch(movies_data, tmdb_data)

        return JSONResponse(content=results)
    except Exception as e:
        logging.exception("Error in /top-rated")
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.post("/recommendations/user", response_model=List[MovieOut])
async def recommend_for_user(payload: dict = Body(...)):
    try:
        movies_df = get_movies_df()
        
        mood = payload.get("mood", "").lower()
        languages = payload.get("language", ["en"])
        safe_mode = bool(payload.get("safe_mode", False))
        liked_movies = payload.get("liked_movies", [])
        disliked_movies = payload.get("disliked_movies", [])
        watchlist = payload.get("watchlist", [])

        # Genre mapping based on mood
        mood_genre_map = {
            "happy": ["Comedy", "Animation", "Family", "Music"],
            "excited": ["Action", "Adventure", "Thriller", "Science Fiction"],
            "relaxed": ["Drama", "Documentary", "History"],
            "adventurous": ["Adventure", "Fantasy", "Action"],
            "romantic": ["Romance", "Drama"],
            "mysterious": ["Mystery", "Thriller", "Crime"]
        }

        preferred_genres = mood_genre_map.get(mood, [])

        filtered = movies_df.copy()

        # Filter by language
        filtered = filtered[filtered["all_languages"].apply(lambda langs: any(lang in langs for lang in languages))]

        # Filter by genre match
        if preferred_genres:
            filtered = filtered[filtered["genres"].apply(lambda g: any(gen in g for gen in preferred_genres))]

        # Remove disliked movies
        if disliked_movies:
            filtered = filtered[~filtered["id"].isin(disliked_movies)]

        # Add priority boost for liked/watchlisted movies
        filtered["score"] = filtered.get("vote_average", filtered.get("vote_average_5", 3.5)).astype(float)

        if liked_movies:
            filtered.loc[filtered["id"].isin(liked_movies), "score"] += 2.0
        if watchlist:
            filtered.loc[filtered["id"].isin(watchlist), "score"] += 1.5

        # If user is not a kid (>=18), exclude Animation entirely
        age = int(payload.get("age", 25)) if str(payload.get("age", "")).isdigit() else 25
        if age >= 18 and 'genres' in filtered.columns:
            filtered = filtered[~filtered['genres'].apply(lambda g: 'Animation' in g if isinstance(g, list) else False)]

        # Apply safe mode to exclude adult content
        if safe_mode and 'adult' in filtered.columns:
            filtered = filtered[filtered['adult'] != True]

        # Select extra to ensure we can fill after TMDB enrich
        top_recommendations = filtered.sort_values("score", ascending=False).head(20)

        # Convert to list of dicts for batch processing
        movies_data = []
        for _, row in top_recommendations.iterrows():
            movie = {k: (v.item() if isinstance(v, (np.integer, np.floating)) else v) for k, v in row.items()}
            movies_data.append(movie)

        # Batch fetch TMDB data for all movies
        movie_ids = [int(movie["id"]) for movie in movies_data]
        tmdb_data = await batch_tmdb_requests(movie_ids)
        
        # Batch enrich all movies
        results = enrich_movies_batch(movies_data, tmdb_data)
        # Return exactly 10 items if possible
        results = results[:10]

        return JSONResponse(content=results)

    except Exception as e:
        logging.exception("Error in /recommendations/user")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Global variables for caching and optimization
_tmdb_cache = {}
_cache_lock = threading.Lock()
_session_pool = None
_executor = ThreadPoolExecutor(max_workers=10)

async def get_session():
    """Get or create aiohttp session for connection pooling"""
    global _session_pool
    if _session_pool is None:
        connector = aiohttp.TCPConnector(limit=TMDB_MAX_PER_HOST * 2, limit_per_host=TMDB_MAX_PER_HOST)
        timeout = aiohttp.ClientTimeout(total=TMDB_TIMEOUT_SEC)
        _session_pool = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _session_pool

async def fetch_tmdb_data_async(session, movie_id: int):
    """Async fetch TMDB data for a single movie"""
    try:
        url = f"{TMDB_API_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Cache the result
                with _cache_lock:
                    _tmdb_cache[movie_id] = data
                return movie_id, data
    except Exception as e:
        logging.error(f"Failed to fetch TMDB data for movie {movie_id}: {e}")
    return movie_id, {}

# Add placeholder functions for endpoints that need local data
async def prewarm_cache():
    """Pre-warm cache with popular movies"""
    logging.info("Cache pre-warming completed (TMDB-only mode)")
    pass
    
    return enriched_results

# Background task for pre-warming cache
async def prewarm_cache():
    """Pre-warm cache with popular movies"""
    try:
        movies_df = get_movies_df()
        popular_movies = movies_df.nlargest(50, "popularity_norm")["id"].tolist()
        await batch_tmdb_requests(popular_movies)
        logging.info("Cache pre-warming completed")
    except Exception as e:
        logging.error(f"Cache pre-warming failed: {e}")