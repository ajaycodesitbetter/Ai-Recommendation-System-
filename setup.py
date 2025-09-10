#!/usr/bin/env python3
"""
Setup script for MovieMate Application
Created by Ajay Mathuriya for IIT Ropar
Helps configure environment variables and validate setup
"""

import os
import sys
from pathlib import Path

def create_config_file():
    """Create config.env file with default values"""
    env_content = """# TMDB API Configuration
TMDB_API_KEY=your_tmdb_api_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3
IMAGE_BASE_URL=https://image.tmdb.org/t/p/w500
FALLBACK_POSTER_URL=https://dummyimage.com/500x750/1f2937/9ca3af&text=No+Poster
YOUTUBE_BASE_URL=https://www.youtube.com/watch?v=

# Backend API Configuration
BACKEND_BASE_URL=http://127.0.0.1:8000
API_TIMEOUT_SEC=20
API_MAX_RETRIES=3

# Model Configuration
MODEL_CACHE_DIR=./models

# Application Configuration
CACHE_TTL_MS=60000
TMDB_BATCH_SIZE=6
TMDB_MAX_PER_HOST=12

# Development Configuration
DEBUG=true
LOG_LEVEL=INFO
"""
    
    config_path = Path("config.env")
    if config_path.exists():
        print("config.env already exists. Skipping creation.")
        return
    
    with open(config_path, 'w') as f:
        f.write(env_content)
    
    print("✅ Created config.env file with default values")
    print("⚠️  Please update TMDB_API_KEY and HF_TOKEN with your actual values")

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'), 
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('scikit-learn', 'sklearn'),
        ('requests', 'requests'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall them with: pip install -r requirements.txt")
        return False
    else:
        print("✅ All required packages are installed")
        return True

def check_files():
    """Check if required data files exist"""
    required_files = [
        "final_movies_cleaned.feather",
        "movie_embeddings_float16.npy",
        "fine_tuned_sbert_multi_modal.zip"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("⚠️  Some data files are missing:")
        for file in missing_files:
            print(f"   - {file}")
    else:
        print("✅ All required data files are present")
    
    return len(missing_files) == 0

def validate_config():
    """Validate the configuration"""
    try:
        from config import config as app_config
        print("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    """Main setup function"""
    print("🎬 Movie Recommender Setup")
    print("=" * 40)
    
    # Create config file
    create_config_file()
    print()
    
    # Check dependencies
    deps_ok = check_dependencies()
    print()
    
    # Check files
    files_ok = check_files()
    print()
    
    # Validate config
    config_ok = validate_config()
    print()
    
    if deps_ok and config_ok:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your API keys in config.env")
        print("2. Run: uvicorn main:app --reload")
        print("3. Open index.html in your browser")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

