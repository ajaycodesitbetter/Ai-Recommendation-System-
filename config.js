/**
 * MoviesMate - AI-Powered Movie Recommendation System
 * Configuration Management
 * 
 * Author: Ajay Mathuriya
 * Institution: Minor in AI from IIT Ropar (iitrprai_24081389)
 * 
 * Handles environment variables and application configuration
 */

// Configuration loader for environment variables
class Config {
    constructor() {
        this.loadConfig();
    }

    loadConfig() {
        // Load from config.env file or use defaults
        this.TMDB_API_KEY = this.getEnvVar('TMDB_API_KEY', '55fcc2429d81d7ed94dc77fd99dc4619');
        this.TMDB_BASE_URL = this.getEnvVar('TMDB_BASE_URL', 'https://api.themoviedb.org/3');
        this.IMAGE_BASE_URL = this.getEnvVar('IMAGE_BASE_URL', 'https://image.tmdb.org/t/p/w500');
        this.FALLBACK_POSTER_URL = this.getEnvVar('FALLBACK_POSTER_URL', 'https://dummyimage.com/500x750/1f2937/9ca3af&text=No+Poster');
        this.YOUTUBE_BASE_URL = this.getEnvVar('YOUTUBE_BASE_URL', 'https://www.youtube.com/watch?v=');
        
        this.BACKEND_BASE_URL = this.getEnvVar('BACKEND_BASE_URL', 'https://ai-recommendation-system-u6q3.onrender.com');
        this.API_TIMEOUT_SEC = parseInt(this.getEnvVar('API_TIMEOUT_SEC', '20'));
        this.API_MAX_RETRIES = parseInt(this.getEnvVar('API_MAX_RETRIES', '3'));
        
        this.MODEL_CACHE_DIR = this.getEnvVar('MODEL_CACHE_DIR', './models');
        
        this.CACHE_TTL_MS = parseInt(this.getEnvVar('CACHE_TTL_MS', '60000'));
        this.TMDB_BATCH_SIZE = parseInt(this.getEnvVar('TMDB_BATCH_SIZE', '6'));
        this.TMDB_MAX_PER_HOST = parseInt(this.getEnvVar('TMDB_MAX_PER_HOST', '12'));
        
        this.DEBUG = this.getEnvVar('DEBUG', 'true') === 'true';
        this.LOG_LEVEL = this.getEnvVar('LOG_LEVEL', 'INFO');
    }

    getEnvVar(key, defaultValue) {
        // Try to get from environment variables (if running in Node.js)
        if (typeof process !== 'undefined' && process.env && process.env[key]) {
            return process.env[key];
        }
        
        // Try to get from config.env file (for browser environment)
        try {
            // For browser environment, we'll need to load this differently
            // For now, return default values
            return defaultValue;
        } catch (error) {
            console.warn(`Could not load ${key} from environment, using default: ${defaultValue}`);
            return defaultValue;
        }
    }

    // Method to update configuration at runtime
    updateConfig(newConfig) {
        Object.assign(this, newConfig);
    }

    // Get all configuration as an object
    getAll() {
        return {
            TMDB_API_KEY: this.TMDB_API_KEY,
            TMDB_BASE_URL: this.TMDB_BASE_URL,
            IMAGE_BASE_URL: this.IMAGE_BASE_URL,
            FALLBACK_POSTER_URL: this.FALLBACK_POSTER_URL,
            YOUTUBE_BASE_URL: this.YOUTUBE_BASE_URL,
            BACKEND_BASE_URL: this.BACKEND_BASE_URL,
            API_TIMEOUT_SEC: this.API_TIMEOUT_SEC,
            API_MAX_RETRIES: this.API_MAX_RETRIES,
            MODEL_CACHE_DIR: this.MODEL_CACHE_DIR,
            CACHE_TTL_MS: this.CACHE_TTL_MS,
            TMDB_BATCH_SIZE: this.TMDB_BATCH_SIZE,
            TMDB_MAX_PER_HOST: this.TMDB_MAX_PER_HOST,
            DEBUG: this.DEBUG,
            LOG_LEVEL: this.LOG_LEVEL
        };
    }
}

// Create global config instance
const config = new Config();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}

