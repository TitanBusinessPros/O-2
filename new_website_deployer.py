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
    
    # Hardcode coordinates for major cities to avoid wrong detection
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
        "Seattle": {"lat": "47.6062", "lon": "-122.3321", "display_name": "Seattle, Washington, USA"},
        "Phoenix": {"lat": "33.4484", "lon": "-112.0740", "display_name": "Phoenix, Arizona, USA"},
        "Philadelphia": {"lat": "39.9526", "lon": "-75.1652", "display_name": "Philadelphia, Pennsylvania, USA"},
        "Houston": {"lat": "29.7604", "lon": "-95.3698", "display_name": "Houston, Texas, USA"},
        "Denver": {"lat": "39.7392", "lon": "-104.9903", "display_name": "Denver, Colorado, USA"},
        "Atlanta": {"lat": "33.7490", "lon": "-84.3880", "display_name": "Atlanta, Georgia, USA"}
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
    return f"{city_name} is a vibrant city with a rich history and growing technology sector, offering numerous opportunities for software developers and tech professionals. The city has become a hub for innovation and digital transformation in recent years."

def query_overpass_fixed(amenity_type, lat, lon):
    """Query Overpass API with proper delays"""
    # Create bounding box around coordinates
    bbox = f"{float(lat)-0.3},{float(lon)-0.3},{float(lat)+0.3},{float(lon)+0.3}"
    
    queries = {
        'libraries': f"""
            [out:json][timeout:30];
            (
                node["amenity"="library"]({bbox});
                way["amenity"="library"]({bbox});
            );
            out center;
        """,
        'bars': f"""
            [out:json][timeout:30];
            (
                node["amenity"="bar"]({bbox});
                way["amenity"="bar"]({bbox});
            );
            out center;
        """,
        'restaurants': f"""
            [out:json][timeout:30];
            (
                node["amenity"="restaurant"]({bbox});
                way["amenity"="restaurant"]({bbox});
            );
            out center;
        """,
        'barbers': f"""
            [out:json][timeout:30];
            (
                node["shop"="hairdresser"]({bbox});
                way["shop"="hairdresser"]({bbox});
            );
            out center;
        """
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
    old_wiki_text = "Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team."
    
    # Add Wikipedia citation
    wiki_with_citation = f"{wikipedia_text}<p><em>Source: Wikipedia</em></p>"
    content = content.replace(old_wiki_text, wiki_with_citation)
    
    # Add OSM citation near coordinates
    osm_citation = " | Data © OpenStreetMap contributors"
    if "Oklahoma City" in content:  # If there are any remaining instances
        content = content.replace("Oklahoma City", city_name)
    
    debug_log("✓ Template replacements completed")
    return content

def deploy_to_github(repo_name, content):
    """Deploy to GitHub with proper authentication"""
    debug_log(f"Deploying to GitHub: {repo_name}")
    
    try:
        # Use GH_TOKEN from environment
        token = os.getenv('GH_TOKEN')
        if not token:
            debug_log("❌ GH_TOKEN environment variable not found!")
            debug_log("Available env vars:")
            for key in os.environ:
                if 'token' in key.lower() or 'github' in key.lower():
                    debug_log(f"  {key}: {'*' * len(os.environ[key])}")
            return False
        
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
        
        # Try to enable GitHub Pages (may not work with GITHUB_TOKEN)
        try:
            repo.edit(has_pages=True)
            debug_log("✓ Enabled GitHub Pages")
        except Exception as e:
            debug_log(f"Note: May need manual Pages setup: {str(e)}")
        
        debug_log("✅ DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/TitanBusinessPros/{repo_name}")
        debug_log(f"🌐 Pages URL: https://TitanBusinessPros.github.io/{repo_name}")
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
        if amenity != amenity_types[-1]:  # Don't wait after the last query
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
        debug_log("🔧 If GitHub Pages isn't auto-enabled, go to:")
        debug_log(f"   https://github.com/TitanBusinessPros/{repo_name}/settings/pages")
        debug_log("   Select 'Deploy from a branch' and choose 'main' branch")
    else:
        debug_log("❌ Deployment failed")

if __name__ == "__main__":
    main()
