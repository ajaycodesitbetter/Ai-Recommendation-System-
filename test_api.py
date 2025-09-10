import requests
import os
from dotenv import load_dotenv

load_dotenv('config.env')

API_KEY = os.getenv('TMDB_API_KEY')
print(f"Testing TMDB API with key: {API_KEY[:10]}...")

url = f'https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}'
response = requests.get(url)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"First movie: {data['results'][0]['title']}")
    print("✅ API key is working!")
else:
    print(f"❌ Error: {response.text}")
