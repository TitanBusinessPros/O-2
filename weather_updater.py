import os
import sys
import requests
import json
import time
import datetime
import base64
from github import Github
from textwrap import dedent

# --- CONFIGURATION ---
BASE_REPO_NAME = "O-2"
REPO_PREFIX = "The-"
REPO_SUFFIX = "-Software-Guild"
TEMPLATE_FILE_NAME = "index.html"
CITY_LIST_FILE = "new.txt"

# Delay between each city deployment to avoid hitting API rate limits
DEPLOYMENT_DELAY_SECONDS = 180

# Overpass API call delay (increased to 5 seconds as requested)
OVERPASS_CALL_DELAY_SECONDS = 5
# ---------------------

def get_city_list(file_name):
    """Reads the list of cities from the provided text file."""
    try:
        with open(file_name, 'r') as f:
            cities = [line.strip() for line in f if line.strip()]
        return list(set(cities))
    except FileNotFoundError:
        print(f"FATAL: The file '{file_name}' was not found. Exiting.")
        sys.exit(1)

def get_coordinates_and_bbox(city_name):
    """
    Uses OSM Nominatim to geocode the city and return its coordinates and bounding box.
    Now properly handles city names with states/countries.
    """
    # Preserve the full city name with state for accurate geocoding
    if '-' in city_name and any(word in city_name for word in ['Oklahoma', 'Texas', 'California', 'Florida', 'New York']):
        # Handle "City-State" format like "Yukon-Oklahoma"
        city_parts = city_name.split('-')
        if len(city_parts) == 2:
            city = city_parts[0].strip()
            state = city_parts[1].strip()
            search_query = f"{city}, {state}, USA"
        else:
            search_query = f"{city_name}, USA"
    elif ',' in city_name:
        # Handle "City, State" format
        search_query = f"{city_name}, USA"
    else:
        # Just city name - default to Oklahoma for your use case
        search_query = f"{city_name}, Oklahoma, USA"
    
    print(f"   -> Geocoding search: {search_query}")
    url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
    
    headers = {'User-Agent': 'Titan-Software-Guild-Deployment-Script/1.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            display_name = data[0].get('display_name', 'Unknown location')
            
            bbox_list = [float(b) for b in data[0]['boundingbox']]
            s_lat, n_lat, w_lon, e_lon = bbox_list[0], bbox_list[1], bbox_list[2], bbox_list[3]
            bbox = f"{s_lat},{w_lon},{n_lat},{e_lon}" 
            
            print(f"   -> Found: {display_name}")
            print(f"   -> Coordinates: Lat: {lat}, Lon: {lon}, BBox: {bbox}")
            return lat, lon, bbox
        else:
            print(f"   -> WARNING: Could not geocode '{search_query}'. Skipping.")
            return None, None, None
            
    except requests.RequestException as e:
        print(f"   -> ERROR geocoding '{search_query}': {e}")
        return None, None, None

def get_overpass_data(bbox, amenity_tag, limit=3):
    """Uses Overpass API to get a list of venues based on amenity tag and BBox."""
    time.sleep(OVERPASS_CALL_DELAY_SECONDS)
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Simplified query to avoid timeouts
    if '=' in amenity_tag:
        key, value = amenity_tag.split('=')
        overpass_query = f"""
        [out:json][timeout:45];
        (
          node[{key}={value}]({bbox});
          way[{key}={value}]({bbox});
        );
        out center {limit};
        """
    else:
        overpass_query = f"""
        [out:json][timeout:45];
        (
          node[{amenity_tag}]({bbox});
          way[{amenity_tag}]({bbox});
        );
        out center {limit};
        """
    
    try:
        response = requests.post(overpass_url, data={'data': overpass_query}, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   -> ERROR querying Overpass for {amenity_tag}: {e}")
        return None

def get_wikipedia_summary(city_name):
    """
    Fetches a descriptive summary for the city from Wikipedia API.
    """
    print(f"-> Fetching city summary from Wikipedia for {city_name}...")
    
    headers = {'User-Agent': 'Titan-Software-Guild-Deployment-Script/1.0'}
    
    # Clean city name for Wikipedia - use just the city part
    clean_city_name = city_name.split('-')[0].split(',')[0].strip()
    
    # Try with state/country context first, then just city name
    wikipedia_queries = [
        city_name.replace('-', ' ').replace(',', ''),
        clean_city_name
    ]
    
    for query in wikipedia_queries:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'extract' in data:
                    summary = data['extract']
                    summary += f" (Source: Wikipedia)"
                    return summary
        except requests.RequestException:
            continue
    
    # Fallback description
    return f"{clean_city_name} is the current focal point of the software development revolution. The Titan Software Guild aims to be the center of this movement in the area. (Source: Wikipedia)"

def get_venue_html(overpass_data, venue_type):
    """Formats Overpass venue data into an HTML list."""
    if not overpass_data or not overpass_data.get('elements'):
        return f"<ul><li>No {venue_type} found in this area.</li></ul>"
    
    html_list = ["<ul>"]
    
    for element in overpass_data['elements'][:3]:
        name = element['tags'].get('name', f'Unnamed {venue_type}')
        
        # Build address information
        address_parts = []
        if 'addr:street' in element['tags']:
            address_parts.append(element['tags']['addr:street'])
        if 'addr:city' in element['tags']:
            address_parts.append(element['tags']['addr:city'])
        elif 'addr:place' in element['tags']:
            address_parts.append(element['tags']['addr:place'])
        
        address = ', '.join(address_parts) if address_parts else 'Address not available'
        
        # Create Google Maps link
        if 'lat' in element and 'lon' in element:
            link = f"https://www.google.com/maps/search/?api=1&query={element['lat']},{element['lon']}"
        elif 'center' in element:
            link = f"https://www.google.com/maps/search/?api=1&query={element['center']['lat']},{element['center']['lon']}"
        else:
            link = "https://www.google.com/maps"
            
        html_list.append(f"""
            <li>
                <a href="{link}" target="_blank">{name}</a>
                <p class="address-line">{address}</p>
            </li>
        """)
        
    html_list.append("</ul>")
    
    return "".join(html_list)

def load_template_content(repo, file_path):
    """Fetches and decodes the content of a file from the GitHub repository."""
    try:
        content_file = repo.get_contents(file_path)
        content = base64.b64decode(content_file.content).decode('utf-8')
        return content
    except Exception as e:
        print(f"FATAL ERROR: Could not read file '{file_path}' from repository '{repo.full_name}'.")
        print(f"Error details: {e}")
        return None

def get_content_sha(repo, file_path):
    """Fetches the SHA hash for a file, needed for updating file content."""
    try:
        content_file = repo.get_contents(file_path)
        return content_file.sha
    except Exception:
        return None

def replace_in_content(content, placeholder, replacement):
    """Performs a global search and replace."""
    if not placeholder:
        raise ValueError("Placeholder for replacement cannot be an empty string.")
    return content.replace(placeholder, replacement)

def process_city_deployment(g, user, token, city_name):
    """Orchestrates the data fetching, content replacement, and repository deployment for a single city."""
    
    repo_name = f"{REPO_PREFIX}{city_name.replace(' ', '-').replace(',', '')}{REPO_SUFFIX}"
    print(f"\n=======================================================")
    print(f"STARTING DEPLOYMENT FOR: {city_name} (Repo: {repo_name})")
    print(f"=======================================================")
    
    # 1. GEOCODING
    print("-> Geocoding city with OSM Nominatim...")
    lat, lon, bbox = get_coordinates_and_bbox(city_name)
    if not lat:
        print(f"COMPLETED DEPLOYMENT FOR: {city_name} (Skipped due to geocoding error)")
        return
    
    # 2. WIKIPEDIA SUMMARY
    summary_text = get_wikipedia_summary(city_name)

    # 3. OVERPASS DATA FETCH with proper delays
    print("-> Querying Overpass for amenities...")
    
    # Libraries
    print("   -> Fetching libraries...")
    libraries_data = get_overpass_data(bbox, 'amenity=library')
    
    # Bars
    print("   -> Fetching bars...")
    bars_data = get_overpass_data(bbox, 'amenity=bar')
    
    # Restaurants
    print("   -> Fetching restaurants...")
    restaurants_data = get_overpass_data(bbox, 'amenity=restaurant')
    
    # Barbers
    print("   -> Fetching barbers...")
    barbers_data = get_overpass_data(bbox, 'shop=barber')

    # 4. GET TEMPLATE CONTENT
    try:
        source_repo = g.get_user().get_repo(BASE_REPO_NAME) 
        html_content = load_template_content(source_repo, TEMPLATE_FILE_NAME)
        if html_content is None:
            raise Exception("Failed to load template content.")
    except Exception as e:
        print(f"FATAL ERROR during deployment for {city_name}: {e}")
        return
        
    # 5. TEMPLATE REPLACEMENT LOGIC
    print("-> Applying template replacements...")
    
    # Clean city name for display (use just the city part)
    display_city_name = city_name.split('-')[0].split(',')[0].strip()
    
    # a. Replace all occurrences of Oklahoma City
    html_content = replace_in_content(html_content, "Oklahoma City", display_city_name)
    html_content = replace_in_content(html_content, "OKC", display_city_name)
    
    # b. Replace latitude and longitude
    html_content = replace_in_content(html_content, "35.4676", str(lat))
    html_content = replace_in_content(html_content, "-97.5164", str(lon))
    
    # c. Replace Wikipedia summary
    original_okc_paragraph = "Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team."
    html_content = replace_in_content(html_content, original_okc_paragraph, summary_text)
    
    # d. Replace venue lists
    html_content = replace_in_content(html_content, "<!-- LIBRARIES_PLACEHOLDER -->", get_venue_html(libraries_data, "libraries"))
    html_content = replace_in_content(html_content, "<!-- BARS_PLACEHOLDER -->", get_venue_html(bars_data, "bars"))
    html_content = replace_in_content(html_content, "<!-- RESTAURANTS_PLACEHOLDER -->", get_venue_html(restaurants_data, "restaurants"))
    html_content = replace_in_content(html_content, "<!-- BARBERS_PLACEHOLDER -->", get_venue_html(barbers_data, "barbers"))
    
    # e. Add citations
    osm_citation = "© OpenStreetMap contributors"
    html_content = replace_in_content(html_content, "<!-- OSM_CITATION_PLACEHOLDER -->", osm_citation)
    
    noaa_citation = "NOAA National Weather Service"
    html_content = replace_in_content(html_content, "<!-- NOAA_CITATION_PLACEHOLDER -->", noaa_citation)

    # 6. REPOSITORY CREATION/UPDATE
    print(f"-> Checking for existing repository: {repo_name}...")
    try:
        target_repo = g.get_user().get_repo(repo_name)
        
        # If it exists, update the file
        print(f"   -> Repository exists. Updating {TEMPLATE_FILE_NAME}...")
        sha = get_content_sha(target_repo, TEMPLATE_FILE_NAME)
        if sha:
            target_repo.update_file(
                path=TEMPLATE_FILE_NAME,
                message=f"Auto-update: Redeploying website for {display_city_name}",
                content=html_content,
                sha=sha,
                branch="main"
            )
            print(f"   -> Successfully updated file in existing repo: {repo_name}")
        else:
            target_repo.create_file(
                path=TEMPLATE_FILE_NAME,
                message=f"Auto-deploy: Initial deployment for {display_city_name}",
                content=html_content,
                branch="main"
            )
            print(f"   -> Created new file in existing repo: {repo_name}")

    except Exception as e:
        if "404" in str(e) or "Not Found" in str(e):
            # Repository does not exist, create it
            print(f"   -> Repository not found. Creating new repository: {repo_name}")
            try:
                new_repo = user.create_repo(
                    name=repo_name,
                    description=f"Local Deployment Hub for The Titan Software Guild in {display_city_name}",
                    private=False,
                    has_issues=True,
                    has_projects=False,
                    has_wiki=False,
                    auto_init=False
                )
                
                # Create the initial index.html file in the new repo
                new_repo.create_file(
                    path=TEMPLATE_FILE_NAME,
                    message=f"Auto-deploy: Initial deployment for {display_city_name}",
                    content=html_content,
                    branch="main"
                )
                print(f"   -> Successfully created new repo and deployed website for {display_city_name}")
                
                # GitHub Pages setup - will need to be enabled manually in repo settings
                print(f"   -> Note: GitHub Pages must be enabled manually in the repository settings.")
                
            except Exception as creation_e:
                print(f"FATAL ERROR during new repository creation/setup for {display_city_name}: {creation_e}")
                return
        else:
            print(f"FATAL ERROR during repository operation for {display_city_name}: {e}")
            return

    print(f"COMPLETED DEPLOYMENT FOR: {city_name}")

def main():
    """Main function to handle authentication and city list processing."""
    
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("FATAL: GH_TOKEN environment variable not set. Exiting.")
        sys.exit(1)

    try:
        g = Github(auth=github.Auth.Token(token))
        user = g.get_user()
        print(f"Authenticated as: {user.login}")
    except Exception as e:
        print(f"FATAL: Failed to authenticate with GitHub. Error: {e}")
        sys.exit(1)

    all_cities = get_city_list(CITY_LIST_FILE)
    if not all_cities:
        print("No cities found in new.txt. Nothing to deploy.")
        return

    print(f"Found {len(all_cities)} cities to deploy.")

    for i, city in enumerate(all_cities):
        if i > 0:
            print(f"\n--- PAUSING for {DEPLOYMENT_DELAY_SECONDS} seconds before next deployment... ---")
            time.sleep(DEPLOYMENT_DELAY_SECONDS)
        
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DEPLOYMENTS COMPLETE ***")

if __name__ == "__main__":
    main()
