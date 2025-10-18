import requests
import time
import os
import re
from datetime import datetime
from github import Github, Auth

# Base URL for Overpass API
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# Hardcoded text to target for replacement (Task 7)
OLD_WIKI_BLOCK = "Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team."

# Hardcoded text for Barbershop List (Task 6)
# Corrected regex for literal match of the old barbershop list.
OLD_BARBERSHOP_BLOCK = r'<li>\*\*The Gents Place\*\* \| 13522 N Pennsylvania Ave, Oklahoma City \| \(405\) 842-8468<\/li>\s*<li>\*\*ManCave Barbershop\*\* \| 5721 N Western Ave, Oklahoma City \| \(405\) 605-4247<\/li>'

# Placeholder comments assumed to exist in index.html for safe amenity replacement
# NOTE: BARS_PLACEHOLDER and RESTAURANTS_PLACEHOLDER likely contain the word 'bar'/'restaurant' too,
# but those amenity types are less likely to result in zero items and require a fallback.
LIBRARY_PLACEHOLDER = r''
BARS_PLACEHOLDER = r''
RESTAURANTS_PLACEHOLDER = r''
WEATHER_PLACEHOLDER = r'<span id="local-weather-conditions">No weather data. Updated by daily workflow.</span>'

# Introduce a placeholder for Barbershops to simplify replacement logic
BARBERS_PLACEHOLDER = r''


def debug_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    """Read city (e.g., Dallas-Texas) from new.txt"""
    try:
        with open('new.txt', 'r') as f:
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
    city_name_simple = full_city_name.split('-')[0].replace(' ', '_')
    debug_log(f"Fetching Wikipedia for {city_name_simple}")
    
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
    citation = "<p class='wiki-citation' style='font-size:0.8em; margin-top: 1em;'>Source: <a href='https://www.wikimedia.org/' target='_blank'>Wikidata/Wikimedia</a></p>"

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city_name_simple}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            extract = data.get('extract', default_text_body)
            
            if len(extract) < 50 or "may refer to" in extract.lower():
                 debug_log(f"⚠ Wikipedia returned a generic or short response. Using default text.")
                 return default_text_body + citation

            debug_log(f"✓ Wikipedia success for {city_name_simple}")
            return extract + citation

    except Exception as e:
        debug_log(f"❌ Wikipedia failed: {str(e)}")
    
    return default_text_body + citation

