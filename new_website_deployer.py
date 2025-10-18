# new_website_deployer.py
import requests
import time
import os
import json
from datetime import datetime
from github import Github, Auth

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
    
    # Hardcode coordinates for major cities
    major_cities = {
        "Nashville": {"lat": "36.1627", "lon": "-86.7816", "display_name": "Nashville, Tennessee, USA"},
        "Detroit": {"lat": "42.3314", "lon": "-83.0458", "display_name": "Detroit, Michigan, USA"},
        "Dallas": {"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, Texas, USA"},
        "Tulsa": {"lat": "36.1540", "lon": "-95.9928", "display_name": "Tulsa, Oklahoma, USA"},
        "Boston": {"lat": "42.3601", "lon": "-71.0589", "display_name": "Boston, Massachusetts, USA"},
        "Chicago": {"lat": "41.8781", "lon": "-87.6298", "display_name": "Chicago, Illinois, USA"},
        "New York": {"lat": "40.7128", "lon": "-74.0060", "display_name": "New York, New York, USA"},
        "Los Angeles": {"lat": "34.0522", "lon": "-118.2437", "display_name": "Los Angeles, California, USA"},
        "Miami": {"lat": "25.7617", "lon": "-80.1918", "display_name": "Miami, Florida, USA"},
        "Seattle": {"lat": "47.6062", "lon": "-122.3321", "display_name": "Seattle, Washington, USA"}
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
    except Exception as e:
        debug_log(f"Wikipedia failed: {str(e)}")
    
    # Fallback description
    return f"{city_name} is a vibrant city with a rich history and growing technology sector, offering numerous opportunities for software developers and tech professionals."

def query_overpass_fixed(amenity_type, lat, lon):
    """Query Overpass API with proper delays"""
    bbox = f"{float(lat)-0.3},{float(lon)-0.3},{float(lat)+0.3},{float(lon)+0.3}"
    
    queries = {
        'libraries': f'[out:json];node["amenity"="library"]({bbox});out;',
        'bars': f'[out:json];node["amenity"="bar"]({bbox});out;',
        'restaurants': f'[out:json];node["amenity"="restaurant"]({bbox});out;',
        'barbers': f'[out:json];node["shop"="hairdresser"]({bbox});out;'
    }
    
    debug_log(f"Querying Overpass for {amenity_type}...")
    
    try:
        response = requests.post(
            "http://overpass-api.de/api/interpreter",
            data=queries[amenity_type],
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            debug_log(f"✓ Found {len(elements)} {amenity_type}")
            return elements
        else:
            debug_log(f"❌ Overpass error: {response.status_code}")
    except Exception as e:
        debug_log(f"❌ Overpass exception: {str(e)}")
    
    return []

def create_website_content(city_name, location_data, wikipedia_text, amenities):
    """Create website content with all replacements"""
    debug_log("Creating website content...")
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        debug_log(f"❌ Cannot read index.html: {str(e)}")
        return None
    
    # Replace all Oklahoma City references
    content = content.replace('Oklahoma City', city_name)
    content = content.replace('OKC', city_name)
    
    # Replace coordinates
    lat = location_data.get('lat', '0')
    lon = location_data.get('lon', '0')
    content = content.replace('35.4676', lat)
    content = content.replace('-97.5164', lon)
    
    # Replace Wikipedia section
    old_wiki_text = "Oklahoma City (OKC) is the capital and largest city of Oklahoma."
    new_wiki_section = f"{wikipedia_text}"
    content = content.replace(old_wiki_text, new_wiki_section)
    
    debug_log("✓ Template replacements completed")
    return content

def deploy_to_github(repo_name, content):
    """Deploy to GitHub using repo secret"""
    debug_log(f"Deploying to GitHub: {repo_name}")
    
    try:
        # Use GH_TOKEN from repository secret
        token = os.getenv('GH_TOKEN')
        if not token:
            debug_log("❌ GH_TOKEN not found in environment!")
            return False
        
        debug_log("✓ GitHub token found, authenticating...")
        
        # Use proper authentication
        g = Github(auth=Auth.Token(token))
        user = g.get_user()
        
        # Create repo
        try:
            repo = user.get_repo(repo_name)
            debug_log(f"✓ Repository exists: {repo_name}")
        except:
            repo = user.create_repo(repo_name, auto_init=False, description=f"Software Guild for {repo_name}")
            debug_log(f"✓ Created repository: {repo_name}")
        
        # Create/update index.html
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update {repo_name}", content, contents.sha)
            debug_log("✓ Updated index.html")
        except:
            repo.create_file("index.html", f"Deploy {repo_name}", content)
            debug_log("✓ Created index.html")
        
        debug_log("✅ DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/TitanBusinessPros/{repo_name}")
        debug_log(f"🔧 Enable Pages: https://github.com/TitanBusinessPros/{repo_name}/settings/pages")
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
    
    # 4. Query amenities with proper delays
    amenities = {}
    amenity_types = ['libraries', 'bars', 'restaurants', 'barbers']
    
    for amenity in amenity_types:
        amenities[amenity] = query_overpass_fixed(amenity, location['lat'], location['lon'])
        if amenity != amenity_types[-1]:
            debug_log("Waiting 5 seconds before next Overpass query...")
            time.sleep(5)
    
    # 5. Create website content
    content = create_website_content(city_name, location, wiki_text, amenities)
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
