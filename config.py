import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from config.env file
load_dotenv('config.env')

class Config:
    """Configuration class for the movie recommender application"""
    
    # TMDB API Configuration
    TMDB_API_KEY: str = os.getenv('TMDB_API_KEY', 'your_tmdb_api_key_here')
    TMDB_BASE_URL: str = os.getenv('TMDB_BASE_URL', 'https://api.themoviedb.org/3')
    IMAGE_BASE_URL: str = os.getenv('IMAGE_BASE_URL', 'https://image.tmdb.org/t/p/w500')
    FALLBACK_POSTER_URL: str = os.getenv('FALLBACK_POSTER_URL', 'https://dummyimage.com/500x750/1f2937/9ca3af&text=No+Poster')
    YOUTUBE_BASE_URL: str = os.getenv('YOUTUBE_BASE_URL', 'https://www.youtube.com/watch?v=')
    
    # Backend API Configuration
    BACKEND_BASE_URL: str = os.getenv('BACKEND_BASE_URL', 'http://127.0.0.1:8000')
    API_TIMEOUT_SEC: int = int(os.getenv('API_TIMEOUT_SEC', '20'))
    API_MAX_RETRIES: int = int(os.getenv('API_MAX_RETRIES', '3'))
    
    # Model Configuration (Local files only)
    MODEL_CACHE_DIR: str = os.getenv('MODEL_CACHE_DIR', './models')
    
    # Application Configuration
    CACHE_TTL_MS: int = int(os.getenv('CACHE_TTL_MS', '60000'))
    TMDB_BATCH_SIZE: int = int(os.getenv('TMDB_BATCH_SIZE', '6'))
    TMDB_MAX_PER_HOST: int = int(os.getenv('TMDB_MAX_PER_HOST', '12'))
    
    # Development Configuration
    DEBUG: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # File paths
    MOVIES_DATA_FILE: str = "final_movies_cleaned.feather"
    EMBEDDINGS_FILE: str = "movie_embeddings_float16.npy"
    MODEL_FILE: str = "fine_tuned_sbert_multi_modal.zip"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_fields = [
            'TMDB_API_KEY',
            'TMDB_BASE_URL',
            'BACKEND_BASE_URL'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"Missing required configuration: {missing_fields}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("=== Configuration ===")
        print(f"TMDB Base URL: {cls.TMDB_BASE_URL}")
        print(f"Backend URL: {cls.BACKEND_BASE_URL}")
        print(f"Image Base URL: {cls.IMAGE_BASE_URL}")
        print(f"Model Cache Dir: {cls.MODEL_CACHE_DIR}")
        print(f"Debug Mode: {cls.DEBUG}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Cache TTL: {cls.CACHE_TTL_MS}ms")
        print(f"API Timeout: {cls.API_TIMEOUT_SEC}s")
        print(f"API Max Retries: {cls.API_MAX_RETRIES}")
        print("===================")

# Create global config instance
config = Config()

# Validate configuration on import
if not config.validate():
    raise ValueError("Invalid configuration. Please check your config.env file.")

# Print configuration in debug mode
if config.DEBUG:
    config.print_config()

