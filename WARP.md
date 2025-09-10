# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

Environment setup (Windows PowerShell):
- Create and activate venv
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
- Install backend deps
  - pip install -r requirements.txt
- Optional frontend deps (none required to run)
  - npm install

Run backend API (FastAPI):
- Dev server (auto-reload):
  - uvicorn main:app --reload --host 0.0.0.0 --port 8000
- Simple Python entrypoint:
  - python main.py

Config:
- Copy and edit environment variables in config.env (already present). Critical: TMDB_API_KEY.
- Validate config and environment:
  - python setup.py

Lint/format (if tools are installed):
- Python lint: flake8 .
- Python format: black .
- JS lint/format (if configured locally): eslint . and prettier -w .

Testing:
- There are no test suites in this repo. If pytest is added later:
  - pytest
  - Run single test: pytest -k "name"

Common ad-hoc checks:
- Verify API docs locally: start http://127.0.0.1:8000/docs
- Quick health check: curl http://127.0.0.1:8000/

## High-level architecture

Overview:
- Monorepo-style but lightweight: a FastAPI backend that serves recommendation data and a static, vanilla JS frontend (index.html + main.js) that calls both the backend and TMDB directly.
- No build toolchain required for the frontend; Tailwind is loaded via CDN and configured via tailwind-config.js.

Backend (FastAPI):
- Entry: main.py; configuration in config.py (dotenv loads config.env).
- Data assets (local):
  - final_movies_cleaned.feather: movie metadata
  - movie_embeddings_float16.npy: vector embeddings for similarity
  - fine_tuned_sbert_multi_modal.zip: local model artifact (not loaded at runtime, but referenced)
- Startup/shutdown: prewarm_cache() is scheduled on startup; aiohttp session pool and a ThreadPoolExecutor are managed (see main.py).
- Endpoints (JSON):
  - GET /                    -> health message
  - GET /model/status        -> local model status
  - GET /search?query=...    -> fuzzy/substring match over local dataset, then enrich via TMDB batch fetch
  - GET /recommendations     -> embedding cosine similarity from a movie_id, optional safe_mode and languages filters
  - GET /trending            -> popularity_norm sorted slice with filters, TMDB enrich
  - GET /top-rated           -> vote_average_5 sorted slice with filters, TMDB enrich
  - POST /recommendations/user -> mood-, language-, and preference-aware recommendations
- Enrichment pipeline:
  - For each list result: batch_tmdb_requests(movie_ids) fetches details from TMDB (via TMDB API key from config.env)
  - enrich_movies_batch merges TMDB fields (poster_path, genres, etc.) before returning to clients
- Performance considerations visible in code:
  - lru_cache on get_tmdb_data_cached for per-movie details (requests-based)
  - Async I/O using aiohttp for batch TMDB calls (see batch_tmdb_requests)
  - Over-select then filter patterns to preserve result counts after applying safe_mode/language filters

Frontend (vanilla JS + Tailwind):
- index.html drives the UI. main.js implements all client behavior.
- config.js provides runtime configuration for browser and Node contexts; the frontend uses:
  - BACKEND_BASE_URL to call the FastAPI API
  - TMDB_BASE_URL + TMDB_API_KEY for direct TMDB calls (trailers, languages, poster enrichment fallbacks)
- Key UX flows in main.js:
  - Initialization: loadUserProfile() -> detectUserLocation() -> getGenres()/getLanguages()/loadInitialData()
  - Search suggestions: debounced getSearchSuggestions() with client-side caching and abortable fetch
  - Search execution: searchMovies() hits /search then fetches /recommendations for first hit
  - Feeds: loadInitialData() loads /trending and /top-rated; loadPersonalizedRecommendations() calls POST /recommendations/user
  - Modals: showMovieDetail(movieId) fetches TMDB details + trailer, shows "More Like This" with /recommendations
  - Watchlist and ratings are persisted in localStorage and fed back into personalized recommendations
- Styling via Tailwind CDN and a local tailwind-config.js that extends animations; additional CSS in style.css.

Config and secrets:
- config.env holds environment variables (TMDB API key, base URLs, caching/retry knobs). Do not commit real secrets.
- The frontend also references TMDB_API_KEY at runtime; if hosting publicly, serve TMDB calls via the backend to avoid exposing the key.

Notes drawn from README.md:
- Quick start includes creating config.env, installing Python deps, and running uvicorn main:app --reload.
- API docs are available at /docs; frontend is opened directly via index.html.

## Repository conventions
- No package.json found; frontend runs without a bundler. Keep main.js modular but single-file.
- Python versions: requires Python 3.8+ (see README). Requirements pinned in requirements.txt.
- Data files must be present in repo root for the backend to start (feather/npy/zip paths are relative).

## Gotchas for Warp
- On Windows PowerShell, activate the venv before running uvicorn; otherwise, global Python may be used.
- If config.validate() fails on import, main.py will raise; run python setup.py to scaffold config.env with defaults, then set TMDB_API_KEY.
- Large data arrays (embeddings) load at startup; give the server a moment on first run.
- CORS is set to allow "*" for dev. If you change BACKEND_BASE_URL in config.env, update config.js if the frontend is served from a different origin.

