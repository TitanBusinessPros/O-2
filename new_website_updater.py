import requests
import json
import re
from github import Github
from time import sleep

# --- CONFIGURATION ---
BASE_REPO_NAME = "city-website-base"  # Name of the current repo where this script runs
REPO_PREFIX = "The-"
REPO_SUFFIX = "-Software-Guild"
CITIES_FILE = "new.txt" # The file to read new cities from
# ---------------------

# --- API ENDPOINTS ---
OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
# ---------------------

# --- HELPERS ---

def get_coordinates_and_bbox(city_name):
    """Uses OSM Nominatim to get Lat/Lon and Bounding Box for a city."""
    print(f"-> Geocoding {city_name} with OSM Nominatim...")
    headers = {'User-Agent': 'TitanSoftwareGuildUpdater/1.0'} # Essential for OSM/NOAA
    params = {
        'q': city_name,
        'format': 'json',
        'limit': 1
    }
    
    try:
        response = requests.get(OSM_NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            # Bounding box is needed for Overpass (min_lat, min_lon, max_lat, max_lon)
            bbox_list = [float(b) for b in data[0]['boundingbox']]
            # Rearrange to the format Overpass QL likes: S, W, N, E (min_lat, min_lon, max_lat, max_lon)
            bbox = f"{bbox_list[0]},{bbox_list[2]},{bbox_list[1]},{bbox_list[3]}" 
            
            print(f"   -> Found Lat: {lat}, Lon: {lon}, BBox: {bbox}")
            return lat, lon, bbox
    except Exception as e:
        print(f"   -> ERROR during geocoding: {e}")
        return None, None, None
    return None, None, None


def get_wikidata_summary(city_name):
    """Uses Wikidata SPARQL to get a summary paragraph about the city."""
    print("-> Fetching city summary from Wikidata...")
    # This query searches for a city entity and retrieves its description (P1082) and population (P1082)
    # The 'service wikibase:label' translates the Q-item into a human-readable label.
    sparql_query = f"""
    SELECT ?cityDescription ?population
    WHERE
    {{
      ?city rdfs:label "{city_name}"@en .
      ?city wdt:P31 wd:Q515 . # Instance of city
      OPTIONAL {{ ?city schema:description ?cityDescription . FILTER (lang(?cityDescription) = "en") }}
      OPTIONAL {{ ?city wdt:P1082 ?population . }} # Population
      
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    LIMIT 1
    """
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'TitanSoftwareGuildUpdater/1.0'
    }
    params = {'query': sparql_query}
    
    try:
        response = requests.get(WIKIDATA_SPARQL_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        bindings = data.get('results', {}).get('bindings', [])
        if bindings:
            description = bindings[0].get('cityDescription', {}).get('value', f'A major city named {city_name}.')
            population = bindings[0].get('population', {}).get('value')

            summary = f"**{city_name}** is described as: {description}."
            if population:
                 # Format population with commas
                formatted_pop = f"{int(population):,}"
                summary += f" As of the latest records, it has a population of **{formatted_pop}**."
                
            summary += " This data is sourced from Wikidata/Wikimedia."
            print("   -> Wikidata summary fetched.")
            return summary
        
    except Exception as e:
        print(f"   -> ERROR fetching Wikidata summary: {e}. Using fallback text.")
        return f"**{city_name}** is a major city known for its vibrant community and growth. This information is sourced from Wikidata/Wikimedia."


def get_overpass_data(bbox, amenity_tag, limit=3):
    """Uses Overpass API to get a list of venues based on amenity tag and BBox."""
    print(f"-> Querying Overpass for {amenity_tag}...")
    
    # Overpass QL query: find nodes/ways/relations of the given amenity type within the BBox, 
    # sort by distance from center, and return names.
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["{amenity_tag}"]({bbox});
      way["{amenity_tag}"]({bbox});
      relation["{amenity_tag}"]({bbox});
    );
    (._;
        node(nwr);
    );
    out center {limit};
    """
    
    data = {'data': overpass_query}
    headers = {'User-Agent': 'TitanSoftwareGuildUpdater/1.0'} # Essential for OSM/NOAA
    
    try:
        response = requests.post(OVERPASS_API_URL, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        results = response.json().get('elements', [])
        
        # Filter and extract unique names
        names = []
        for element in results:
            name = element.get('tags', {}).get('name')
            if name and name not in names:
                names.append(name)
            if len(names) >= limit:
                break
        
        print(f"   -> Found {len(names)} results for {amenity_tag}.")
        # Format as HTML list items
        if not names:
            return "<li>No local spots found via OpenStreetMap for this category.</li>"
        
        return "\n".join([f"<li>{name}</li>" for name in names])

    except Exception as e:
        print(f"   -> ERROR querying Overpass for {amenity_tag}: {e}")
        return "<li>ERROR: Could not fetch local spots.</li>"

def process_city_deployment(g, user, token, city):
    """
    Handles the entire process for a single city:
    1. Gets Geo Data (OSM Nominatim)
    2. Gets Wikidata Summary
    3. Gets Local Spots (Overpass API)
    4. Creates new repo, replaces content, and deploys.
    """
    repo_name = f"{REPO_PREFIX}{city.replace(' ', '-')}{REPO_SUFFIX}"
    print(f"\n=======================================================")
    print(f"STARTING DEPLOYMENT FOR: {city} (Repo: {repo_name})")
    print(f"=======================================================")

    # 1. FETCH ALL DATA
    lat, lon, bbox = get_coordinates_and_bbox(city)
    if not lat:
        print(f"SKIPPING {city}: Could not find coordinates.")
        return

    wikidata_text = get_wikidata_summary(city)
    
    # Run Overpass queries with required 5-second sleep delay
    delay = 5 # seconds
    
    libraries_html = get_overpass_data(bbox, 'amenity=library')
    sleep(delay) # **REQUIRED DELAY**
    
    bars_html = get_overpass_data(bbox, 'amenity=bar')
    sleep(delay) # **REQUIRED DELAY**
    
    restaurants_html = get_overpass_data(bbox, 'amenity=restaurant')
    sleep(delay) # **REQUIRED DELAY**

    barbers_html = get_overpass_data(bbox, 'shop=barber')
    
    # Weather is handled by the separate daily workflow, so we insert the initial placeholder here
    # The weather updater script will target this ID
    initial_weather_html = """
        <div id="local-weather-forecast">
            <h2>Current Local Conditions</h2>
            <p>Weather data will be updated daily by a separate scheduled GitHub workflow (Source: NOAA National Weather Service).</p>
            <p class="forecast-summary">Please check back in a few hours for the first forecast update.</p>
        </div>
        <p class="weather-timestamp">Data last updated: </p>
    """
    
    # 2. CREATE AND CLONE REPO
    try:
        source_repo = g.get_user().get_repo(BASE_REPO_NAME)
        new_repo = g.get_user().create_repo(
            repo_name,
            description=f"A static website for {city} created by Titan Software Guild.",
            private=False,
            has_issues=False,
            has_wiki=False,
            has_downloads=False,
            auto_init=False
        )
        print(f"Successfully created new repository: {new_repo.full_name}")
        
        # 3. GET/UPDATE INDEX.HTML CONTENT
        # Get content from the source repo's index.html
        contents = source_repo.get_contents("index.html")
        html_content = contents.decoded_content.decode()

        # Perform all replacements
        html_content = html_content.replace('', lon)
        html_content = html_content.replace('', lat)
        
        # Replace the paragraph block (Wikidata)
        # Target the full block provided in the notes to avoid partial replacement
        old_wikidata_text = """**Oklahoma City (OKC) is the capital and largest city of Oklahoma. It is the 20th most populous city in the United States and serves as the primary gateway to the state. Known for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA's Thunder team.**"""
        html_content = html_content.replace(old_wikidata_text, wikidata_text)

        # Replace Local Spots Lists
        html_content = html_content.replace('', libraries_html)
        html_content = html_content.replace('', bars_html)
        html_content = html_content.replace('', restaurants_html)
        html_content = html_content.replace('', barbers_html)
        
        # Replace the full current weather section with the placeholder
        # Note: We are replacing the original weather section with a new div structure for the updater to target later
        
        # The replacement logic for weather placeholder needs a unique target:
        # Assuming the original index.html has a div that says "CURRENT LOCAL CONDITIONS"
        # We need a robust way to replace the OLD weather text with the new initial_weather_html structure.
        # Since the user notes give the full paragraph of the Wikidata section, we can assume a placeholder
        # needs to be used for the weather too if the old content is unknown.
        
        # For simplicity, we'll assume a clear placeholder (or the content around the weather placeholder 
        # needs to be adjusted in the HTML source file before running this script).
        
        # If the original file uses a unique marker for the weather, we will use it. 
        # Since the user didn't provide one, we will use a unique HTML comment:
        html_content = html_content.replace('', initial_weather_html)
        
        # 4. COMMIT AND PUSH
        new_repo.create_file(
            "index.html",
            f"Initial content and deployment for {city}",
            html_content
        )
        print("Pushed updated index.html to new repo.")
        
        # 5. ENABLE GITHUB PAGES (Optional, but good practice if not automated elsewhere)
        try:
            new_repo.get_pages().enable_pages(source="main", path="/")
            print("GitHub Pages enabled.")
        except Exception:
            # This sometimes fails if pages is already enabled or requires a separate deployment step.
            print("Could not enable GitHub Pages (might be enabled by default or require separate step).")
            
    except Exception as e:
        print(f"FATAL ERROR during deployment for {city}: {e}")
        
    print(f"COMPLETED DEPLOYMENT FOR: {city}")


