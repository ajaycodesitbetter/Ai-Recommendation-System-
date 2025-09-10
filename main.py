from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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

# Load assets from config
movies_df = pd.read_feather(config.MOVIES_DATA_FILE)
movie_embeddings = np.load(config.EMBEDDINGS_FILE)

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

@lru_cache(maxsize=10000)
def get_tmdb_data_cached(movie_id: int):
    try:
        url = f"{TMDB_API_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"TMDB fetch failed: {e}")
    return {}


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "MoviesMate API is running!"}

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

@app.get("/search")
async def search_movies(query: str = Query(...)):
    try:
        df = get_movies_df().dropna(subset=["title"]).copy()
        
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
_movies_df = None
_movie_embeddings = None
_tmdb_cache = {}
_cache_lock = threading.Lock()
_session_pool = None
_executor = ThreadPoolExecutor(max_workers=10)

def get_movies_df():
    """Lazy loading of movies dataframe with caching"""
    global _movies_df
    if _movies_df is None:
        _movies_df = pd.read_feather("final_movies_cleaned.feather")
        # Pre-compute common columns for faster access
        _movies_df["title_clean"] = _movies_df["title"].astype(str).apply(normalize)
        _movies_df["title_length"] = _movies_df["title_clean"].str.len()
    return _movies_df

def get_movie_embeddings():
    """Lazy loading of movie embeddings with caching"""
    global _movie_embeddings
    if _movie_embeddings is None:
        _movie_embeddings = np.load("movie_embeddings_float16.npy")
    return _movie_embeddings

async def get_session():
    """Get or create aiohttp session for connection pooling"""
    global _session_pool
    if _session_pool is None:
        connector = aiohttp.TCPConnector(limit=TMDB_MAX_PER_HOST * 2, limit_per_host=TMDB_MAX_PER_HOST)
        timeout = aiohttp.ClientTimeout(total=TMDB_TIMEOUT_SEC)
        _session_pool = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _session_pool

async def batch_tmdb_requests(movie_ids: List[int]) -> dict:
    """Batch TMDB API requests for better performance"""
    session = await get_session()
    results = {}
    
    # Group requests into batches of 10 (TMDB rate limit friendly)
    batch_size = TMDB_BATCH_SIZE
    for i in range(0, len(movie_ids), batch_size):
        batch = movie_ids[i:i + batch_size]
        
        # Create tasks for concurrent execution
        tasks = []
        for movie_id in batch:
            # Check cache first
            with _cache_lock:
                if movie_id in _tmdb_cache:
                    results[movie_id] = _tmdb_cache[movie_id]
                    continue
            
            # Create async task for TMDB request
            task = asyncio.create_task(fetch_tmdb_data_async(session, movie_id))
            tasks.append((movie_id, task))
        
        # Wait for all tasks in batch to complete
        for movie_id, task in tasks:
            try:
                data = await task
                results[movie_id] = data
                # Cache only non-empty useful results
                if data:
                    with _cache_lock:
                        _tmdb_cache[movie_id] = data
            except Exception as e:
                logging.error(f"Error fetching TMDB data for movie {movie_id}: {e}")
                results[movie_id] = {}
    
    return results

def _sync_fetch_tmdb(movie_id: int) -> dict:
    try:
        url = f"{TMDB_API_URL}/movie/{movie_id}"
        params = {"api_key": TMDB_API_KEY, "language": "en-US"}
        r = requests.get(url, params=params, timeout=TMDB_TIMEOUT_SEC)
        if r.status_code == 200:
            return r.json()
        return {}
    except Exception:
        return {}

async def fetch_tmdb_data_async(session: aiohttp.ClientSession, movie_id: int) -> dict:
    """Async version of TMDB data fetching"""
    url = f"{TMDB_API_URL}/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    backoff = 0.5
    for attempt in range(1, TMDB_RETRY_ATTEMPTS + 1):
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    await asyncio.sleep(retry_after)
                elif response.status in {500, 502, 503, 504}:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    # Other client/server errors: don't spam retries
                    body = await response.text()
                    logging.warning(f"TMDB {response.status} for movie {movie_id}: {body[:200]}")
                    return {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(f"Attempt {attempt} failed for movie {movie_id}: {e}")
            await asyncio.sleep(backoff)
            backoff *= 2
        except Exception as e:
            logging.error(f"Error in async TMDB request for movie {movie_id}: {e}")
            break
    # Final sync fallback
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _sync_fetch_tmdb, movie_id)

def enrich_movies_batch(movies_data: List[dict], tmdb_data: dict) -> List[dict]:
    """Batch enrich movies with TMDB data"""
    enriched_results = []
    
    for movie in movies_data:
        movie_id = int(movie["id"])
        tmdb_info = tmdb_data.get(movie_id, {})
        
        enriched_movie = {}
        for k, v in movie.items():
            if isinstance(v, (np.integer, np.floating)):
                enriched_movie[k] = v.item()
            elif isinstance(v, np.ndarray):
                enriched_movie[k] = v.tolist()
            else:
                enriched_movie[k] = v
        
        # Enrich with TMDB data
        # Prefer TMDB poster; fallback to existing movie poster if usable
        poster_from_tmdb = tmdb_info.get("poster_path")
        poster_from_movie = movie.get("poster_path")
        if poster_from_tmdb:
            enriched_movie["poster_path"] = f"{IMAGE_BASE_URL}{poster_from_tmdb}"
        elif isinstance(poster_from_movie, str) and poster_from_movie:
            if poster_from_movie.startswith("http"):
                enriched_movie["poster_path"] = poster_from_movie
            else:
                enriched_movie["poster_path"] = f"{IMAGE_BASE_URL}{poster_from_movie}"
        else:
            enriched_movie["poster_path"] = None
        
        enriched_movie["vote_average"] = tmdb_info.get("vote_average", movie.get("vote_average_5", 0) * 2)
        
        enriched_movie["genres"] = tmdb_info.get("genres") or [
            {"name": g} for g in movie.get("genres", [])
        ]

        # Include adult flag for frontend filtering
        enriched_movie["adult"] = bool(tmdb_info.get("adult", movie.get("adult", False)))
        
        enriched_results.append(enriched_movie)
    
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