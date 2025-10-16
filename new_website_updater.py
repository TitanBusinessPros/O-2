import os
import re
import json
import requests
from github import Github
from time import sleep
# --- NEW IMPORTS REQUIRED FOR DATA FETCHING ---
import wikipedia
from geopy.geocoders import Nominatim

# --- Configuration ---
# NOTE: The user should ensure this file is the template content, renamed to 'index.html'
SOURCE_HTML_FILE = 'index.html' 
# REFERENCE TO THE NEW TXT FILE
CITIES_FILE = 'new.txt' 
# Placeholder to be replaced
SEARCH_TERM = 'Oklahoma City'
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
# File paths and content for the new files
VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html'
THANKYOU_FILE_NAME = 'thankyou.html' # Changed to .html for better GH Pages compatibility
# ---------------------

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def get_thankyou_content(user_login, repo_name):
    """Generates the thank you HTML with the correct, dynamic redirect URL."""
    # Base URL for GitHub Pages is typically: https://USERNAME.github.io/REPO_NAME/
    redirect_url = f"https://{user_login}.github.io/{repo_name}/index.html"

    # Content of the Google verification file (as a plain string)
    verification_content = 'google-site-verification: google51f4be664899794b6.html'

    # Content for the Thank You redirect page
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

# ***************************************************************
# --- NEW DATA ACQUISITION FUNCTIONS ---
# ***************************************************************

def get_wikipedia_summary(city):
    """Function 7: Fetches a short summary paragraph about the city from Wikipedia."""
    try:
        # Set to find 3 sentences max
        return wikipedia.summary(city, sentences=3, auto_suggest=False, redirect=True)
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
        return f"Welcome to {city}! This is where ordinary people become extraordinary creators. The Titan Software Guild is the future."
    except Exception as e:
        print(f"Error fetching Wikipedia data for {city}: {e}")
        return f"Welcome to {city}! This is where ordinary people become extraordinary creators. The Titan Software Guild is the future."

def get_lat_lon(city):
    """Function 1: Fetches the longitude and latitude for the city."""
    try:
        geolocator = Nominatim(user_agent="titan_software_guild_deployer")
        location = geolocator.geocode(city)
        if location:
            return str(location.latitude), str(location.longitude)
        return '35.4822', '-97.5215' # Default to OKC coordinates on failure
    except Exception as e:
        print(f"Error fetching geolocation for {city}: {e}")
        return '35.4822', '-97.5215'

