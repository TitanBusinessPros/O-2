# new_website_updater.py

import os
import re
import json
import requests
import wikipediaapi
from github import Github
from time import sleep

# --- Configuration ---
SOURCE_HTML_FILE = 'index.html'
[cite_start]CITIES_FILE = 'new.txt'  # REFERENCE TO THE NEW TXT FILE [cite: 21]
[cite_start]SEARCH_TERM = 'Oklahoma City'  # Placeholder to be replaced [cite: 21]
[cite_start]REPO_PREFIX = 'The-' [cite: 21]
[cite_start]REPO_SUFFIX = '-Software-Guild' [cite: 21]
[cite_start]VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html' [cite: 21]
[cite_start]THANKYOU_FILE_NAME = 'thankyou.index' [cite: 21]
# ---------------------

# --- API & Helper Functions ---

def get_api_data(query, api_key):
    """Generic function to fetch data from Google Places and Geocoding APIs."""
    # [cite_start]This function is used to fetch the three libraries, three bars, three restaurants, and three barber shops. [cite: 6, 8, 10, 13]
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {'query': query, 'key': api_key}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed for query '{query}': {e}")
        return {}

def get_city_coords(city, api_key):
    """Fetches longitude and latitude for a city using Google Geocoding."""
    # [cite_start]This function implements requirement 1. [cite: 3]
    query = f"{city}"
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': query, 'key': api_key}
    try:
        response = requests.get(geo_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except requests.exceptions.RequestException as e:
        print(f"Geocoding API request failed for '{city}': {e}")
    return 'N/A', 'N/A'

def get_wikipedia_summary(city):
    """Fetches the introductory paragraph for a city from Wikipedia."""
    # [cite_start]This function implements requirement 7. [cite: 15, 16, 17]
    wiki = wikipediaapi.Wikipedia('CityInfoBot/1.0', 'en')
    page = wiki.page(city)
    if page.exists():
        # Return the first paragraph of the summary
        return page.summary.split('\n')[0]
    return f"A detailed description of {city} could not be found at this time."

def create_html_list(items, not_found_message="No locations found."):
    """Creates an HTML list from a list of items."""
    if not items:
        return f'<li>{not_found_message}</li>'
    return ''.join([f'<li>{item}</li>' for item in items])

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        [cite_start]return f.read() [cite: 21]

def get_thankyou_content(user_login, repo_name):
    """Generates the thank you HTML with the correct, dynamic redirect URL."""
    [cite_start]redirect_url = f"https://{user_login}.github.io/{repo_name}/index.html" [cite: 22]
    [cite_start]verification_content = 'google-site-verification: google51f4be664899794b6.html' [cite: 22]
    thankyou_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You!</title>
    <meta http-equiv="refresh" content="0; url={redirect_url}">
</head>
<body>
    <h1>Thank you for contacting us!</h1>
    <p>Redirecting you back to our homepage...</p>
    <a href="{redirect_url}">Click here if you are not redirected</a>
</body>
</html>"""
    return verification_content, thankyou_html

def process_city_deployment(g, user, token, city):
    """Handles the full creation, update, and deployment cycle for a single city."""
    repo_name_base = f"{city.replace(' ', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DEPLOYMENT FOR: {city} ---")
    print(f"Targeting new repository: {new_repo_name}")

    google_api_key = os.environ.get('GOOGLE_API_KEY')
    if not google_api_key:
        # Note: This warning is shown in the output, indicating the key must be set as a secret.
        print("Warning: GOOGLE_API_KEY environment variable not set. Dynamic content will be skipped.")
        
    # Read and perform initial city name replacement (Requirement 8)
    [cite_start]base_html_content = read_file(SOURCE_HTML_FILE) [cite: 27]
    
    # 💥 FIXED: Removed the erroneous citation placeholder from this line
    new_content = base_html_content.replace(SEARCH_TERM, city)
    
    [cite_start]new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}" [cite: 27]
    [cite_start]new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE) [cite: 27]

    # --- NEW: Fetch and Replace Dynamic Content ---
    if google_api_key:
        print("Fetching dynamic content...")
        # 1. Replace Lat/Lon (Requirement 1)
        lat, lon = get_city_coords(city, google_api_key)
        new_content = re.sub(r'', str(lat), new_content)
        new_content = re.sub(r'', str(lon), new_content)
        
        # 2. Replace Local Conditions (Requirement 2)
        [cite_start]new_content = re.sub(r'', f'Current Conditions in {city}', new_content) [cite: 4, 5]
        
        # 3. Replace Lists: Libraries, Bars, Restaurants, Barbers (Requirements 3, 4, 5, 6)
        place_types = {
            'libraries': ('libraries in', 'library-list'),
            'bars': ('bars in', 'bar-list'),
            'restaurants': ('restaurants in', 'restaurant-list'),
            'barbers': ('barber shops in', 'barber-list')
        }
        
        for key, (query_text, element_id) in place_types.items():
            api_results = get_api_data(f"{query_text} {city}", google_api_key)
            names = [item['name'] for item in api_results.get('results', [])[:3]]
            html_list = create_html_list(names, f"No local {key} found.")
            # Regex to replace the content of a specific <ul> element by ID
            pattern = re.compile(f'(<ul id="{element_id}">)(.*?)(</ul>)', re.DOTALL)
            new_content = pattern.sub(f'\\1{html_list}\\3', new_content)
            
        # 4. Replace Wikipedia Paragraph (Requirement 7)
        wiki_summary = get_wikipedia_summary(city)
        pattern = re.compile(f'(<p id="wiki-summary">)(.*?)(</p>)', re.DOTALL)
        new_content = pattern.sub(f'\\1{wiki_summary}\\3', new_content)

    # 5. Connect to GitHub and Create/Get Repo
    repo = None
    try:
        try:
            [cite_start]repo = user.get_repo(new_repo_name) [cite: 28]
            [cite_start]print(f"Repository already exists. Proceeding to update.") [cite: 29]
        except Exception:
            print(f"Repository does not exist. Creating new repository.")
            [cite_start]repo = user.create_repo(name=new_repo_name, private=False, auto_init=True) [cite: 30]
            sleep(5) 

        verification_content, thankyou_html = get_thankyou_content(user.login, new_repo_name)
        
        # Commit verification and thankyou files
        for path, content, msg in [
            (VERIFICATION_FILE_NAME, verification_content, "Add/Update Google verification file")[cite_start], [cite: 31]
            (THANKYOU_FILE_NAME, thankyou_html, "Add/Update thankyou redirect page")[cite_start], [cite: 32]
            (".nojekyll", "", "Add/Update .nojekyll file") [cite_start][cite: 33]
        ]:
            try:
                contents = repo.get_contents(path, ref="main")
                repo.update_file(path, msg, content, contents.sha, branch="main")
            except Exception:
                repo.create_file(path, msg, content, branch="main")
            print(f"Committed {path}.")

        # Commit the generated index.html
        try:
            [cite_start]contents = repo.get_contents("index.html", ref="main") [cite: 34]
            [cite_start]repo.update_file("index.html", f"Update site content for {city}", new_content, contents.sha, branch="main") [cite: 34]
        except Exception:
            [cite_start]repo.create_file("index.html", f"Initial site deployment for {city}", new_content, branch="main") [cite: 34]
        print("Committed updated index.html to the new repository.")

        # 6. Enable GitHub Pages
        [cite_start]pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages" [cite: 35]
        [cite_start]headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'} [cite: 35]
        [cite_start]data = {'source': {'branch': 'main', 'path': '/'}} [cite: 35]
        [cite_start]response = requests.post(pages_api_url, headers=headers, json=data) [cite: 35]
        if response.status_code == 201:
            [cite_start]print("Successfully configured GitHub Pages.") [cite: 36]
        elif response.status_code == 409: # Already exists, so update
            requests.put(pages_api_url, headers=headers, json=data)
            [cite_start]print("Successfully updated GitHub Pages configuration.") [cite: 36]
        
        # 7. Fetch and Display Final URL
        sleep(10)
        [cite_start]r = requests.get(pages_api_url, headers=headers) [cite: 37]
        pages_url = r.json().get('html_url', 'URL not yet active.')
        [cite_start]print(f"Final Repository URL: {repo.html_url}") [cite: 38]
        print(f"Live site URL: {pages_url}")
        print(f"--- {city} DEPLOYMENT COMPLETE ---")

    except Exception as e:
        print(f"A critical error occurred during {city} deployment: {e}")

def main():
    """Main execution function to loop through all cities."""
    [cite_start]token = os.environ.get('GH_TOKEN') [cite: 39]
    [cite_start]delay = float(os.environ.get('DEPLOY_DELAY', 180)) [cite: 39]

    if not token:
        [cite_start]raise EnvironmentError("Missing GH_TOKEN environment variable.") [cite: 39]

    [cite_start]cities = [c.strip() for c in read_file(CITIES_FILE).splitlines() if c.strip()] [cite: 39]
    if not cities:
        print(f"Error: {CITIES_FILE} is empty.")
        return

    # [cite_start]Initialize GitHub connection (once) [cite: 40]
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = Github(token)
        user = g.get_user()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to GitHub API: {e}")

    # [cite_start]Iterate through all cities with a delay [cite: 41]
    for i, city in enumerate(cities):
        if i > 0:
            [cite_start]print(f"\n--- PAUSING for {delay} seconds before next deployment... ---") [cite: 41]
            sleep(delay)
        process_city_deployment(g, user, token, city)
    
    print("\n\n*** ALL DEPLOYMENTS COMPLETE ***")

if __name__ == "__main__":
    main()
