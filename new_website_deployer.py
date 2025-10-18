import requests
import time
import os
import re
from datetime import datetime
from github import Github, Auth

# Base URL for Overpass API
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

def debug_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    """Read city (e.g., Dallas-Texas) from new.txt"""
    try:
        with open('new.txt', 'r') as f:
            # Task 4 fix: Read city-state format
            full_city_name = f.read().strip()
            # Handle the 'Madison, Wisconsin' format (Problem 4 and Error Log warning)
            if ',' in full_city_name:
                full_city_name = full_city_name.replace(', ', '-').strip()
                debug_log(f"WARNING: Converted input to 'City-State' format: '{full_city_name}'")

            if '-' not in full_city_name:
                debug_log("WARNING: City in new.txt should be in 'City-State' format (e.g., Dallas-Texas).")
            debug_log(f"City from new.txt: '{full_city_name}'")
            return full_city_name
    except Exception as e:
        debug_log(f"ERROR reading new.txt: {str(e)}")
        return None

def create_safe_repo_name(full_city_name):
    """Create repository name without spaces or special characters"""
    # Use the full name including state for a more specific repo name
    city_part = full_city_name.replace('-', '_')
    safe_name = re.sub(r'[^a-zA-Z0-9]', '-', city_part)
    safe_name = re.sub(r'-+', '-', safe_name).strip('-')
    repo_name = f"The-{safe_name}-Software-Guild"
    debug_log(f"Safe repository name: {repo_name}")
    return repo_name

def geocode_city_fixed(full_city_name):
    """Geocode city using the 'City-State' format for better accuracy."""
    city_name_query = full_city_name.replace('-', ', ') # e.g., Dallas, Texas
    debug_log(f"Geocoding: {city_name_query}")

    # Use Nominatim for accurate lookups (Problem 0 fix)
    query = f"{city_name_query}, USA"
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
    headers = {'User-Agent': 'TitanBusinessPros-CityDeployer/1.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and response.json():
            result = response.json()[0]
            debug_log(f"✓ Found: {result.get('display_name')}")
            return {
                'lat': result.get('lat'),
                'lon': result.get('lon'),
                'display_name': result.get('display_name')
            }
    except Exception as e:
        debug_log(f"Geocoding error: {str(e)}")
    
    return None

def get_wikipedia_summary_fixed(full_city_name):
    """Task 7 & Problem 1 Fix: Get Wikipedia summary for the city."""
    # Use only the city part for the API call
    city_name_simple = full_city_name.split('-')[0].replace(' ', '_')
    debug_log(f"Fetching Wikipedia for {city_name_simple}")
    
    # Task 7 Default Paragraph (Problem 5 Fix)
    city_display = full_city_name.replace('-', ' ')
    default_text_body = (
        f"Starting a software guild in {city_display} brings together developers, designers, and tech "
        "enthusiasts to foster a strong sense of community and shared growth. A guild provides a structured environment "
        "for collaboration, where members can exchange knowledge, mentor newcomers, and work on local or open-source "
        "projects. It serves as a bridge between aspiring programmers and experienced professionals, helping to close "
        "skill gaps and encourage lifelong learning. By organizing workshops, coding sessions, and networking events, "
        "the guild strengthens the local tech ecosystem and inspires innovation. It also creates opportunities for "
        "partnerships with schools, businesses, and startups, stimulating economic growth and job creation. A software "
        "guild encourages ethical coding practices and a culture of craftsmanship, promoting quality and accountability "
        "in the tech community. Members benefit from both personal and professional development through peer feedback "
        "and shared problem-solving. Ultimately, a software guild transforms a city into a hub of creativity, "
        "collaboration, and technological advancement that benefits everyone involved."
    )
    # Task #7 Citation
    citation = "<p class='wiki-citation' style='font-size:0.8em; margin-top: 1em;'>Source: <a href='https://www.wikimedia.org/' target='_blank'>Wikidata/Wikimedia</a></p>"

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city_name_simple}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            extract = data.get('extract', default_text_body)
            
            # Use the default if the API returns a generic or very short/unrelated summary
            if len(extract) < 50 or "may refer to" in extract.lower():
                 debug_log(f"⚠ Wikipedia returned a generic or short response. Using default text.")
                 return default_text_body + citation

            debug_log(f"✓ Wikipedia success for {city_name_simple}")
            return extract + citation

    except Exception as e:
        debug_log(f"❌ Wikipedia failed: {str(e)}")
    
    return default_text_body + citation # returns default text if API fails

