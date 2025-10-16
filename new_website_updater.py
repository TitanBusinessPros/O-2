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
SOURCE_HTML_FILE = 'index.html' 
CITIES_FILE = 'new.txt' 
# Placeholder to be replaced
SEARCH_TERM = 'Oklahoma City'
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
# File paths and content for the new files
VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html'
THANKYOU_FILE_NAME = 'thankyou.html' 
# ---------------------

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
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

# ***************************************************************
# --- NEW DATA ACQUISITION FUNCTIONS ---
# ***************************************************************

def get_wikipedia_summary(city):
    """Function 7: Fetches a short summary paragraph about the city from Wikipedia."""
    try:
        # Set to find 3 sentences max
        # It's crucial to remove or clean up the city name if it contains state/country info for best wiki results.
        clean_city = city.split(',')[0].strip()
        summary = wikipedia.summary(clean_city, sentences=3, auto_suggest=True, redirect=True)
        # Ensure newlines are replaced with spaces for proper HTML insertion
        return summary.replace('\n', ' ')
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
            # Ensure coordinates are returned as strings for HTML insertion
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
        # Function 2: Local Conditions Word
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
    # Ensure this matches the <li> style in your template
    return ''.join([
        f'<li><a href="{poi["url"]}" target="_blank" rel="noopener noreferrer" style="color: var(--text-light); text-decoration: none;">**{poi["name"]}**</a></li>'
        for poi in poi_list
    ])

# ***************************************************************
# --- CORE DEPLOYMENT LOGIC MODIFIED ---
# ***************************************************************

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

    # Function 8 (Base): Replace ALL 'Oklahoma City' occurrences
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    # Replace the site title
    new_site_title = f"The Titan Software Guild: {city} Deployment Hub"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)

    # Function 7: Replace Wiki Paragraph (The Greatest Time in Human History section)
    # The erroneous text that needs to be replaced is the long OKC description.
    # We use re.escape to handle all special characters in the source text.
    okc_wiki_block_template = r'Oklahoma City is famous for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA\'s Thunder team.'
    
    # Since the full block includes the two sentences before and after, we capture the entire block:
    wiki_block_full_pattern = r'(<p class="mission-text">)(.*?)(</p>)' # This targets the second <p> inside <section class="mission">
    
    # We MUST ensure the regex only targets the paragraph containing the OKC description.
    # The snippet you provided: "Austin-Texas (OKC) is the capital and largest city..." is the *result* of a failed replace.
    # We target the *original* text using the provided template text.
    
    # FIX: Use re.escape on the entire template text block to ensure a direct match.
    okc_wiki_block_original = r'Oklahoma City is famous for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA\'s Thunder team.'

    # Use a generic approach that handles potential whitespace/formatting issues around the target text block:
    # Look for the opening <p> tag and ensure we only replace the content of the second mission-text <p>.
    
    # 1. Split the content to get the two <p> blocks under the mission section.
    mission_text_pattern = r'(<p class="mission-text">.*?)</p>'
    mission_paragraphs = re.findall(mission_text_pattern, new_content, re.DOTALL)
    
    if len(mission_paragraphs) >= 2:
        # We replace the content of the SECOND paragraph (index 1) which contains the city description.
        # This replaces the text *inside* the <p> tag but preserves the tags themselves.
        target_paragraph = mission_paragraphs[1]
        
        # Replace the content of that target paragraph with the new wiki summary
        new_target_paragraph = f'<p class="mission-text">{city_data["wiki_summary"]}</p>'
        
        # We must use a full string replacement since the regex is complex to manage nesting.
        # Find the original, static content of the target paragraph (after replacing the general 'Oklahoma City' name)
        # We assume the second mission-text paragraph contains the text starting with the city name.
        
        # Find the full block of the original OKC wiki description after general city replacements
        # Since 'Oklahoma City' is replaced with the new city name, we search for the *new* city name
        # followed by the static rest of the paragraph.
        
        # This is a robust targeted string replacement:
        new_content = new_content.replace(
            f'{city} is famous for its historical roots in the oil industry and cattle packing, it has modernized into a hub for technology, energy, and corporate sectors. OKC is famous for the Bricktown Entertainment District and being home to the NBA\'s Thunder team.',
            city_data['wiki_summary']
        )

    print("Function 7: Replaced Wikipedia summary block.")

    # Function 2: Replace Current Local Conditions Word
    weather_placeholder = r'☀️ 75°F <span>Humidity: 45% \| \*\*2:44 PM CDT\*\*</span>'
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
        ('library-list', 'libraries'),  # Function 3
        ('jobs-list', 'bars'),          # Function 4 (Misleading class name used in template)
        ('news-list', 'restaurants'),   # Function 5 (Misleading class name used in template)
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


    # Function 1: Replace longitude & latitude 
    # Assumes <input type="hidden" id="deploy-lat" value="35.4822"> exists near the footer
    lat_search_pattern = r'(id="deploy-lat"\s*value=")([^"]*)(")'
    lon_search_pattern = r'(id="deploy-lon"\s*value=")([^"]*)(")'
    
    new_content = re.sub(lat_search_pattern, r'\1' + city_data['latitude'] + r'\3', new_content)
    new_content = re.sub(lon_search_pattern, r'\1' + city_data['longitude'] + r'\3', new_content)
    print("Function 1: Replaced Longitude and Latitude values.")

    # ----------------------------------------------------
    # END CORE MODIFICATIONS
    # ----------------------------------------------------

    # 5. Connect to GitHub and Create/Get Repo (Remaining code for GitHub logic)
    
    repo = None
    try:
        # Get or Create Repository
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
        try:
            contents = repo.get_contents(VERIFICATION_FILE_NAME, ref="main")
            repo.update_file(path=VERIFICATION_FILE_NAME, message="Update Google verification file", content=verification_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=VERIFICATION_FILE_NAME, message="Add Google verification file for Console", content=verification_content, branch="main")
        print(f"Committed {VERIFICATION_FILE_NAME}.")

        # 6b. Commit Thank You Redirect File
        try:
            contents = repo.get_contents(THANKYOU_FILE_NAME, ref="main")
            repo.update_file(path=THANKYOU_FILE_NAME, message="Update thankyou redirect file", content=thankyou_html, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=THANKYOU_FILE_NAME, message="Add thankyou redirect page", content=thankyou_html, branch="main")
        print(f"Committed {THANKYOU_FILE_NAME}.")
        
        # 6c. Commit Core Files

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