def query_overpass_fixed(amenity_type, lat, lon):
    """Query Overpass API for amenities."""
    delta = 0.015 
    bbox = f"{float(lat)-delta},{float(lon)-delta},{float(lat)+delta},{float(lon)+delta}"
    
    amenity_tag = amenity_type
    if amenity_type == 'barbers':
        amenity_tag = 'shop="hairdresser"'
    elif amenity_type == 'library':
        amenity_tag = 'amenity="library"'
    elif amenity_type == 'bar':
        amenity_tag = 'amenity="bar"'
    elif amenity_type == 'restaurant':
        amenity_tag = 'amenity="restaurant"'
    
    query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'
    
    debug_log(f"Querying Overpass for {amenity_type} in small box...")
    
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            
            filtered_elements = []
            for element in elements:
                tags = element.get('tags', {})
                name = tags.get('name')
                phone = tags.get('phone', 'N/A')
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
    """Ensures a minimum of 3 amenities by trying wider search if needed."""
    amenities = query_overpass_fixed(amenity_type, lat, lon)
    
    if len(amenities) < 3:
        debug_log(f"⚠ Only found {len(amenities)} {amenity_type}. Retrying with wider search...")
        delta = 0.05
        bbox = f"{float(lat)-delta},{float(lon)-delta},{float(lat)+delta},{float(lon)+delta}"
        
        amenity_tag = amenity_type
        if amenity_type == 'barbers':
            amenity_tag = 'shop="hairdresser"'
        elif amenity_type == 'library':
            amenity_tag = 'amenity="library"'
        elif amenity_type == 'bar':
            amenity_tag = 'amenity="bar"'
        elif amenity_type == 'restaurant':
            amenity_tag = 'amenity="restaurant"'

        query = f'[out:json];node[{amenity_tag}]({bbox});out 3;'

        try:
            response = requests.post(OVERPASS_URL, data=query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                elements = data.get('elements', [])
                
                additional_amenities = []
                for element in elements:
                    tags = element.get('tags', {})
                    name = tags.get('name')
                    phone = tags.get('phone', 'N/A')
                    city_from_tag = tags.get('addr:city', 'Nearby Town')
                    address = tags.get('addr:full') or f"{tags.get('addr:street', 'Local Street')}, {city_from_tag}"

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

    final_amenities = amenities[:3]
    city_display = full_city_name.replace('-', ' ')
    
    while len(final_amenities) < 3:
        debug_log(f"⚠ Adding fallback item for {amenity_type}")
        
        fallback_name = f"Great Local {amenity_type.capitalize()}"
        # FIX: Change 'library' fallback name to avoid conflict with LIBRARY_PLACEHOLDER string.
        if amenity_type == 'library':
            fallback_name = "Great Local Reading Spot"

        final_amenities.append({
            'name': fallback_name,
            'address': f"Central {city_display} Area",
            'phone': '(555) 555-1212'
        })

    return final_amenities

def create_amenity_html(amenities):
    """
    Generates the HTML list items for a set of 3 amenities.
    Uses simple newline separator.
    """
    html_list = []
    for a in amenities:
        html_list.append(
            f"<li>**{a['name']}** | {a['address']} | {a['phone']}</li>"
        )
    return '\n'.join(html_list)

def create_website_content(full_city_name, location_data, wikipedia_text, amenities):
    """Create website content with all replacements."""
    debug_log("Creating website content...")
    city_name = full_city_name.split('-')[0]
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        debug_log(f"❌ Cannot read index.html: {str(e)}")
        return None
    
    # ------------------ City Name Replacements (Task 8 & 2) ------------------
    city_display = full_city_name.replace('-', ' ')
    content = content.replace('Current Local Conditions: Oklahoma City', f'Current Local Conditions: {city_display}')
    content = content.replace('Oklahoma City', city_display) 
    content = content.replace('OKC', city_name) 
    
    # ------------------ Coordinates & Citation (Task 1) ------------------
    lat = location_data.get('lat', '0')
    lon = location_data.get('lon', '0')
    
    old_coord_line = 'Lat: **35.4676** | Long: **-97.5164**'
    new_coord_line = f"Lat: **{lat}** | Long: **{lon}** <span class='osm-citation' style='font-size:0.8em;'>© <a href='https://www.openstreetmap.org/copyright' target='_blank'>OpenStreetMap contributors</a> | OSM Nominatim</span>"
    content = content.replace(old_coord_line, new_coord_line)
    
    # ------------------ Wikipedia section (Task 7) ------------------
    old_wiki_with_guild_line = OLD_WIKI_BLOCK + "\nThe Titan Software Guild is where ordinary people become extraordinary creators. Where dreams transform into apps, games, websites, and intelligent systems that change lives."
    
    new_wiki_with_guild_line = (
        wikipedia_text + 
        "\nThe Titan Software Guild is where ordinary people become extraordinary creators. Where dreams transform into apps, games, websites, and intelligent systems that change lives."
    )
    
    content = content.replace(old_wiki_with_guild_line, new_wiki_with_guild_line)

    
    # ------------------ Amenity Lists (Tasks 3, 4, 5, 6) ------------------
    
    # Barbershop List (Task 6): Use two-step process to safely replace using placeholder.
    barbers_html = create_amenity_html(amenities['barbers'])
    
    # 1. Replace the hardcoded list items with the new placeholder
    content = re.sub(OLD_BARBERSHOP_BLOCK, BARBERS_PLACEHOLDER, content, 1, re.DOTALL)
    
    # 2. Replace the placeholder with the generated HTML
    content = content.replace(BARBERS_PLACEHOLDER, barbers_html)
    
    # Libraries (Task 3) - Use Placeholder
    content = content.replace(LIBRARY_PLACEHOLDER, create_amenity_html(amenities["library"]))
    
    # Bars (Task 4) - Use Placeholder
    content = content.replace(BARS_PLACEHOLDER, create_amenity_html(amenities["bar"]))

    # Restaurants (Task 5) - Use Placeholder
    content = content.replace(RESTAURANTS_PLACEHOLDER, create_amenity_html(amenities["restaurant"]))


    # ------------------ Weather Placeholder (Problem 2 Fix and Citation) ------------------
    new_weather_content = f'<span id="local-weather-conditions">No weather data. Updated by daily workflow.</span><p class="noaa-citation" style="font-size:0.8em;">Source: NOAA</p>'
    content = content.replace(WEATHER_PLACEHOLDER, new_weather_content)


    debug_log("✓ HTML content generated with all replacements.")
    return content

# --- GITHUB DEPLOYMENT FUNCTIONS ---

def enable_github_pages(repo):
    """Enable GitHub Pages on the repository"""
    debug_log("Enabling GitHub Pages...")
    try:
        try:
            pages_info = repo.get_pages()
            debug_log(f"✓ GitHub Pages already enabled: {pages_info.url}")
            return True
        except:
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
            # Assuming the repository owner is 'TitanBusinessPros'
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
        token = os.getenv('GH_TOKEN')
        if not token:
            debug_log("❌ GH_TOKEN not found in environment!")
            return False
        
        debug_log("✓ GitHub token found, authenticating...")
        
        g = Github(auth=Auth.Token(token))
        user = g.get_user()
        
        try:
            repo = g.get_repo(f"{user.login}/{repo_name}")
            debug_log(f"✓ Repository exists: {repo_name}")
        except:
            repo = user.create_repo(repo_name, auto_init=False, description=f"Software Guild for {repo_name.replace('-', ' ')}")
            debug_log(f"✓ Created repository: {repo_name}")
        
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update {repo_name} content", content, contents.sha)
            debug_log("✓ Updated index.html")
        except:
            repo.create_file("index.html", f"Deploy {repo_name} content", content)
            debug_log("✓ Created index.html")
        
        try:
            repo.create_file(".nojekyll", "Add .nojekyll file", "")
            debug_log("✓ Created .nojekyll")
        except:
            pass

        enable_github_pages(repo)
        
        debug_log("✅ DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/{user.login}/{repo_name}")
        return True
        
    except Exception as e:
        debug_log(f"❌ GitHub deployment failed: {str(e)}")
        return False

def main():
    debug_log("=== STARTING DEPLOYMENT ===")
    
    full_city_name = read_city_file()
    if not full_city_name:
        return
    
    repo_name = create_safe_repo_name(full_city_name)
    
    location = geocode_city_fixed(full_city_name)
    if not location:
        debug_log("❌ No location data (Geocoding failed)")
        return
    
    wiki_text = get_wikipedia_summary_fixed(full_city_name)
    
    amenities = {}
    amenity_types = ['library', 'bar', 'restaurant', 'barbers'] 
    
    for amenity in amenity_types:
        amenities[amenity] = get_3_amenities(full_city_name, location['lat'], location['lon'], amenity)
        
        if amenity != amenity_types[-1]:
            debug_log("Waiting 5 seconds before next Overpass query...")
            time.sleep(5)
    
    content = create_website_content(full_city_name, location, wiki_text, amenities)
    if not content:
        return
    
    if deploy_to_github(repo_name, content):
        debug_log(f"🎉 {full_city_name} successfully deployed!")
    else:
        debug_log("❌ Deployment failed")

if __name__ == "__main__":
    main()
