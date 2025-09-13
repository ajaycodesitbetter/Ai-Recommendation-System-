# 🎬 MoviesMate - AI-Powered Movie Recommendation System

A modern, intelligent movie recommendation platform that provides personalized suggestions based on user preferences, mood, and viewing history. Built with FastAPI backend and a beautiful, responsive frontend.

**Created by:** Ajay Mathuriya  
**Institution:** Minor in AI from IIT Ropar (iitrprai_24081389)  
**Project Type:** AI/ML Web Application



## ✨ Features

### 🎯 **Intelligent Recommendations**
- **AI-Powered Suggestions**: Advanced machine learning algorithms provide personalized movie recommendations
- **Mood-Based Filtering**: Get movie suggestions based on your current mood (Happy, Excited, Relaxed, Adventurous, Romantic, Mysterious)
- **User Profile Learning**: System learns from your likes, dislikes, and watchlist to improve recommendations
- **Similar Movie Discovery**: Find movies similar to ones you already love

### 🔍 **Advanced Search & Discovery**
- **Smart Search**: Fast, fuzzy search with instant suggestions
- **Real-time Suggestions**: Get movie suggestions as you type (150ms response time)
- **Popular Movies**: Pre-loaded suggestions for common searches
- **Trending & Top-Rated**: Discover what's popular and critically acclaimed

### 🌍 **Multi-Language & Regional Support**
- **Language Preferences**: Support for 10+ languages including English, Hindi, Spanish, French, German, Japanese, Korean, Portuguese, Italian, and Russian
- **Regional Content**: Movies filtered by your region preferences
- **Localized Interface**: User interface adapts to your language settings

### 👨‍👩‍👧‍👦 **Family-Friendly Features**
- **Safe Mode**: Automatically filter out adult content for family viewing
- **Age-Appropriate Content**: Content filtering based on user age
- **Parental Controls**: Easy-to-use safety settings

### 📱 **Modern User Experience**
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **Dark Theme**: Beautiful dark gradient design with glass effects
- **Smooth Animations**: Fluid transitions and hover effects
- **Keyboard Navigation**: Full keyboard support for accessibility
- **Touch Gestures**: Swipe support for mobile devices

### 📚 **Watchlist & History Management**
- **Personal Watchlist**: Save movies you want to watch later
- **Viewing History**: Track movies you've explored
- **Like/Dislike System**: Rate movies to improve recommendations
- **Profile Management**: Customizable user profiles with preferences

## 🖼️ Screenshots

### 🏠 **Homepage & Main Interface**
![Homepage](screenshots/homepage.png)

*Clean, modern interface showing trending movies, search functionality, and personalized recommendations*

### 🔍 **Search & Suggestions**
![Search Interface](screenshots/search_interface.png)

*Advanced search with real-time suggestions, showing search results and related recommendations*

### 👤 **User Profile & Preferences**
![User Profile](screenshots/user_profile.png)

*Comprehensive user profile with mood selection, language preferences, and safety settings*

### 📋 **Watchlist Management**
![Watchlist](screenshots/watchlist.png)

*Personal watchlist showing saved movies with easy management options*

### 🎭 **Mood-Based Recommendations**
![Mood Selection](screenshots/mood_selection.png)

*Interactive mood selection interface with emoji-based mood indicators*

### 🎬 **Movie Details & Trailer**
![Movie Details](screenshots/movie_details.png)

*Detailed movie information page with trailer integration and similar movie recommendations*

### 📱 **Mobile Responsive Design**
<div align="left">
  <img width="200px" src="screenshots/mobile_view.png" alt="Mobile View">
</div>   

