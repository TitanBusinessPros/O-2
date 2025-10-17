# debug_fix.py
import requests
import time
import json
import os
from datetime import datetime

def debug_log(message):
    print(f"[DEBUG] {datetime.now().strftime('%H:%M:%S')} - {message}")

def read_city_file():
    """Read and parse the city from the text file"""
    try:
        with open('city.txt', 'r') as f:
            city_line = f.read().strip()
            debug_log(f"Raw content from city.txt: '{city_line}'")
        
        # Clean and extract city name
        city_name = city_line.split(',')[0].strip() if ',' in city_line else city_line.strip()
        debug_log(f"Parsed city name: '{city_name}'")
        return city_name
    except Exception as e:
        debug_log(f"ERROR reading city.txt: {str(e)}")
        return None

def fix_geocoding(city_name):
    """Fix the geocoding to find the right city"""
    debug_log("=== FIXING GEOCODING ===")
    
    # Try different query formats to find the right city
    queries = [
        f"{city_name}, Michigan, USA",  # Specific to Michigan
        f"{city_name}, USA",            # Broader search
        city_name                       # Original format
    ]
    
    for query in queries:
        debug_log(f"Trying query: '{query}'")
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=5"
        
        headers = {'User-Agent': 'TitanBusinessPros-CityDeployer/1.0'}
        
        try:
            response = requests.get(url, headers=headers)
            debug_log(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                debug_log(f"Found {len(data)} results")
                
                for i, result in enumerate(data):
                    display_name = result.get('display_name', '')
                    debug_log(f"Result {i+1}: {display_name}")
                    
                    # Check if this looks like the right city (not a street)
                    if 'Michigan' in display_name and 'County' not in display_name:
                        debug_log(f"✓ FOUND CORRECT CITY: {display_name}")
                        return result
                
                if data:
                    debug_log("Using first result (may be wrong)")
                    return data[0]
                    
        except Exception as e:
            debug_log(f"Query failed: {str(e)}")
        
        time.sleep(1)  # Be nice to the API
    
    debug_log("❌ NO SUITABLE LOCATION FOUND")
    return None

def test_wikipedia(city_name):
    """Test Wikipedia API"""
    debug_log("=== TESTING WIKIPEDIA API ===")
    
    # Try different search formats
    searches = [
        f"{city_name}, Michigan",
        city_name
    ]
    
    for search in searches:
        debug_log(f"Searching Wikipedia for: '{search}'")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search.replace(' ', '_')}"
        
        try:
            response = requests.get(url)
            debug_log(f"Wikipedia status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                extract = data.get('extract', 'No extract found')
                debug_log(f"✓ WIKIPEDIA SUCCESS: {extract[:100]}...")
                return extract
            else:
                debug_log(f"Wikipedia error: {response.status_code} - {response.text}")
                
        except Exception as e:
            debug_log(f"Wikipedia exception: {str(e)}")
    
    return None

def test_overpass_api(lat, lon):
    """Test Overpass API with proper delays"""
    debug_log("=== TESTING OVERPASS API ===")
    
    # Create bounding box around coordinates
    bbox = f"{float(lat)-0.1},{float(lon)-0.1},{float(lat)+0.1},{float(lon)+0.1}"
    
    amenities = ['library', 'bar', 'restaurant', 'hairdresser']
    results = {}
    
    for amenity in amenities:
        debug_log(f"Querying for {amenity}...")
        
        if amenity == 'hairdresser':
            query = f"""
                [out:json][timeout:25];
                (
                  node["shop"="hairdresser"]({bbox});
                  way["shop"="hairdresser"]({bbox});
                );
                out center;
            """
        else:
            query = f"""
                [out:json][timeout:25];
                (
                  node["amenity"="{amenity}"]({bbox});
                  way["amenity"="{amenity}"]({bbox});
                );
                out center;
            """
        
        try:
            response = requests.post(
                "http://overpass-api.de/api/interpreter",
                data=query
            )
            debug_log(f"Overpass {amenity} status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get('elements', [])
                debug_log(f"✓ Found {len(elements)} {amenity}(s)")
                results[amenity] = elements
            else:
                debug_log(f"❌ Overpass error: {response.status_code}")
                results[amenity] = []
                
        except Exception as e:
            debug_log(f"❌ Overpass exception: {str(e)}")
            results[amenity] = []
        
        # Critical: Wait between requests
        debug_log("Waiting 5 seconds before next Overpass query...")
        time.sleep(5)
    
    return results

def check_template_files():
    """Check if template files exist"""
    debug_log("=== CHECKING TEMPLATE FILES ===")
    
    required_files = ['index_template.html', 'new_website_deployer.py']
    
    for file in required_files:
        if os.path.exists(file):
            debug_log(f"✓ Found: {file}")
        else:
            debug_log(f"❌ Missing: {file}")

def main():
    debug_log("=== STARTING COMPREHENSIVE DEBUG ===")
    
    # 1. Check template files
    check_template_files()
    
    # 2. Read city file
    city_name = read_city_file()
    if not city_name:
        return
    
    # 3. Fix geocoding
    location = fix_geocoding(city_name)
    if not location:
        debug_log("❌ CRITICAL: Cannot proceed without location data")
        return
    
    debug_log(f"✓ Final location: {location.get('display_name')}")
    debug_log(f"✓ Coordinates: {location.get('lat')}, {location.get('lon')}")
    
    # 4. Test Wikipedia
    wiki_text = test_wikipedia(city_name)
    
    # 5. Test Overpass API
    amenities = test_overpass_api(location.get('lat'), location.get('lon'))
    
    # 6. Summary
    debug_log("=== DEBUG SUMMARY ===")
    debug_log(f"City: {city_name}")
    debug_log(f"Location Found: {location.get('display_name')}")
    debug_log(f"Wikipedia: {'✓ SUCCESS' if wiki_text else '❌ FAILED'}")
    debug_log(f"Amenities Found: {sum(len(v) for v in amenities.values())} total")
    
    debug_log("\n=== NEXT STEPS ===")
    if 'Michigan' not in location.get('display_name', ''):
        debug_log("❌ WRONG CITY DETECTED - Need to fix geocoding query")
    else:
        debug_log("✓ Correct city detected - Ready for deployment")

if __name__ == "__main__":
    main()