def find_local_poi_data(city):
    """
    Functions 3, 4, 5, 6: MOCK DATA
    NOTE: In a live scenario, this must be replaced with a real API call.
    """
    # These are MOCK links and names for demonstration. 
    return {
        # Function 3: Local Libraries
        'libraries': [
            {'name': f'{city} Central Library', 'url': f'https://google.com/search?q={city}+library+1'},
            {'name': f'North {city} Community Library', 'url': f'https://google.com/search?q={city}+library+2'},
            {'name': f'{city} Tech Center Library', 'url': f'https://google.com/search?q={city}+library+3'}
        ],
        # Function 4: Local Bars (Replaces content in the 'jobs-list' section)
        'bars': [
            {'name': 'The Code Bar & Grill', 'url': f'https://google.com/search?q={city}+bar+1'},
            {'name': 'The Python Pub', 'url': f'https://google.com/search?q={city}+bar+2'},
            {'name': 'The Git Grind Coffee', 'url': f'https://google.com/search?q={city}+bar+3'}
        ],
        # Function 5: Restaurants (Replaces content in the 'news-list' section)
        'restaurants': [
            {'name': 'The Data Diner', 'url': f'https://google.com/search?q={city}+restaurant+1'},
            {'name': 'The Algorithm Eatery', 'url': f'https://google.com/search?q={city}+restaurant+2'},
            {'name': 'SQL Steakhouse', 'url': f'https://google.com/search?q={city}+restaurant+3'}
        ],
        # Function 6: Barber Shops
        'barbers': [
            {'name': f'{city} Slickers Barbershop', 'url': f'https://google.com/search?q={city}+barber+1'},
            {'name': 'The Fade Factory', 'url': f'https://google.com/search?q={city}+barber+2'},
            {'name': 'Executive Cuts - {city}', 'url': f'https://google.com/search?q={city}+barber+3'}
        ],
        # Function 2: Local Conditions Word
        'conditions_word': 'Warm and Cloudless' # This will be used to replace the hardcoded weather phrase
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
    # Note: Using the format <a href="..." target="_blank">Name</a>
    return ''.join([
        f'<li><a href="{poi["url"]}" target="_blank" rel="noopener noreferrer" style="color: var(--text-light); text-decoration: none;">**{poi["name"]}**</a></li>'
        for poi in poi_list
    ])


# ***************************************************************
# --- CORE DEPLOYMENT LOGIC MODIFIED ---
# ***************************************************************

def process_city_deployment(g, user, token, city):
    """Handles the full creation, update, and deployment cycle for a single city."""

    # 3. Define New Repository Details
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DUPLICATE DEPLOYMENT FOR: {city} ---")
    print(f"Targeting new repository: {new_repo_name}")

    # 4. Read and Modify HTML Content
    base_html_content = read_file(SOURCE_HTML_FILE)

    # 4a. Fetch all dynamic data for the new city
    city_data = get_city_data(city)

    # ----------------------------------------------------
    # CORE MODIFICATIONS TO REFLECT CURRENT CITY
    # ----------------------------------------------------

    # Function 8 (Original/Base): Replace ALL 'Oklahoma City' occurrences
    # This updates Title, Meta Description, Hero Subtitle, and all general mentions.
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the site title (more explicit search)
    new_site_title = f"The Titan Software Guild: {city} Deployment Hub"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)

    # Function 7: Replace Wiki Paragraph (The Greatest Time in Human History section)
    # Targets the unique paragraph text in the 'mission' section.
    # The regex targets the specific paragraph content starting after the section title
    wiki_search_pattern = r'(<div id="greatest-time-section" class="mission-text">)(.*?)(</p>)'
    
    # NOTE: The template.html structure is simpler and does not have a unique id="greatest-time-section" on a div.
    # It has a <section class="mission"> and two <p> tags with class="mission-text".
    
    # We will target the first major description paragraph that talks about OKC (snippet 8).
    # This paragraph starts with: "Oklahoma City is famous for its historical roots..."
    # And ends with: "...that change lives."
    okc_wiki_block = r'Oklahoma City is famous for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA\'s Thunder team.'
    
    new_content = new_content.replace(
        okc_wiki_block,
        city_data['wiki_summary']
    )
    
    print("Function 7: Replaced Wikipedia summary block.")

    # Function 2: Replace Current Local Conditions Word
    # This targets the hardcoded temperature/time string inside the local hub card.
    # The text is: ☀️ 75°F <span>Humidity: 45% | **2:44 PM CDT**</span>
    weather_placeholder = r'☀️ 75°F <span>Humidity: 45% | \*\*2:44 PM CDT\*\*</span>'
    new_conditions = f'{city_data["poi"]["conditions_word"]} <span>Check local weather for details.</span>'

    new_content = re.sub(
        weather_placeholder, 
        re.escape(new_conditions),
        new_content
    )
    print(f"Function 2: Replaced local conditions with: {city_data['poi']['conditions_word']}")

    # Functions 3, 4, 5, 6: Replace POI Links inside the <ul> tags (Robust method)
    # Map: (ul_class, poi_data_key) -> ul_class must match template.html
    poi_map = [
        # Function 3: Local Libraries
        ('library-list', 'libraries'), 
        # Function 4: Local Bars (Replacing the 'jobs-list' content based on position)
        ('jobs-list', 'bars'), 
        # Function 5: Restaurants (Replacing the 'news-list' content based on position)
        ('news-list', 'restaurants'), 
        # Function 6: Barber Shops
        ('barber-list', 'barbers')
    ]

    for ul_class, data_key in poi_map:
        new_list_html = create_list_items(city_data['poi'][data_key])
        
        # Regex to find the entire <ul> block by its class and replace its *contents*
        # Pattern: (<ul class="[class]">)(.*?)(</ul>)
        # Flags: DOTALL to match newlines within the list, IGNORECASE just in case.
        ul_pattern = rf'(<ul class="{re.escape(ul_class)}">)(.*?)(</ul>)'
        
        # Replace the list content. r'\1' and r'\3' are the captured <ul> tags.
        new_content = re.sub(
            ul_pattern, 
            r'\1' + new_list_html + r'\3', 
            new_content, 
            flags=re.DOTALL | re.IGNORECASE
        )
        print(f"Function {poi_map.index((ul_class, data_key)) + 3}: Replaced POI list for {data_key.capitalize()}.")


    # Function 1: Replace longitude & latitude (Requires user to add this to index.html)
    # RECOMMENDED HTML TO ADD BEFORE </body>:
    # <input type="hidden" id="deploy-lat" value="35.4822">
    # <input type="hidden" id="deploy-lon" value="-97.5215">
    
    lat_search_pattern = r'(id="deploy-lat"\s*value=")([^"]*)(")'
    lon_search_pattern = r'(id="deploy-lon"\s*value=")([^"]*)(")'
    
    new_content = re.sub(lat_search_pattern, r'\1' + city_data['latitude'] + r'\3', new_content)
    new_content = re.sub(lon_search_pattern, r'\1' + city_data['longitude'] + r'\3', new_content)
    print("Function 1: Replaced Longitude and Latitude values.")

    # ----------------------------------------------------
    # END CORE MODIFICATIONS
    # ----------------------------------------------------

    # 5. Connect to GitHub and Create/Get Repo (Remaining code unchanged)
    
    repo = None
    try:
        # Get or Create Repository
        # ... (GitHub connection and repo handling code)
        try:
            repo = user.get_repo(new_repo_name)
            print(f"Repository already exists. Proceeding to update.")
        except Exception:
            print(f"Repository does not exist. Creating new repository.")
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                auto_init=True
            )
            sleep(5) 

        # --- NEW FILE COMMITS ---
        verification_content, thankyou_html = get_thankyou_content(user.login, new_repo_name)
        
        # 6a. Commit Google Verification File
        # ... (Commit verification file code)
        try:
            contents = repo.get_contents(VERIFICATION_FILE_NAME, ref="main")
            repo.update_file(path=VERIFICATION_FILE_NAME, message="Update Google verification file", content=verification_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=VERIFICATION_FILE_NAME, message="Add Google verification file for Console", content=verification_content, branch="main")
        print(f"Committed {VERIFICATION_FILE_NAME}.")

        # 6b. Commit Thank You Redirect File
        # ... (Commit thankyou file code)
        try:
            contents = repo.get_contents(THANKYOU_FILE_NAME, ref="main")
            repo.update_file(path=THANKYOU_FILE_NAME, message="Update thankyou redirect file", content=thankyou_html, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=THANKYOU_FILE_NAME, message="Add thankyou redirect page", content=thankyou_html, branch="main")
        print(f"Committed {THANKYOU_FILE_NAME}.")
        
        # 6c. Commit Core Files
        # ... (Commit index.html and .nojekyll)

        # Add/Update the .nojekyll file
        try:
            contents = repo.get_contents(".nojekyll", ref="main")
            repo.update_file(path=".nojekyll", message="Update .nojekyll file", content="", sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=".nojekyll", message="Add .nojekyll to enable direct HTML serving", content="", branch="main")
        print("Added/Updated .nojekyll file.")

        # Commit the generated index.html
        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(path="index.html", message=f"Update site content for {city}", content=new_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path="index.html", message=f"Initial site deployment for {city}", content=new_content, branch="main")
        print("Committed updated index.html to the new repository.")

        
        # 7. Enable GitHub Pages using direct requests API call
        # ... (GitHub Pages API configuration code)
        pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
        data = {'source': {'branch': 'main', 'path': '/'}}
        
        r = requests.post(pages_api_url, headers=headers, json=data)
        
        if r.status_code == 201:
            print("Successfully configured GitHub Pages (New Site).")
        elif r.status_code == 409:
            r = requests.put(pages_api_url, headers=headers, json=data)
            if r.status_code == 204:
                print("Successfully updated GitHub Pages configuration.")

        # 8. Fetch and Display Final URL
        # ... (Final URL retrieval code)
        pages_info_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        r = requests.get(pages_info_url, headers=headers)
        
        try:
            pages_url = json.loads(r.text).get('html_url', 'URL not yet active or failed to retrieve.')
        except:
            pages_url = 'URL failed to retrieve, check repo settings manually.'
        print(f"Final Repository URL: {repo.html_url}")
        print(f"Live site URL: {pages_url}")
        print(f"--- {city} DUPLICATE DEPLOYMENT COMPLETE ---")

    except Exception as e:
        print(f"A critical error occurred during {city} duplicate deployment: {e}")
        pass # Allow other cities to proceed


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