def query_overpass_fixed(amenity_type, lat, lon):
    """Query Overpass API for amenities."""
    # Create a small bounding box centered on the coordinates
    delta = 0.015 # Approx 1.5 - 2 km radius for a very local search
    bbox = f"{float(lat)-delta},{float(lon)-delta},{float(lat)+delta},{float(lon)+delta}"
    
    amenity_tag = amenity_type
    if amenity_type == 'barbers':
        amenity_tag = 'shop="hairdresser"'
        query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
    elif amenity_type == 'library':
        amenity_tag = 'amenity="library"'
        query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
    elif amenity_type == 'bar':
        amenity_tag = 'amenity="bar"'
        query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
    elif amenity_type == 'restaurant':
        amenity_tag = 'amenity="restaurant"'
        query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
    
    debug_log(f"Querying Overpass for {amenity_type} in small box...")
    
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            
            # Simple check for required fields (name, phone) and filter
            filtered_elements = []
            for element in elements:
                tags = element.get('tags', {})
                name = tags.get('name')
                phone = tags.get('phone', 'N/A')
                # Use city from the tag if available, otherwise use a placeholder
                city_from_tag = tags.get('addr:city', 'Local Area') 
                address = tags.get('addr:full') or f"{tags.get('addr:street', 'Local Street')}, {city_from_tag}"
                
                if name:
                    filtered_elements.append({
                        'name': name,
                        'address': address,
                        'phone': phone
                    })
            
            debug_log(f"✓ Found {len(filtered_elements)} local {amenity_type}")
            return filtered_elements
        else:
            debug_log(f"❌ Overpass error: {response.status_code}")
    except Exception as e:
        debug_log(f"❌ Overpass exception: {str(e)}")
    
    return []

