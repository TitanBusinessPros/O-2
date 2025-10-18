import requests
import time
import os
import re
from datetime import datetime
from github import Github, Auth
from jinja2 import Template

def debug_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    try:
        with open('new.txt', 'r') as f:
            city_name = f.read().strip()
            debug_log(f"City from new.txt: '{city_name}'")
            return city_name
    except Exception as e:
        debug_log(f"ERROR reading new.txt: {str(e)}")
        return None

def geocode_city_fixed(city_name):
    major_cities = {
        "Nashville": {"lat": "36.1627", "lon": "-86.7816"},
        "Dallas": {"lat": "32.7767", "lon": "-96.7970"},
        # Add more fixed cities if needed
    }
    if city_name in major_cities:
        debug_log(f"Using fixed coordinates for {city_name}")
        return major_cities[city_name]
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={city_name}, USA&limit=1"
    headers = {'User-Agent': 'TitanBusinessPros-CityDeployer/1.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.json():
            result = response.json()[0]
            debug_log(f"Geocode success: {result.get('display_name')}")
            return {"lat": result['lat'], "lon": result['lon']}
    except Exception as e:
        debug_log(f"Geocode error: {str(e)}")
    return None

def get_wikipedia_summary(city_name):
    debug_log(f"Fetching Wikipedia summary for {city_name}")
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city_name.replace(' ', '_')}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get('extract', '')
    except Exception as e:
        debug_log(f"Wikipedia fetch error: {str(e)}")
    return f"{city_name} is a vibrant city with a rich history and a strong tech community."

def query_overpass(amenity_type, lat, lon):
    bbox = f"{float(lat)-0.3},{float(lon)-0.3},{float(lat)+0.3},{float(lon)+0.3}"
    queries = {
        'libraries': f'[out:json];node["amenity"="library"]({bbox});out;',
        'bars': f'[out:json];node["amenity"="bar"]({bbox});out;',
        'restaurants': f'[out:json];node["amenity"="restaurant"]({bbox});out;',
        'barbers': f'[out:json];node["shop"="hairdresser"]({bbox});out;'
    }
    debug_log(f"Querying Overpass for {amenity_type}")
    try:
        response = requests.post("http://overpass-api.de/api/interpreter", data=queries[amenity_type], timeout=30)
        if response.status_code == 200:
            return response.json().get('elements', [])
    except Exception as e:
        debug_log(f"Overpass error: {str(e)}")
    return []

def create_website_content(city_name, location, wiki_text, amenities):
    debug_log("Rendering HTML content with Jinja2")
    with open('index.html', 'r', encoding='utf-8') as f:
        template = Template(f.read())
    # For simplicity, only including names for amenities, truncated to 3 each
    def extract_names(elements):
        names = []
        for el in elements:
            name = el.get('tags', {}).get('name')
            if name:
                names.append(name)
            if len(names) >= 3:
                break
        return names

    context = {
        'CITY_NAME': city_name,
        'CITY_ABBR': city_name[:3].upper(),
        'LATITUDE': location.get('lat', '0'),
        'LONGITUDE': location.get('lon', '0'),
        'WIKI_INTRO': wiki_text,
        'LIBRARIES': extract_names(amenities.get('libraries', [])),
        'BARS': extract_names(amenities.get('bars', [])),
        'RESTAURANTS': extract_names(amenities.get('restaurants', [])),
        'BARBERS': extract_names(amenities.get('barbers', []))
    }

    rendered = template.render(**context)
    return rendered

def deploy_to_github(repo_name, content):
    debug_log(f"Deploying repository {repo_name}")
    token = os.getenv('GH_TOKEN')
    if not token:
        debug_log("GitHub token not found!")
        return False
    try:
        g = Github(token)
        user = g.get_user()
        try:
            repo = user.get_repo(repo_name)
        except:
            repo = user.create_repo(repo_name)
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", "Update site", content, contents.sha)
        except:
            repo.create_file("index.html", "Create site", content)
        debug_log("Deployment succeeded")
        return True
    except Exception as e:
        debug_log(f"Deployment failed: {str(e)}")
        return False

def main():
    debug_log("Starting deployment process")
    city = read_city_file()
    if not city:
        return
    repo_name = f"The-{city.replace(' ', '-')}-Software-Guild"
    location = geocode_city_fixed(city)
    if not location:
        debug_log("Location not found")
        return
    wiki_text = get_wikipedia_summary(city)
    amenities = {}
    for amenity in ['libraries', 'bars', 'restaurants', 'barbers']:
        amenities[amenity] = query_overpass(amenity, location['lat'], location['lon'])
        time.sleep(5)  # Respect API rate limits
    content = create_website_content(city, location, wiki_text, amenities)
    deploy_to_github(repo_name, content)

if __name__ == "__main__":
    main()
