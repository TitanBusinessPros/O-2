import os
import re
import json
import requests
from github import Github
from time import sleep
# Required for Functions 1, 7 (data fetching)
import wikipedia
from geopy.geocoders import Nominatim

# --- Configuration ---
SOURCE_HTML_FILE = 'template.html' 
OUTPUT_HTML_FILE = 'index.html' 
CITIES_FILE = 'new.txt' 
SEARCH_TERM = 'Oklahoma City' 
ORIGINAL_WIKI_BLOCK = 'Oklahoma City is famous for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA\'s Thunder team.'
WEATHER_PLACEHOLDER = r'☀️ 75°F <span>Humidity: 45% \| \*\*2:44 PM CDT\*\*</span>'
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html'
THANKYOU_FILE_NAME = 'thankyou.html' 
# ---------------------

def read_file(filename):
    """Reads the content of a file, with a fallback check for 'index.html'."""
    if not os.path.exists(filename):
        if filename == 'template.html' and os.path.exists('index.html'):
            filename = 'index.html'
        else:
            raise FileNotFoundError(f"Required source HTML file not found: {filename}")
            
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def get_thankyou_content(user_login, repo_name):
    """Generates thank you HTML (required for deployment success)."""
    redirect_url = f"https://{user_login}.github.io/{repo_name}/index.html"
    verification_content = 'google-site-verification: google51f4be664899794b6.html'
    thankyou_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="refresh" content="0; url={redirect_url}">
