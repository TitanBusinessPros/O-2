# new_website_deployer.py
import requests
import time
import os
from github import Github
from datetime import datetime

def debug_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    """Read city from new.txt"""
    try:
        with open('new.txt', 'r') as f:
            city_name = f.read().strip()
            debug_log(f"City from new.txt: '{city_name}'")
            return city_name
    except Exception as e:
        debug_log(f"ERROR reading new.txt: {str(e)}")
        return None

def geocode_city_fixed(city_name):
    """Force correct major city detection"""
    debug_log(f"Geocoding: {city_name}")
    
    # MAJOR FIX: Hardcode coordinates for major cities to avoid wrong detection
    major_cities = {
        "Nashville": {"lat": "36.1627", "lon": "-86.7816", "display_name": "Nashville, Tennessee, USA"},
        "Detroit": {"lat": "42.3314", "lon": "-83.0458", "display_name": "Detroit, Michigan, USA"},
        "Dallas": {"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, Texas, USA"},
        "Tulsa": {"lat": "36.1540", "lon": "-95.9928", "display_name": "Tulsa, Oklahoma, USA"},
        "Boston": {"lat": "42.3601", "lon": "-71.0589", "display_name": "Boston, Massachusetts, USA"}
    }
    
    if city_name in major_cities:
        debug_log(f"✓ Using pre-defined coordinates for {city_name}")
        return major_cities[city_name]
    
    # Fallback for other cities
    query = f"{city_name}, USA"
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
    headers = {'User-Agent': 'TitanBusinessPros-CityDeployer/1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.json():
            result = response.json()[0]
            debug_log(f"✓ Found: {result.get('display_name')}")
            return result
    except Exception as e:
        debug_log(f"Geocoding error: {str(e)}")
    
    return None

def get_wikipedia_summary_fixed(city_name):
    """Get Wikipedia data with simple fallback"""
    debug_log(f"Fetching Wikipedia for {city_name}")
    
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city_name.replace(' ', '_')}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            extract = data.get('extract', 'No summary available.')
            debug_log(f"✓ Wikipedia success")
            return extract
    except:
        debug_log("Wikipedia failed, using fallback")
    
    # SIMPLE FALLBACK
    return f"{city_name} is a vibrant city with a rich history and growing technology sector, offering numerous opportunities for software developers and tech professionals. The city has become a hub for innovation and digital transformation in recent years."

def query_overpass_simple(amenity_type, lat, lon):
    """Simple Overpass query with delay"""
    bbox = f"{float(lat)-0.2},{float(lon)-0.2},{float(lat)+0.2},{float(lon)+0.2}"
    
    if amenity_type == 'barbers':
        query = f'[out:json];node["shop"="hairdresser"]({bbox});out;'
    else:
        query = f'[out:json];node["amenity"="{amenity_type}"]({bbox});out;'
    
    debug_log(f"Querying {amenity_type}...")
    
    try:
        response = requests.post("http://overpass-api.de/api/interpreter", data=query)
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            debug_log(f"✓ Found {len(elements)} {amenity_type}")
            return elements
    except Exception as e:
        debug_log(f"Overpass error: {str(e)}")
    
    return []

def create_website_content(city_name, location_data, wikipedia_text):
    """Create website content with basic replacements"""
    debug_log("Creating website content...")
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        debug_log(f"❌ Cannot read index.html: {str(e)}")
        return None
    
    # CRITICAL FIX: Replace all Oklahoma City references
    content = content.replace('Oklahoma City', city_name)
    content = content.replace('OKC', city_name)
    
    # Replace coordinates
    content = content.replace('35.4676', location_data['lat'])
    content = content.replace('-97.5164', location_data['lon'])
    
    # Replace Wikipedia section
    old_text = "Oklahoma City (OKC) is the capital and largest city of Oklahoma."
    new_text = f"{city_name} {wikipedia_text}"
    content = content.replace(old_text, new_text)
    
    debug_log("✓ Template replacements completed")
    return content

def deploy_to_github(repo_name, content):
    """Deploy to GitHub with fixed authentication"""
    debug_log(f"Deploying to GitHub: {repo_name}")
    
    try:
        # CRITICAL FIX: Use GH_TOKEN from environment
        token = os.getenv('GH_TOKEN')
        if not token:
            debug_log("❌ GH_TOKEN environment variable not found!")
            return False
        
        g = Github(token)
        user = g.get_user()
        
        # Create repo
        try:
            repo = user.get_repo(repo_name)
            debug_log(f"✓ Repository exists: {repo_name}")
        except:
            repo = user.create_repo(repo_name, auto_init=False)
            debug_log(f"✓ Created repository: {repo_name}")
        
        # Create/update index.html
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update {repo_name}", content, contents.sha)
        except:
            repo.create_file("index.html", f"Deploy {repo_name}", content)
        
        debug_log("✅ DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/TitanBusinessPros/{repo_name}")
        return True
        
    except Exception as e:
        debug_log(f"❌ GitHub deployment failed: {str(e)}")
        return False

def main():
    debug_log("=== STARTING DEPLOYMENT ===")
    
    # 1. Read city
    city_name = read_city_file()
    if not city_name:
        return
    
    # 2. Geocode with fixed coordinates
    location = geocode_city_fixed(city_name)
    if not location:
        debug_log("❌ No location data")
        return
    
    # 3. Get Wikipedia data
    wiki_text = get_wikipedia_summary_fixed(city_name)
    
    # 4. Skip Overpass for now to speed up deployment
    debug_log("Skipping Overpass queries for faster deployment")
    
    # 5. Create website content
    content = create_website_content(city_name, location, wiki_text)
    if not content:
        return
    
    # 6. Deploy to GitHub
    repo_name = f"The-{city_name}-Software-Guild"
    if deploy_to_github(repo_name, content):
        debug_log(f"🎉 {city_name} successfully deployed!")
    else:
        debug_log("❌ Deployment failed")

if __name__ == "__main__":
    main()
