import os
import re
import json
import requests 
from github import Github
from time import sleep
import yaml
import wikipedia

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

# API Keys (you'll need to add these to your GitHub secrets)
OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY', 'your_opencage_api_key')
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', 'your_google_places_api_key')

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def get_city_coordinates(city_name):
    """Get latitude and longitude for a city using OpenCage Geocoding API."""
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={city_name}&key={OPENCAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if data['results']:
            geometry = data['results'][0]['geometry']
            return geometry['lat'], geometry['lng']
        else:
            print(f"Could not find coordinates for {city_name}")
            return 35.4676, -97.5164  # Default to Oklahoma City coordinates
    except Exception as e:
        print(f"Error getting coordinates for {city_name}: {e}")
        return 35.4676, -97.5164

def get_places_by_type(city_name, place_type, limit=3):
    """Get places of specific type in a city using Google Places API."""
    try:
        # First get city coordinates
        lat, lng = get_city_coordinates(city_name)
        
        # Search for places
        if place_type == "library":
            search_query = f"library in {city_name}"
        elif place_type == "bar":
            search_query = f"bar in {city_name}"
        elif place_type == "restaurant":
            search_query = f"restaurant in {city_name}"
        elif place_type == "barber":
            search_query = f"barber shop in {city_name}"
        else:
            search_query = f"{place_type} in {city_name}"
            
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': search_query,
            'key': GOOGLE_PLACES_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        places = []
        for place in data.get('results', [])[:limit]:
            places.append(place['name'])
            
        return places
    except Exception as e:
        print(f"Error getting {place_type} for {city_name}: {e}")
        # Return default places if API fails
        if place_type == "library":
            return ["Downtown Library", "Public Library", "Community Library"]
        elif place_type == "bar":
            return ["Local Pub", "Sports Bar", "Lounge"]
        elif place_type == "restaurant":
            return ["Local Diner", "Family Restaurant", "Cafe"]
        elif place_type == "barber":
            return ["Classic Barbershop", "Modern Cuts", "Style Salon"]
        return []

def get_wikipedia_summary(city_name):
    """Get Wikipedia summary for a city."""
    try:
        wikipedia.set_lang("en")
        page = wikipedia.page(city_name)
        summary = wikipedia.summary(city_name, sentences=3)
        return summary
    except Exception as e:
        print(f"Error getting Wikipedia summary for {city_name}: {e}")
        return f"{city_name} is a vibrant city with a rich history and diverse community."

def replace_html_section(html_content, section_id, new_content):
    """Replace content within a specific HTML section."""
    pattern = f'<div[^>]*id=["\']{section_id}["\'][^>]*>.*?</div>'
    replacement = f'<div id="{section_id}">{new_content}</div>'
    return re.sub(pattern, replacement, html_content, flags=re.DOTALL)

def create_libraries_section(libraries):
    """Create HTML for libraries section."""
    html = '<h3>Local Library Access</h3><ul>'
    for library in libraries:
        html += f'<li>{library}</li>'
    html += '</ul>'
    return html

def create_bars_section(bars):
    """Create HTML for bars section."""
    html = '<h3>Local Spots to Meet</h3><ul>'
    for bar in bars:
        html += f'<li>{bar}</li>'
    html += '</ul>'
    return html

def create_restaurants_section(restaurants):
    """Create HTML for restaurants section."""
    html = '<h3>Restaurants Near Me</h3><ul>'
    for restaurant in restaurants:
        html += f'<li>{restaurant}</li>'
    html += '</ul>'
    return html

def create_barbers_section(barbers):
    """Create HTML for barbers section."""
    html = '<h3>Get a Haircut and Get a Real Job!</h3><ul>'
    for barber in barbers:
        html += f'<li>{barber}</li>'
    html += '</ul>'
    return html

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

def process_city_deployment(g, user, token, city):
    """Handles the full creation, update, and deployment cycle for a single city."""
    
    # 3. Define New Repository Details
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DUPLICATE DEPLOYMENT FOR: {city} ---")
    print(f"Targeting new repository: {new_repo_name}")
    
    # 4. Read and Modify HTML Content
    base_html_content = read_file(SOURCE_HTML_FILE)
    
    # Get city-specific data
    print(f"Fetching data for {city}...")
    lat, lng = get_city_coordinates(city)
    libraries = get_places_by_type(city, "library")
    bars = get_places_by_type(city, "bar")
    restaurants = get_places_by_type(city, "restaurant")
    barbers = get_places_by_type(city, "barber")
    wiki_summary = get_wikipedia_summary(city)
    
    # Replace the city placeholder and the title
    new_content = base_html_content.replace(SEARCH_TERM, city)
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # 1. Replace longitude & latitude
    new_content = re.sub(r'data-lat="[^"]*"', f'data-lat="{lat}"', new_content)
    new_content = re.sub(r'data-lng="[^"]*"', f'data-lng="{lng}"', new_content)
    
    # 2. Replace current local conditions (assuming there's a section for this)
    # This would depend on your HTML structure - you might need to adjust the selectors
    
    # 3. Replace libraries section
    libraries_html = create_libraries_section(libraries)
    new_content = replace_html_section(new_content, 'libraries', libraries_html)
    
    # 4. Replace bars section
    bars_html = create_bars_section(bars)
    new_content = replace_html_section(new_content, 'bars', bars_html)
    
    # 5. Replace restaurants section
    restaurants_html = create_restaurants_section(restaurants)
    new_content = replace_html_section(new_content, 'restaurants', restaurants_html)
    
    # 6. Replace barbers section
    barbers_html = create_barbers_section(barbers)
    new_content = replace_html_section(new_content, 'barbers', barbers_html)
    
    # 7. Replace Wikipedia section
    wiki_pattern = r'<div[^>]*id=["\']wikipedia["\'][^>]*>.*?</div>'
    wiki_replacement = f'<div id="wikipedia"><p>{wiki_summary}</p></div>'
    new_content = re.sub(wiki_pattern, wiki_replacement, new_content, flags=re.DOTALL)
    
    # 8. Any remaining Oklahoma City references
    new_content = new_content.replace('Oklahoma City', city)
    
    # 5. Connect to GitHub and Create/Get Repo
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
    delay = float(os.environ.get('DEPLOY_DELAY', 180)) # Default 180 seconds (3 mins)

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