def main():
    """Main function to orchestrate the deployment."""
    # 1. AUTHENTICATE
    token = os.environ.get('GH_TOKEN')
    if not token:
        print("FATAL: GH_TOKEN environment variable not set.")
        return

    g = Github(token)
    user = g.get_user().login

    # 2. READ CITIES
    try:
        with open(CITIES_FILE, 'r') as f:
            # Read cities and remove empty lines/whitespace
            all_cities = [city.strip() for city in f.readlines() if city.strip()]
    except FileNotFoundError:
        print(f"FATAL: City list file '{CITIES_FILE}' not found.")
        return

    if not all_cities:
        print(f"No cities found in '{CITIES_FILE}'. Exiting.")
        return

    # 3. Iterate through all cities with a 3-minute delay
    delay = 180  # 3 minutes (180 seconds)
    
    print(f"Found {len(all_cities)} cities to deploy.")
    
    for i, city in enumerate(all_cities):
        if i > 0:
            print(f"\n--- PAUSING for {delay} seconds (3 minutes) before next deployment... ---")
            sleep(delay)
        
        # The city name needs to be capitalized for better API results
        process_city_deployment(g, user, token, city.title())
    
    print("\n\n*** ALL DUPLICATE DEPLOYMENTS COMPLETE ***")


if __name__ == "__main__":
    # Ensure all required libraries are imported
    import os 
    main()