</head>
<body>Redirecting...</body>
</html>"""
    return verification_content, thankyou_html

def get_wikipedia_summary(city):
    """(Function 7): Gets data for the Wiki block (kept for deployment stability)."""
    try:
        clean_city = city.split(',')[0].strip()
        summary = wikipedia.summary(clean_city, sentences=3, auto_suggest=True, redirect=True)
        return summary.replace('\n', ' ')
    except:
        return f"Welcome to {city}! This is where ordinary people become extraordinary creators."

def get_lat_lon(city):
    """Function 1: Fetches the longitude and latitude using the full City, State string."""
    try:
        # Use the full city, state string for best geolocation accuracy
        geolocator = Nominatim(user_agent="titan_software_guild_deployer")
        location = geolocator.geocode(city)
        if location:
            return str(location.latitude), str(location.longitude)
        return '35.4822', '-97.5215' 
    except Exception as e:
        print(f"Error fetching geolocation for {city}: {e}")
        return '35.4822', '-97.5215'

# MOCK functions must be included to avoid NameErrors in the main script
def find_local_poi_data(city): return {'libraries': [], 'bars': [], 'restaurants': [], 'barbers': [], 'conditions_word': 'Warm and Cloudless'}
def create_list_items(poi_list): return ''

def get_city_data(city):
    """Compiles all required dynamic data for the city."""
    wiki_summary = get_wikipedia_summary(city)
    latitude, longitude = get_lat_lon(city)
    poi_data = find_local_poi_data(city)
    return {
        'wiki_summary': wiki_summary,
        'latitude': latitude,
        'longitude': longitude,
        'poi': poi_data
    }


def process_city_deployment(g, user, token, city):
    """Handles the full creation, update, and deployment cycle for a single city."""

    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DEPLOYMENT FOR: {city} ---")
    
    base_html_content = read_file(SOURCE_HTML_FILE)
    city_data = get_city_data(city)

    # Function 8 (Base): Replace ALL 'Oklahoma City' occurrences globally.
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # --- FUNCTION 1 FOCUS: Replace/Insert longitude & latitude ---
    lat_search_pattern = r'(id="deploy-lat"\s*value=")([^"]*)(")'
    lon_search_pattern = r'(id="deploy-lon"\s*value=")([^"]*)(")'
    
    # CRITICAL FIX: Use callable for replacement to treat data as literal text (fixes re.PatternError)
    def lat_replacer(match):
        return match.group(1) + city_data['latitude'] + match.group(3)

    def lon_replacer(match):
        return match.group(1) + city_data['longitude'] + match.group(3)

    # 1. Attempt replacement and count the occurrences
    lat_replaced, lat_count = re.subn(lat_search_pattern, lat_replacer, new_content)
    lon_replaced, lon_count = re.subn(lon_search_pattern, lon_replacer, lat_replaced)
    
    new_content = lon_replaced

    # 2. Check if insertion is needed (if tags did not exist)
    if lat_count == 0 or lon_count == 0:
        coordinate_inputs = f'\n<input type="hidden" id="deploy-lat" value="{city_data["latitude"]}">\n<input type="hidden" id="deploy-lon" value="{city_data["longitude"]}">\n'
        new_content = re.sub(r'(</body>)', coordinate_inputs + r'\1', new_content, flags=re.IGNORECASE)

    print(f"Function 1: Successfully set Longitude ({city_data['longitude']}) and Latitude ({city_data['latitude']}).")
    # --- END FUNCTION 1 FOCUS ---
    
    # (Other Functions must be in the code block to run, but are omitted from print statements)
    
    # 5. Connect to GitHub and Create/Get Repo (Deployment Logic)
    repo = None
    try:
        # Get or Create Repository
        try:
            repo = user.get_repo(new_repo_name)
        except Exception:
            repo = user.create_repo(name=new_repo_name, description=f"Site for {city}", private=False, auto_init=True)
            sleep(5) 

        # --- COMMIT FILES ---
        verification_content, thankyou_html = get_thankyou_content(user.login, new_repo_name)
        
        def commit_file(path, message, content):
            try:
                contents = repo.get_contents(path, ref="main")
                repo.update_file(path=path, message=message, content=content, sha=contents.sha, branch="main")
            except Exception:
                repo.create_file(path=path, message=message, content=content, branch="main")

        commit_file(VERIFICATION_FILE_NAME, "Update Google verification file", verification_content)
        commit_file(THANKYOU_FILE_NAME, "Update thankyou redirect file", thankyou_html)
        commit_file(".nojekyll", "Add .nojekyll", "")
        
        # Commit the MODIFIED content to the final 'index.html' file
        commit_file(OUTPUT_HTML_FILE, f"Update site content for {city}", new_content)
        print(f"Committed MODIFIED {OUTPUT_HTML_FILE} to the new repository.")

        
        # 7. Enable GitHub Pages 
        pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
        data = {'source': {'branch': 'main', 'path': '/'}}
        requests.put(pages_api_url, headers=headers, json=data) # Attempt PUT/Update
        requests.post(pages_api_url, headers=headers, json=data) # Attempt POST/Create

        # 8. Fetch and Display Final URL
        pages_info_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        r = requests.get(pages_info_url, headers=headers)
        try:
            pages_url = json.loads(r.text).get('html_url', f"https://{user.login}.github.io/{new_repo_name}/")
        except:
            pages_url = f"https://{user.login}.github.io/{new_repo_name}/"
            
        print(f"Live site URL: {pages_url}")
        print(f"--- {city} DEPLOYMENT COMPLETE ---")

    except Exception as e:
        print(f"A critical error occurred during {city} deployment: {e}")
        pass 


def main():
    token = os.environ.get('GH_TOKEN')
    delay = float(os.environ.get('DEPLOY_DELAY', 200)) 

    if not token:
        raise EnvironmentError("Missing GH_TOKEN environment variable. Cannot proceed.")

    cities_data = read_file(CITIES_FILE)
    all_cities = [c.strip() for c in cities_data.splitlines() if c.strip()]

    if not all_cities:
        print(f"Error: {CITIES_FILE} is empty. No deployments to run.")
        return

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = Github(token)
        user = g.get_user()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to GitHub API: {e}")

    for i, city in enumerate(all_cities):
        if i > 0:
            print(f"\n--- PAUSING for {delay} seconds (3 minutes) before next deployment... ---")
            sleep(delay)
        
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DEPLOYMENTS COMPLETE ***")


if __name__ == "__main__":
    main()
