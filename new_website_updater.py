import os
import re
import json
import requests
from github import Github
from time import sleep
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
            print(f"Using 'index.html' as source, as '{filename}' was not found.")
            filename = 'index.html'
        else:
            raise FileNotFoundError(f"Required source HTML file not found: {filename}")
            
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def get_thankyou_content(user_login, repo_name):
    """Generates the thank you HTML with the correct, dynamic redirect URL."""
    redirect_url = f"https://{user_login}.github.io/{repo_name}/index.html"
    verification_content = 'google-site-verification: google51f4be664899794b6.html'
    thankyou_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You!</title>
    <meta http-equiv="refresh" content="0; url={redirect_url}">
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #0a0a0f;
            color: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }}
        h1 {{
            color: #00d4ff;
        }}
        a {{
            color: #00d4ff;
            text-decoration: none;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div>
        <h1>Thank you for contacting us!</h1>
        <p>Redirecting you back to the new guild homepage...</p>
        <a href="{redirect_url}">Click here if you are not redirected</a>
    </div>
</body>
</html>"""
    return verification_content, thankyou_html

def get_wikipedia_summary(city):
    """Function 7: Fetches a short summary paragraph about the city. Uses only City name for better lookup."""
    try:
        clean_city = city.split(',')[0].strip()
        summary = wikipedia.summary(clean_city, sentences=3, auto_suggest=True, redirect=True)
        return summary.replace('\n', ' ')
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
        return f"Welcome to {city}! This is where ordinary people become extraordinary creators. The Titan Software Guild is the future."
    except Exception as e:
        print(f"Error fetching Wikipedia data for {city}: {e}")
        return f"Welcome to {city}! This is where ordinary people become extraordinary creators. The Titan Software Guild is the future."

def get_lat_lon(city):
    """Function 1: Fetches the longitude and latitude. Uses full City, State for precision."""
    try:
        geolocator = Nominatim(user_agent="titan_software_guild_deployer")
        location = geolocator.geocode(city)
        if location:
            return str(location.latitude), str(location.longitude)
        return '35.4822', '-97.5215' 
    except Exception as e:
        print(f"Error fetching geolocation for {city}: {e}")
        return '35.4822', '-97.5215'

def find_local_poi_data(city):
    """
    Functions 3, 4, 5, 6: MOCK DATA. Uses full City, State in search queries.
    """
    return {
        'libraries': [
            {'name': f'{city} Central Library', 'url': f'https://google.com/search?q={city}+library+1'},
            {'name': f'North {city} Community Library', 'url': f'https://google.com/search?q={city}+library+2'},
            {'name': f'{city} Tech Center Library', 'url': f'https://google.com/search?q={city}+library+3'}
        ],
        'bars': [
            {'name': 'The Code Bar & Grill', 'url': f'https://google.com/search?q={city}+bar+1'},
            {'name': 'The Python Pub', 'url': f'https://google.com/search?q={city}+bar+2'},
            {'name': 'The Git Grind Coffee', 'url': f'https://google.com/search?q={city}+bar+3'}
        ],
        'restaurants': [
            {'name': 'The Data Diner', 'url': f'https://google.com/search?q={city}+restaurant+1'},
            {'name': 'The Algorithm Eatery', 'url': f'https://google.com/search?q={city}+restaurant+2'},
            {'name': 'SQL Steakhouse', 'url': f'https://google.com/search?q={city}+restaurant+3'}
        ],
        'barbers': [
            {'name': f'{city} Slickers Barbershop', 'url': f'https://google.com/search?q={city}+barber+1'},
            {'name': 'The Fade Factory', 'url': f'https://google.com/search?q={city}+barber+2'},
            {'name': 'Executive Cuts - {city}', 'url': f'https://google.com/search?q={city}+barber+3'}
        ],
        'conditions_word': 'Warm and Cloudless' 
    }

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

def create_list_items(poi_list):
    """Generates the HTML <li> list items for POI data."""
    return ''.join([
        f'<li><a href="{poi["url"]}" target="_blank" rel="noopener noreferrer" style="color: var(--text-light); text-decoration: none;">**{poi["name"]}**</a></li>'
        for poi in poi_list
    ])


def process_city_deployment(g, user, token, city):
    """Handles the full creation, update, and deployment cycle for a single city."""

    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DUPLICATE DEPLOYMENT FOR: {city} ---")
    
    base_html_content = read_file(SOURCE_HTML_FILE)
    city_data = get_city_data(city)

    # ----------------------------------------------------
    # CORE MODIFICATIONS TO REFLECT CURRENT CITY
    # ----------------------------------------------------

    # Function 8 (Base): Replace ALL 'Oklahoma City' occurrences globally.
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the site title
    new_site_title = f"The Titan Software Guild: {city} Deployment Hub"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)

    # Function 7: Replace the specific Wiki Paragraph block.
    new_content = new_content.replace(
        ORIGINAL_WIKI_BLOCK,
        city_data['wiki_summary']
    )
    print("Function 7: Successfully replaced Wikipedia summary block.")

    # Function 2: Replace Current Local Conditions Word
    new_conditions = f'{city_data["poi"]["conditions_word"]} <span>Check local weather for details.</span>'

    new_content = re.sub(
        re.escape(WEATHER_PLACEHOLDER), 
        re.escape(new_conditions),
        new_content
    )
    print(f"Function 2: Replaced local conditions with: {city_data['poi']['conditions_word']}")

    # Functions 3, 4, 5, 6: Replace POI Links inside the <ul> tags
    poi_map = [
        ('library-list', 'libraries'),  # Function 3
        ('jobs-list', 'bars'),          # Function 4 
        ('news-list', 'restaurants'),   # Function 5 
        ('barber-list', 'barbers')      # Function 6
    ]

    for ul_class, data_key in poi_map:
        new_list_html = create_list_items(city_data['poi'][data_key])
        ul_pattern = rf'(<ul class="{re.escape(ul_class)}">)(.*?)(</ul>)'
        new_content = re.sub(
            ul_pattern, 
            r'\1' + new_list_html + r'\3', 
            new_content, 
            flags=re.DOTALL | re.IGNORECASE
        )
        print(f"Function {poi_map.index((ul_class, data_key)) + 3}: Replaced POI list for {data_key.capitalize()}.")


    # Function 1 (CRITICAL FIX): Replace/Insert longitude & latitude 
    lat_search_pattern = r'(id="deploy-lat"\s*value=")([^"]*)(")'
    lon_search_pattern = r'(id="deploy-lon"\s*value=")([^"]*)(")'
    
    # Use callable for replacement to treat data as literal text (fixes re.PatternError)
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
        print("Warning: Coordinate input tags not found. Inserting them before </body>.")
        coordinate_inputs = f'\n<input type="hidden" id="deploy-lat" value="{city_data["latitude"]}">\n<input type="hidden" id="deploy-lon" value="{city_data["longitude"]}">\n'
        new_content = re.sub(r'(</body>)', coordinate_inputs + r'\1', new_content, flags=re.IGNORECASE)

    print("Function 1: Replaced/Inserted Longitude and Latitude values.")

    # ----------------------------------------------------
    # END CORE MODIFICATIONS
    # ----------------------------------------------------

    # 5. Connect to GitHub and Create/Get Repo (Deployment Logic)
    repo = None
    try:
        # Get or Create Repository
        try:
            repo = user.get_repo(new_repo_name)
        except Exception:
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                auto_init=True
            )
            sleep(5) 

        # --- COMMIT FILES ---
        verification_content, thankyou_html = get_thankyou_content(user.login, new_repo_name)
        
        # Helper function for commiting/updating files
        def commit_file(path, message, content):
            try:
                contents = repo.get_contents(path, ref="main")
                repo.update_file(path=path, message=message, content=content, sha=contents.sha, branch="main")
            except Exception:
                repo.create_file(path=path, message=message, content=content, branch="main")

        commit_file(VERIFICATION_FILE_NAME, "Update Google verification file", verification_content)
        commit_file(THANKYOU_FILE_NAME, "Update thankyou redirect file", thankyou_html)
        commit_file(".nojekyll", "Add .nojekyll to enable direct HTML serving", "")
        
        # Commit the MODIFIED content to the final 'index.html' file
        commit_file(OUTPUT_HTML_FILE, f"Update site content for {city}", new_content)
        print(f"Committed MODIFIED {OUTPUT_HTML_FILE} to the new repository.")

        
        # 7. Enable GitHub Pages 
        pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
        data = {'source': {'branch': 'main', 'path': '/'}}
        
        # Use PUT (update) then POST (create) for reliable configuration
        r = requests.put(pages_api_url, headers=headers, json=data)
        if r.status_code not in [201, 204]:
            r = requests.post(pages_api_url, headers=headers, json=data)

        if r.status_code in [201, 204]:
            print("Successfully configured GitHub Pages (New Site).")
        else:
            print(f"Warning: Pages configuration failed. Status Code: {r.status_code}")


        # 8. Fetch and Display Final URL
        pages_info_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        r = requests.get(pages_info_url, headers=headers)
        
        # Fallback to calculated URL if API retrieval fails
        try:
            pages_url = json.loads(r.text).get('html_url', f"https://{user.login}.github.io/{new_repo_name}/")
        except:
            pages_url = f"https://{user.login}.github.io/{new_repo_name}/"
            
        print(f"Live site URL: {pages_url}")
        print(f"--- {city} DUPLICATE DEPLOYMENT COMPLETE ---")

    except Exception as e:
        print(f"A critical error occurred during {city} duplicate deployment: {e}")
        pass 


def main():
    """Main execution function to loop through all cities."""
    
    token = os.environ.get('GH_TOKEN')
    delay = float(os.environ.get('DEPLOY_DELAY', 200)) 

    if not token:
        raise EnvironmentError("Missing GH_TOKEN environment variable. Cannot proceed.")

    # 1. Read All Cities
    cities_data = read_file(CITIES_FILE)
    all_cities = [c.strip() for c in cities_data.splitlines() if c.strip()]

    if not all_cities:
        print(f"Error: {CITIES_FILE} is empty. No deployments to run.")
        return

    # 2. Initialize GitHub connection (once)
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = Github(token)
        user = g.get_user()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to GitHub API: {e}")

    # 3. Iterate through all cities with a delay
    for i, city in enumerate(all_cities):
        if i > 0:
            print(f"\n--- PAUSING for {delay} seconds (3 minutes) before next deployment... ---")
            sleep(delay)
        
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DUPLICATE DEPLOYMENTS COMPLETE ***")


if __name__ == "__main__":
    main()