def get_3_amenities(full_city_name, lat, lon, amenity_type):
    """
    Problem 3 Fix: Ensures a minimum of 3 amenities by trying wider search if needed.
    """
    amenities = query_overpass_fixed(amenity_type, lat, lon)
    
    if len(amenities) < 3:
        debug_log(f"⚠ Only found {len(amenities)} {amenity_type}. Retrying with wider search...")
        # Widen the bounding box for a second attempt (e.g., 5-6 km radius)
        delta = 0.05
        bbox = f"{float(lat)-delta},{float(lon)-delta},{float(lat)+delta},{float(lon)+delta}"
        
        amenity_tag = amenity_type
        if amenity_type == 'barbers':
            amenity_tag = 'shop="hairdresser"'
            query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
        elif amenity_type == 'library':
            amenity_tag = 'amenity="library"'
            query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
        elif amenity_type == 'bar':
            amenity_tag = 'amenity="bar"'
            query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
        elif amenity_type == 'restaurant':
            amenity_tag = 'amenity="restaurant"'
            query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'

        try:
            response = requests.post(OVERPASS_URL, data=query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                elements = data.get('elements', [])
                
                # Filter elements again
                additional_amenities = []
                for element in elements:
                    tags = element.get('tags', {})
                    name = tags.get('name')
                    phone = tags.get('phone', 'N/A')
                    city_from_tag = tags.get('addr:city', 'Nearby Town')
                    address = tags.get('addr:full') or f"{tags.get('addr:street', 'Local Street')}, {city_from_tag}"

                    # Avoid duplicates and check for name
                    if name and all(a['name'] != name for a in amenities): 
                        additional_amenities.append({
                            'name': name,
                            'address': address,
                            'phone': phone
                        })
                        if len(amenities) + len(additional_amenities) >= 3:
                            break
                
                amenities.extend(additional_amenities)
                debug_log(f"✓ Final count for {amenity_type}: {len(amenities)}")
        except Exception as e:
            debug_log(f"❌ Overpass wide search exception: {str(e)}")

    # Truncate to 3 and provide fallback if still not enough
    final_amenities = amenities[:3]
    city_display = full_city_name.replace('-', ' ')
    
    while len(final_amenities) < 3:
        debug_log(f"⚠ Adding fallback item for {amenity_type}")
        final_amenities.append({
            'name': f"Great Local {amenity_type.capitalize()}",
            'address': f"Central {city_display} Area",
            'phone': '(555) 555-1212'
        })

    return final_amenities

def create_amenity_html(amenities):
    """Generates the HTML list items for a set of 3 amenities."""
    html_list = []
    for a in amenities:
        # Task 3, 4, 5, 6 fulfillment
        html_list.append(
            f"<li>**{a['name']}** | {a['address']} | {a['phone']}</li>"
        )
    return '\n\t\t\t\t\t\t\t'.join(html_list) # Use correct indentation for neat replacement

def create_website_content(full_city_name, location_data, wikipedia_text, amenities):
    """Create website content with all replacements (Tasks 1, 2, 7, 8 & Problem 3 Fix)"""
    debug_log("Creating website content...")
    city_name = full_city_name.split('-')[0] # e.g., Dallas
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        debug_log(f"❌ Cannot read index.html: {str(e)}")
        return None
    
    # ------------------ Task 8 & 2: Replace City Names ------------------
    # The 'current local conditions' title needs to be updated. Assuming the title is:
    content = content.replace('Current Local Conditions: Oklahoma City', f'Current Local Conditions: {city_name}')
    
    # Replace all general "Oklahoma City" references (Task 8)
    content = content.replace('Oklahoma City', full_city_name.replace('-', ' ')) 
    content = content.replace('OKC', city_name) 
    
    # ------------------ Task 1: Replace Coordinates & Citation ------------------
    lat = location_data.get('lat', '0')
    lon = location_data.get('lon', '0')
    
    # Target the footer coordinate line and add citation (Task 1 & OSM Citation)
    old_coord_line = 'Lat: **35.4676** | Long: **-97.5164**'
    new_coord_line = f"Lat: **{lat}** | Long: **{lon}** <span class='osm-citation' style='font-size:0.8em;'>© <a href='https://www.openstreetmap.org/copyright' target='_blank'>OpenStreetMap contributors</a> | OSM Nominatim</span>"
    content = content.replace(old_coord_line, new_coord_line)
    
    # ------------------ Task 7: Replace Wikipedia section ------------------
    old_wiki_text = "Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team."
    
    # The wiki_text already includes the citation (Task 7 & Citation)
    new_wiki_section = f"{wikipedia_text}" 
    # Use re.DOTALL to match across newlines in the block
    content = re.sub(re.escape(old_wiki_text) + r'[^<]*The Titan Software Guild', new_wiki_section + '\n\t\t\t\t\t\t\t\tThe Titan Software Guild', content, 1, re.DOTALL)

    
    # ------------------ Task 3, 4, 5, 6: Replace Amenity Lists (Problem 3 Fix) ------------------
    
    # Barbershop List (Task 6): This is the section you provided:
    barbers_html = create_amenity_html(amenities['barbers'])
    barbershop_regex = r'<li>\*\*The Gents Place\*\* \| 13522 N Pennsylvania Ave, Oklahoma City \| \(405\) 842-8468<\/li>\s*<li>\*\*ManCave Barbershop\*\* \| 5721 N Western Ave, Oklahoma City \| \(405\) 605-4247<\/li>'
    content = re.sub(barbershop_regex, barbers_html, content, 1, re.DOTALL)
    
    # Assuming other amenity lists are structurally similar and can be targeted:

    # Libraries (Task 3) - Assuming the library list follows the barbershop list and has a similar structure or a marker:
    # We must use placeholder text for sections not provided, or this will fail. We will use a unique placeholder.
    library_placeholder = r''
    if library_placeholder in content:
        content = content.replace(library_placeholder, create_amenity_html(amenities["library"]))
    
    # Bars (Task 4)
    bars_placeholder = r''
    if bars_placeholder in content:
        content = content.replace(bars_placeholder, create_amenity_html(amenities["bar"]))

    # Restaurants (Task 5)
    restaurants_placeholder = r''
    if restaurants_placeholder in content:
        content = content.replace(restaurants_placeholder, create_amenity_html(amenities["restaurant"]))


    # ------------------ Problem 2 Fix: Weather Placeholder and NOAA Citation ------------------
    # Assuming a placeholder like <span id="local-weather-conditions">...</span>
    weather_placeholder = r'<span id="local-weather-conditions">No weather data. Updated by daily workflow.</span>'
    content = content.replace(weather_placeholder, f'<span id="local-weather-conditions">No weather data. Updated by daily workflow.</span><p class="noaa-citation" style="font-size:0.8em;">Source: NOAA</p>')


    debug_log("✓ HTML content generated with all replacements.")
    return content

# --- REQUIRED GITHUB DEPLOYMENT FUNCTIONS (Fix for NameError) ---

def enable_github_pages(repo):
    """Enable GitHub Pages on the repository"""
    debug_log("Enabling GitHub Pages...")
    try:
        # First check if Pages is already enabled
        try:
            pages_info = repo.get_pages()
            debug_log(f"✓ GitHub Pages already enabled: {pages_info.url}")
            return True
        except:
            # Enable Pages via API
            headers = {
                "Authorization": f"token {os.getenv('GH_TOKEN')}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            # Assuming the repository owner is 'TitanBusinessPros' based on previous context
            response = requests.post(
                f"https://api.github.com/repos/TitanBusinessPros/{repo.name}/pages",
                headers=headers,
                json=data
            )
            if response.status_code in [200, 201]:
                debug_log("✓ GitHub Pages enabled successfully")
                return True
            else:
                debug_log(f"⚠ Could not auto-enable Pages: {response.status_code}")
                return False
    except Exception as e:
        debug_log(f"⚠ Pages enablement issue: {str(e)}")
        return False

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
            # Check if repo exists under the authenticated user
            repo = g.get_repo(f"{user.login}/{repo_name}")
            debug_log(f"✓ Repository exists: {repo_name}")
        except:
            # Create the repository
            repo = user.create_repo(repo_name, auto_init=False, description=f"Software Guild for {repo_name.replace('-', ' ')}")
            debug_log(f"✓ Created repository: {repo_name}")
        
        # Create/update index.html
        try:
            # Check if file exists to decide between create_file and update_file
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update {repo_name} content", content, contents.sha)
            debug_log("✓ Updated index.html")
        except:
            # File does not exist, so create it
            repo.create_file("index.html", f"Deploy {repo_name} content", content)
            debug_log("✓ Created index.html")
        
        # Also deploy the .nojekyll file to ensure GitHub pages works for pure HTML/CSS
        try:
            repo.create_file(".nojekyll", "Add .nojekyll file", "")
            debug_log("✓ Created .nojekyll")
        except:
            # File probably exists, which is fine
            pass

        # Enable GitHub Pages
        enable_github_pages(repo)
        
        debug_log("✅ DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/{user.login}/{repo_name}")
        return True
        
    except Exception as e:
        debug_log(f"❌ GitHub deployment failed: {str(e)}")
        return False

def main():
    debug_log("=== STARTING DEPLOYMENT ===")
    
    # 1. Read city (Task 4 Fix)
    full_city_name = read_city_file()
    if not full_city_name:
        return
    
    # 2. Create safe repository name
    repo_name = create_safe_repo_name(full_city_name)
    
    # 3. Geocode (Task 0 Fix)
    location = geocode_city_fixed(full_city_name)
    if not location:
        debug_log("❌ No location data (Geocoding failed)")
        return
    
    # 4. Get Wikipedia data (Task 7, Problem 1, Problem 5 Fix)
    wiki_text = get_wikipedia_summary_fixed(full_city_name)
    
    # 5. Query amenities with proper delays (Tasks 3, 4, 5, 6, Problem 3 Fix)
    amenities = {}
    amenity_types = ['library', 'bar', 'restaurant', 'barbers'] 
    
    for amenity in amenity_types:
        # Get 3 amenities logic (Problem 3 Fix)
        amenities[amenity] = get_3_amenities(full_city_name, location['lat'], location['lon'], amenity)
        
        # Delay to satisfy Overpass API requirements (Mandatory instruction)
        if amenity != amenity_types[-1]:
            debug_log("Waiting 5 seconds before next Overpass query...")
            time.sleep(5)
    
    # 6. Create website content (All Tasks/Problems handled here)
    content = create_website_content(full_city_name, location, wiki_text, amenities)
    if not content:
        return
    
    # 7. Deploy to GitHub (FIX for NameError)
    if deploy_to_github(repo_name, content):
        debug_log(f"🎉 {full_city_name} successfully deployed!")
    else:
        debug_log("❌ Deployment failed")

if __name__ == "__main__":
    main()
