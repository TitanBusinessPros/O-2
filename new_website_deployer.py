import os
import sys
import requests
import json
import re
import base64
from time import sleep
from github import Github
from textwrap import dedent

# --- CONFIGURATION ---
# !!! IMPORTANT: CHANGE THIS TO THE NAME OF YOUR REPOSITORY (e.g., "O-2") !!!
BASE_REPO_NAME = "O-2"  # <-- VERIFY THIS NAME IS CORRECT (e.g., "O-2")
REPO_PREFIX = "The-"
REPO_SUFFIX = "-Software-Guild"
TEMPLATE_FILE_NAME = "index.html"
CITY_LIST_FILE = "new.txt"

# Delay between each *city deployment* to avoid hitting API rate limits (in seconds)
DEPLOYMENT_DELAY_SECONDS = 180

# Overpass API call delay (in seconds) to avoid per-request limits
OVERPASS_CALL_DELAY_SECONDS = 2
# ---------------------


# --- HELPER FUNCTIONS ---

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
    """
    search_query = f"{city_name}, USA"
    url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
    
    # Required custom User-Agent for Nominatim
    headers = {'User-Agent': 'Titan-Software-Guild-Deployment-Script/1.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            
            # The boundingbox list from Nominatim is typically [min_lat, max_lat, min_lon, max_lon]
            bbox_list = [float(b) for b in data[0]['boundingbox']]
            
            # Overpass QL format (S, W, N, E)
            s_lat, n_lat, w_lon, e_lon = bbox_list[0], bbox_list[1], bbox_list[2], bbox_list[3]
            bbox = f"{s_lat},{w_lon},{n_lat},{e_lon}" 
            
            print(f"   -> Found Lat: {lat}, Lon: {lon}, BBox (S,W,N,E): {bbox}")
            return lat, lon, bbox
        else:
            print(f"   -> WARNING: Could not geocode city '{city_name}'. Skipping.")
            return None, None, None
            
    except requests.RequestException as e:
        print(f"   -> ERROR geocoding '{city_name}': {e}")
        return None, None, None


def get_overpass_data(bbox, amenity_tag, limit=3):
    """Uses Overpass API to get a list of venues based on amenity tag and BBox."""
    sleep(OVERPASS_CALL_DELAY_SECONDS)
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass QL query:
    overpass_query = dedent(f"""
    [out:json][timeout:25];
    (
      node["{amenity_tag}"~"."][name](bbox:{bbox});
      way["{amenity_tag}"~"."][name](bbox:{bbox});
      relation["{amenity_tag}"~"."][name](bbox:{bbox});
    );
    out center {limit};
    """).strip()
    
    try:
        response = requests.post(overpass_url, data={'data': overpass_query}, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"   -> ERROR querying Overpass for {amenity_tag}: {e}")
        return None


def get_wikidata_summary(city_name):
    """
    Fetches a descriptive summary for the city from the Wikidata API.
    """
    print("-> Fetching city summary from Wikidata...")
    
    # Required User-Agent header to avoid 403 Forbidden error
    headers = {'User-Agent': 'Titan-Software-Guild-Deployment-Script/1.0 (Contact: user@example.com)'}
    
    # Step 1: Search for the entity (QID)
    search_url = (
        "https://www.wikidata.org/w/api.php?action=wbsearchentities&search="
        f"{city_name} city&language=en&format=json&limit=1"
    )
    try:
        search_res = requests.get(search_url, headers=headers, timeout=10)
        search_res.raise_for_status()
        search_data = search_res.json()
        
        if not search_data['search']:
            print("   -> WARNING: Wikidata search failed.")
            return f"No detailed history found for {city_name} on Wikidata."
            
        qid = search_data['search'][0]['id']
        
        # Step 2: Fetch the summary (description/sitelinks)
        entity_url = (
            "https://www.wikidata.org/w/api.php?action=wbgetentities&ids="
            f"{qid}&format=json&languages=en&props=descriptions"
        )
        entity_res = requests.get(entity_url, headers=headers, timeout=10)
        entity_res.raise_for_status()
        entity_data = entity_res.json()
        
        description = entity_data['entities'][qid]['descriptions']['en']['value']
        
        if description and 'city' in description.lower():
            summary = (
                f"{city_name} is a major metropolitan area. {description}. "
                "Data provided by Wikimedia/Wikidata."
            )
            return summary
        else:
            return (
                f"{city_name} is the current focal point of the software development revolution. "
                "The Titan Software Guild aims to be the center of this movement in the area. "
                "Data provided by Wikimedia/Wikidata."
            )
            
    except requests.RequestException as e:
        print(f"   -> ERROR fetching Wikidata summary: {e}")
        return f"Could not retrieve city summary from Wikidata due to an error."


def get_venue_html(overpass_data):
    """Formats Overpass venue data into an HTML list."""
    if not overpass_data or not overpass_data.get('elements'):
        return "<ul><li>No local venues found in this category.</li></ul>"
    
    html_list = ["<ul>"]
    
    for element in overpass_data['elements']:
        name = element['tags'].get('name', 'Unnamed Location')
        street = element['tags'].get('addr:street', 'Unknown Street')
        city = element['tags'].get('addr:city', 'The City')
        
        # Link to Google Maps
        if 'lat' in element and 'lon' in element:
            link = f"https://www.google.com/maps/search/?api=1&query={element['lat']},{element['lon']}"
        else:
            link = "https://www.google.com/maps"
            
        html_list.append(dedent(f"""
            <li>
                <a href="{link}" target="_blank">{name}</a>
                <p class="address-line">{street}, {city}</p>
            </li>
        """))
        
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
    # Safety check: Prevent MemoryError by ensuring placeholder is not an empty string
    if not placeholder:
        raise ValueError("Placeholder for replacement cannot be an empty string.")
    return content.replace(placeholder, replacement)


# --- MAIN LOGIC ---

def process_city_deployment(g, user, token, city_name):
    """Orchestrates the data fetching, content replacement, and repository deployment for a single city."""
    
    repo_name = f"{REPO_PREFIX}{city_name.replace(' ', '-')}{REPO_SUFFIX}"
    print(f"\n=======================================================")
    print(f"STARTING DEPLOYMENT FOR: {city_name} (Repo: {repo_name})")
    print(f"=======================================================")
    
    # 1. GEOCODING AND WIKIDATA FETCH
    print("-> Geocoding city with OSM Nominatim...")
    lat, lon, bbox = get_coordinates_and_bbox(city_name)
    if not lat:
        print(f"COMPLETED DEPLOYMENT FOR: {city_name} (Skipped due to geocoding error/warning)")
        return
        
    summary_text = get_wikidata_summary(city_name)

    # 2. OVERPASS DATA FETCH (Libraries, Bars, Restaurants, Barbers)
    print("-> Querying Overpass for amenities...")
    libraries_data = get_overpass_data(bbox, 'amenity=library')
    bars_data = get_overpass_data(bbox, 'amenity=bar')
    restaurants_data = get_overpass_data(bbox, 'amenity=restaurant')
    barbers_data = get_overpass_data(bbox, 'shop=barber')

    # 3. GET TEMPLATE CONTENT
    try:
        source_repo = g.get_user().get_repo(BASE_REPO_NAME) 
        html_content = load_template_content(source_repo, TEMPLATE_FILE_NAME)
        if html_content is None:
            raise Exception("Failed to load template content.")
    except Exception as e:
        print(f"FATAL ERROR during deployment for {city_name}: {e}")
        return
        
    # 4. TEMPLATE REPLACEMENT LOGIC
    print("-> Applying template replacements...")
    
    # a. City Name (for Title and description)
    html_content = replace_in_content(html_content, "Oklahoma City Deployment Hub", f"{city_name} Deployment Hub")
    html_content = replace_in_content(html_content, "Oklahoma City", city_name)
    html_content = replace_in_content(html_content, "OKC", city_name)
    
    # b. Lat/Lon for weather updater
    # FIX: Correct placeholders for Latitude and Longitude (lines 257-258)
    html_content = replace_in_content(html_content, "", str(lat))
    html_content = replace_in_content(html_content, "", str(lon))
    
    # c. Wikidata Summary (Must match the exact text in the template)
    original_summary_text = dedent("""
        **Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team.**
        The Titan Software Guild is where ordinary people become extraordinary creators. Where dreams transform into apps, games, websites, and intelligent systems that change lives.
    """).strip()
    
    replacement_summary = (
        f"**{summary_text}**\n"
        "The Titan Software Guild is where ordinary people become extraordinary creators. Where dreams transform into apps, games, websites, and intelligent systems that change lives."
    ).strip()
    
    html_content = replace_in_content(html_content, original_summary_text, replacement_summary)
    
    # d. Venue Lists (Libraries, Bars, Restaurants, Barbers)
    html_content = replace_in_content(html_content, "", get_venue_html(libraries_data))
    html_content = replace_in_content(html_content, "", get_venue_html(bars_data))
    html_content = replace_in_content(html_content, "", get_venue_html(restaurants_data))
    html_content = replace_in_content(html_content, "", get_venue_html(barbers_data))
    
    # e. Weather Section (Initial data injection)
    import datetime
    current_time_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC (Initial Deployment)")
    html_content = replace_in_content(html_content, "", current_time_utc)


    # 5. REPOSITORY CREATION/UPDATE
    print(f"-> Checking for existing repository: {repo_name}...")
    try:
        target_repo = g.get_user().get_repo(repo_name)
        
        # If it exists, update the file
        print(f"   -> Repository exists. Updating {TEMPLATE_FILE_NAME}...")
        sha = get_content_sha(target_repo, TEMPLATE_FILE_NAME)
        if sha:
            target_repo.update_file(
                path=TEMPLATE_FILE_NAME,
                message=f"Auto-update: Redploying website for {city_name}",
                content=html_content,
                sha=sha,
                branch="main"
            )
            print(f"   -> Successfully updated file in existing repo: {repo_name}")
        else:
             target_repo.create_file(
                path=TEMPLATE_FILE_NAME,
                message=f"Auto-deploy: Initial deployment for {city_name}",
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
                    description=f"Local Deployment Hub for The Titan Software Guild in {city_name}",
                    private=False,
                    has_issues=True,
                    has_projects=False,
                    has_wiki=False,
                    auto_init=False
                )
                
                # Create the initial index.html file in the new repo
                new_repo.create_file(
                    path=TEMPLATE_FILE_NAME,
                    message=f"Auto-deploy: Initial deployment for {city_name}",
                    content=html_content,
                    branch="main"
                )
                print(f"   -> Successfully created new repo and deployed website for {city_name}")
                
                # Set up GitHub Pages for the newly created repo
                print(f"   -> Setting up GitHub Pages for {repo_name}...")
                new_repo.enable_pages(
                    source={"branch": "main", "path": "/"}
                )
                print(f"   -> GitHub Pages successfully enabled.")
                
            except Exception as creation_e:
                print(f"FATAL ERROR during new repository creation/setup for {city_name}: {creation_e}")
                return
        else:
            print(f"FATAL ERROR during repository operation for {city_name}: {e}")
            return

    print(f"COMPLETED DEPLOYMENT FOR: {city_name}")


def main():
    """Main function to handle authentication and city list processing."""
    
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("FATAL: GH_TOKEN environment variable not set. Exiting.")
        sys.exit(1)

    try:
        g = Github(token)
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
            sleep(DEPLOYMENT_DELAY_SECONDS)
        
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DUPLICATE DEPLOYMENTS COMPLETE ***")


if __name__ == "__main__":
    main()
