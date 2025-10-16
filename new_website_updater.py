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
# REFERENCE TO THE NEW TXT FILE
CITIES_FILE = 'new.txt'
# Placeholder to be replaced
SEARCH_TERM = 'Oklahoma City'
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
# File paths and content for the new files
VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html'
THANKYOU_FILE_NAME = 'thankyou.index'
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
            background: #1e293b;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }}
        h1 {{
            color: #38bdf8;
        }}
        a {{
            color: #38bdf8;
            text-decoration: none;
            font-weight: bold;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div>
        <h1>Thank you for contacting us!</h1>
        <p>Redirecting you back to our homepage...</p>
        <a href="index.html">Click here if you are not redirected</a>
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
        return f"Information about {city} could not be found. Here is a generic city description."
    except Exception as e:
        print(f"Error fetching Wikipedia data for {city}: {e}")
        return f"Information about {city} could not be found due to an API error."

def get_lat_lon(city):
    """Function 1: Fetches the longitude and latitude for the city."""
    try:
        geolocator = Nominatim(user_agent="titan_software_guild_deployer")
        location = geolocator.geocode(city)
        if location:
            return location.latitude, location.longitude
        return '35.4822', '-97.5215' # Default to OKC coordinates on failure
    except Exception as e:
        print(f"Error fetching geolocation for {city}: {e}")
        return '35.4822', '-97.5215'

def find_local_poi_data(city):
    """
    Functions 3, 4, 5, 6: MOCK DATA
    In a live scenario, this would call a Places API (Google, Yelp, etc.) 
    to fetch real, up-to-date local businesses based on the city name.
    """
    # NOTE: These are MOCK links and names for demonstration. 
    # They should be replaced with real API calls and links.
    return {
        # Function 3: Local Libraries
        'libraries': [
            {'name': f'{city} Main Library', 'url': '#'},
            {'name': f'South {city} Branch', 'url': '#'},
            {'name': f'{city} Tech Hub Library', 'url': '#'}
        ],
        # Function 4: Local Bars
        'bars': [
            {'name': 'The Code Bar', 'url': '#'},
            {'name': 'The Python Pub', 'url': '#'},
            {'name': 'The Git Grind', 'url': '#'}
        ],
        # Function 5: Restaurants
        'restaurants': [
            {'name': 'The Data Diner', 'url': '#'},
            {'name': 'The Algorithm Eatery', 'url': '#'},
            {'name': 'SQL Steakhouse', 'url': '#'}
        ],
        # Function 6: Barber Shops
        'barbers': [
            {'name': 'City Slickers Barbershop', 'url': '#'},
            {'name': 'The Fade Factory', 'url': '#'},
            {'name': 'Executive Cuts', 'url': '#'}
        ],
        # Function 2: Local Conditions Word
        'conditions_word': 'Sunny with a chance of code'
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

    # Function 8 (Original): Replace ALL 'Oklahoma City' occurrences
    new_content = base_html_content.replace(SEARCH_TERM, city)

    # Replace the site title (already implemented)
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)

    # Function 7: Replace Wiki Paragraph (The Greatest Time in Human History section)
    # The regex targets the specific paragraph content within that section
    wiki_search_pattern = r'(<div id="greatest-time-section".*?<p>)(.*?)(</p>.*?)'
    new_content = re.sub(
        wiki_search_pattern,
        r'\1' + re.escape(city_data['wiki_summary']) + r'\3',
        new_content,
        flags=re.DOTALL
    )

    # Function 2: Replace Current Local Conditions Word
    # Assuming the placeholder is 'Sunny with a chance of code'
    new_content = new_content.replace('Sunny with a chance of code', city_data['poi']['conditions_word'])


    # Functions 3, 4, 5, 6: Replace POI Links
    # This loop is generic and requires the HTML to have distinct sections 
    # to target the correct link sets. We will target by the section title/comment.
    
    # Structure for link replacement:
    # We assume the HTML section for each category (libraries, bars, restaurants, barbers) 
    # contains 3 <a href> tags wrapped in a distinct div/comment block.
    # The regex targets the entire 3-link block using a clear comment/title as the anchor.
    
    poi_replacements = [
        ('Local Library Access', city_data['poi']['libraries']),
        ('Local spots to meet', city_data['poi']['bars']),
        ('restaurants near me', city_data['poi']['restaurants']),
        ('Get a Haircut and Get a Real Job!', city_data['poi']['barbers'])
    ]

    for anchor_text, poi_list in poi_replacements:
        # Create the new HTML block of links
        new_links_html = ''.join([
            f'<a href="{poi["url"]}" target="_blank" class="link-item">{poi["name"]}</a>'
            for poi in poi_list
        ])
        
        # Regex to find the existing 3-link grid under the specific title/comment
        # This is a complex pattern to ensure accuracy: finding the section title 
        # and then replacing the content of the following <div> with class="link-grid".
        # WARNING: This regex requires specific, consistent HTML structure in index.html
        poi_pattern = rf'(.*?<div class="link-grid">)(.*?)(</div>)'
        
        # We search and replace the content *inside* the <div class="link-grid"> for each category
        # If your HTML structure is simpler, a simpler regex may be needed.
        new_content = re.sub(
            poi_pattern, 
            r'\1' + new_links_html + r'\3', 
            new_content, 
            flags=re.DOTALL | re.IGNORECASE
        )


    # Function 1: Replace longitude & latitude near footer
    # Assuming there are hidden inputs or a meta tag near the footer/end of body
    # with IDs like 'deploy-lat' and 'deploy-lon'.
    lat_search_pattern = r'(id="deploy-lat"\s*value=")([^"]*)(")'
    lon_search_pattern = r'(id="deploy-lon"\s*value=")([^"]*)(")'
    
    new_content = re.sub(lat_search_pattern, r'\1' + str(city_data['latitude']) + r'\3', new_content)
    new_content = re.sub(lon_search_pattern, r'\1' + str(city_data['longitude']) + r'\3', new_content)

    # 5. Connect to GitHub and Create/Get Repo (Remaining code unchanged)
    # ... (rest of the original process_city_deployment function)

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
        pass # Allow other cities to proceed


def main():
    """Main execution function to loop through all cities."""
    
    token = os.environ.get('GH_TOKEN')
    # Default 180 seconds (3 mins) delay is increased slightly to account for API calls
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
            print(f"\n--- PAUSING for {delay} seconds before next deployment... ---")
            sleep(delay)
        
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DUPLICATE DEPLOYMENTS COMPLETE ***")


if __name__ == "__main__":
    # Ensure the script is saved as new_website_updater.py
    main()
