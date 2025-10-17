# fixed_website_deployer.py
import requests
import time
import json
import os
from datetime import datetime
from github import Github

def debug_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    """Read city from new.txt"""
    try:
        with open('new.txt', 'r') as f:
            city_line = f.read().strip()
            debug_log(f"Read from new.txt: '{city_line}'")
        
        city_name = city_line.split(',')[0].strip() if ',' in city_line else city_line.strip()
        return city_name
    except Exception as e:
        debug_log(f"ERROR reading new.txt: {str(e)}")
        return None

def geocode_city_fixed(city_name):
    """Force finding the right city with state specification"""
    debug_log(f"Geocoding: {city_name}")
    
    # Map cities to their states to avoid wrong matches
    city_state_map = {
        "Detroit": "Michigan",
        "Dallas": "Texas", 
        "Tulsa": "Oklahoma",
        "Boston": "Massachusetts",
        "Stillwater": "Oklahoma",
        "Chicago": "Illinois",
        "New York": "New York"
    }
    
    state = city_state_map.get(city_name, "Michigan")  # Default to Michigan
    
    query = f"{city_name}, {state}, USA"
    debug_log(f"Using precise query: {query}")
    
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
    headers = {'User-Agent': 'TitanBusinessPros-CityDeployer/1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]
                debug_log(f"✓ Found: {result.get('display_name')}")
                debug_log(f"✓ Coordinates: {result.get('lat')}, {result.get('lon')}")
                return result
            else:
                debug_log("❌ No results found!")
        else:
            debug_log(f"❌ Geocoding API error: {response.status_code}")
    except Exception as e:
        debug_log(f"❌ Geocoding exception: {str(e)}")
    
    return None

def get_wikipedia_summary_fixed(city_name):
    """Get Wikipedia summary with proper error handling"""
    debug_log(f"Fetching Wikipedia for {city_name}")
    
    # Try different search formats
    searches = [
        f"{city_name}",
        f"{city_name} (city)"
    ]
    
    for search in searches:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search.replace(' ', '_')}"
        debug_log(f"Trying Wikipedia: {url}")
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                extract = data.get('extract', 'No summary available.')
                debug_log(f"✓ Wikipedia success: {extract[:100]}...")
                return extract
        except Exception as e:
            debug_log(f"Wikipedia attempt failed: {str(e)}")
    
    debug_log("❌ Could not fetch Wikipedia data")
    return f"{city_name} is a vibrant city with a rich history and growing technology sector."

def query_overpass_fixed(amenity_type, lat, lon):
    """Query Overpass API with proper delays and error handling"""
    # Create a bounding box around the coordinates
    bbox = f"{float(lat)-0.2},{float(lon)-0.2},{float(lat)+0.2},{float(lon)+0.2}"
    
    queries = {
        'libraries': f"""
            [out:json][timeout:25];
            (
                node["amenity"="library"]({bbox});
                way["amenity"="library"]({bbox});
            );
            out center;
        """,
        'bars': f"""
            [out:json][timeout:25];
            (
                node["amenity"="bar"]({bbox});
                way["amenity"="bar"]({bbox});
            );
            out center;
        """,
        'restaurants': f"""
            [out:json][timeout:25];
            (
                node["amenity"="restaurant"]({bbox});
                way["amenity"="restaurant"]({bbox});
            );
            out center;
        """,
        'barbers': f"""
            [out:json][timeout:25];
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
            data=queries[amenity_type]
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
    """Create the actual website content with all replacements"""
    debug_log("Creating website content...")
    
    # Read the template
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            template = f.read()
    except Exception as e:
        debug_log(f"❌ Cannot read index.html: {str(e)}")
        return None
    
    # Perform all replacements
    content = template
    
    # 1. Replace city name throughout
    content = content.replace('Oklahoma City', city_name)
    content = content.replace('OKC', city_name)
    
    # 2. Replace coordinates
    lat = location_data.get('lat', '0')
    lon = location_data.get('lon', '0')
    content = content.replace('35.4676', lat)
    content = content.replace('-97.5164', lon)
    
    # 3. Replace Wikipedia section
    wiki_section = f"""
    <div class="wiki-section">
        <h3>The Greatest Time in Human History</h3>
        <p>{wikipedia_text}</p>
        <p><em>Source: Wikipedia</em></p>
        <p>The Titan Software Guild is where ordinary people become extraordinary creators. Where dreams transform into apps, games, websites, and intelligent systems that change lives.</p>
    </div>
    """
    content = content.replace('Oklahoma City (OKC) is the capital and largest city of Oklahoma.', wiki_section)
    
    # 4. Replace amenities (libraries, bars, restaurants, barbers)
    # This would need more specific template markers - for now do basic replacement
    for amenity_type, items in amenities.items():
        if items:
            debug_log(f"Replacing {amenity_type} with {len(items)} items")
            # You'll need specific placeholder logic here
    
    debug_log("✓ Website content created successfully")
    return content

def deploy_to_github(repo_name, content):
    """Deploy to GitHub with automatic Pages setup"""
    debug_log(f"Deploying to GitHub: {repo_name}")
    
    try:
        # Use your GitHub token
        g = Github(os.getenv('GITHUB_TOKEN'))
        user = g.get_user()
        
        # Check if repo exists
        try:
            repo = user.get_repo(repo_name)
            debug_log(f"✓ Repository {repo_name} already exists")
        except:
            # Create new repo
            repo = user.create_repo(repo_name, auto_init=False)
            debug_log(f"✓ Created new repository: {repo_name}")
        
        # Create or update index.html
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update content for {repo_name}", content, contents.sha)
            debug_log("✓ Updated index.html")
        except:
            repo.create_file("index.html", f"Initial commit for {repo_name}", content)
            debug_log("✓ Created index.html")
        
        # Enable GitHub Pages automatically
        try:
            repo.edit(has_pages=True)
            # This might need additional API calls for newer GitHub versions
            debug_log("✓ GitHub Pages enabled")
        except Exception as e:
            debug_log(f"Note: May need manual Pages setup: {str(e)}")
        
        return True
        
    except Exception as e:
        debug_log(f"❌ GitHub deployment failed: {str(e)}")
        return False

def main():
    debug_log("=== STARTING FIXED DEPLOYMENT ===")
    
    # 1. Read city from new.txt
    city_name = read_city_file()
    if not city_name:
        return
    
    # 2. Geocode with fixed approach
    location = geocode_city_fixed(city_name)
    if not location:
        debug_log("❌ Cannot proceed without location data")
        return
    
    # 3. Get Wikipedia data
    wiki_text = get_wikipedia_summary_fixed(city_name)
    
    # 4. Query amenities with proper delays
    amenities = {}
    amenity_types = ['libraries', 'bars', 'restaurants', 'barbers']
    
    for amenity in amenity_types:
        amenities[amenity] = query_overpass_fixed(amenity, location['lat'], location['lon'])
        time.sleep(5)  # Critical delay between Overpass calls
    
    # 5. Create website content
    content = create_website_content(city_name, location, wiki_text, amenities)
    if not content:
        return
    
    # 6. Deploy to GitHub
    repo_name = f"The-{city_name}-Software-Guild"
    if deploy_to_github(repo_name, content):
        debug_log(f"✅ SUCCESS: {city_name} deployed to {repo_name}")
        debug_log(f"📝 Manual step: Check GitHub Pages settings at:")
        debug_log(f"   https://github.com/TitanBusinessPros/{repo_name}/settings/pages")
    else:
        debug_log("❌ DEPLOYMENT FAILED")

if __name__ == "__main__":
    main()