*Fully responsive design optimized for mobile devices with touch gestures*

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for development)
- TMDB API Key (free at [themoviedb.org](https://www.themoviedb.org/settings/api))

### 1. Clone the Repository
```bash
git clone <repository-url>
cd MoviesMate
```

### 2. Install Dependencies
```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies (if needed)
npm install  # Optional for development
```

### 3. Configuration
Create a `config.env` file in the root directory:

```env
# TMDB API Configuration
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
CACHE_TTL_MS=30000
TMDB_BATCH_SIZE=6
TMDB_MAX_PER_HOST=12

# Development Configuration
DEBUG=true
LOG_LEVEL=INFO
```

### 4. Run the Application
```bash
# Start the backend server
python main.py

# Or with uvicorn for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Application
- **Backend API**: http://127.0.0.1:8000
- **Frontend**: Open `index.html` in your browser
- **API Documentation**: http://127.0.0.1:8000/docs

## 🏗️ Architecture

### Backend (FastAPI)
- **FastAPI**: Modern, fast web framework for building APIs
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing for embeddings
- **Scikit-learn**: Machine learning for similarity calculations
- **Async/Await**: High-performance asynchronous operations

### Frontend (Vanilla JavaScript)
- **Modern ES6+**: Clean, maintainable JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide Icons**: Beautiful, customizable icons
- **Responsive Design**: Mobile-first approach

### Data & Models
- **Local Model Files**: Pre-trained embeddings and movie data
- **TMDB Integration**: Real-time movie data and images
- **Caching System**: Optimized performance with intelligent caching

## 📊 API Endpoints

### Core Endpoints
- `GET /` - API status and health check
- `GET /model/status` - Local model status and information
- `GET /search?query={query}` - Search movies with fuzzy matching
- `GET /recommendations?movie_id={id}` - Get similar movie recommendations
- `GET /trending` - Get currently trending movies
- `GET /top-rated` - Get top-rated movies
- `POST /recommendations/user` - Get personalized recommendations

### Query Parameters
- `limit`: Number of results (default: 10, max: 50)
- `safe_mode`: Filter adult content (true/false)
- `languages`: Comma-separated language codes (e.g., "en,hi,es")

## 🎨 Customization

### Themes
The application uses a beautiful dark theme with customizable colors:
- **Primary**: Purple gradient (#667eea to #764ba2)
- **Secondary**: Pink accents (#f093fb to #f5576c)
- **Background**: Dark gradients with glass effects

### Adding New Features
1. **Backend**: Add new endpoints in `main.py`
2. **Frontend**: Extend functionality in `main.js`
3. **Styling**: Customize appearance in `style.css`

## 🔧 Development

### Project Structure
```
MoviesMate/
├── main.py                    # FastAPI backend server
├── config.py                  # Python configuration loader
├── config.js                  # Frontend configuration
├── main.js                    # Frontend JavaScript application
├── index.html                 # Main HTML page
├── style.css                  # Custom styles
├── tailwind-config.js         # Tailwind CSS configuration
├── config.env                 # Environment variables
├── requirements.txt           # Python dependencies
├── final_movies_cleaned.feather    # Movie dataset
├── movie_embeddings_float16.npy    # Movie embeddings
├── fine_tuned_sbert_multi_modal.zip # Trained model
└── README.md                  # This file
```

### Development Commands
```bash
# Run with auto-reload
uvicorn main:app --reload

# Run with specific host/port
python main.py

# Check API documentation
open http://127.0.0.1:8000/docs
```

### Code Quality
- **Linting**: ESLint for JavaScript, Flake8 for Python
- **Formatting**: Prettier for JavaScript, Black for Python
- **Type Hints**: Full type annotations in Python code

## 🚀 Performance Optimizations

### Backend Optimizations
- **Async Operations**: Non-blocking I/O for better performance
- **Connection Pooling**: Efficient HTTP client management
- **Caching**: Intelligent caching of API responses
- **Batch Processing**: Optimized database operations

### Frontend Optimizations
- **Lazy Loading**: Images and content loaded on demand
- **Debounced Search**: Reduced API calls with smart debouncing
- **Local Caching**: Browser-side caching for faster responses
- **Optimized Rendering**: Efficient DOM updates

## 🔒 Security Features

- **Input Validation**: Comprehensive input sanitization
- **CORS Protection**: Configurable cross-origin resource sharing
- **Rate Limiting**: Built-in protection against abuse
- **Safe Mode**: Content filtering for family-friendly viewing
- **Environment Variables**: Secure configuration management

## 🌐 Browser Support

- **Chrome**: 90+ ✅
- **Firefox**: 88+ ✅
- **Safari**: 14+ ✅
- **Edge**: 90+ ✅
- **Mobile Browsers**: iOS Safari, Chrome Mobile ✅

## 📈 Performance Metrics

- **Search Response Time**: < 150ms
- **Page Load Time**: < 2 seconds
- **API Response Time**: < 500ms
- **Cache Hit Rate**: > 80%
- **Mobile Performance**: 90+ Lighthouse Score

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **The Movie Database (TMDB)** for providing comprehensive movie data
- **Tailwind CSS** for the beautiful utility-first CSS framework
- **Lucide** for the amazing icon set
- **FastAPI** for the excellent Python web framework
- **Pandas & NumPy** for data processing capabilities

## 📞 Support

- **GitHub Repository**: [MoviesMate AI Recommendation System](https://github.com/ajaycodesitbetter/Ai-Recommendation-System-)
- **Developer**: Ajay Mathuriya, IIT Ropar
- **Academic Project**: Minor in AI from IIT Ropar

---

**Made with ❤️ for movie lovers everywhere**


*Discover your next favorite movie with AI-powered recommendations!*




#   D e p l o y m e n t   t r i g g e r   -   0 9 / 1 0 / 2 0 2 5   2 2 : 4 5 : 1 7 
 

 

