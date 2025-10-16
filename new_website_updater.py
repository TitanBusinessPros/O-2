import os
import re
import json
import requests 
from github import Github
from time import sleep

# --- Configuration ---
SOURCE_HTML_FILE = 'index.html'
CITIES_FILE = 'new.txt' 
SEARCH_TERM = 'Oklahoma City' 
REPO_PREFIX = 'The-'
REPO_SUFFIX = '-Software-Guild'
VERIFICATION_FILE_NAME = 'google51f4be664899794b6.html'
THANKYOU_FILE_NAME = 'thankyou.index'
# ---------------------

def read_file(filename):
    """Reads the content of a file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def get_city_coordinates(city_name):
    """Get latitude and longitude for any city."""
    # Simple coordinate lookup for common cities - will expand as needed
    coordinates_db = {
        'Oklahoma City': (35.4676, -97.5164),
        'Kansas City, Kansas': (39.1142, -94.6275),
        'Dallas': (32.7767, -96.7970),
        'Tulsa': (36.1540, -95.9928),
        'Stillwater': (36.1156, -97.0584),
        'Roland-Oklahoma': (35.4212, -97.2936),
        'Boston': (42.3601, -71.0589),
        'New York': (40.7128, -74.0060),
        'Los Angeles': (34.0522, -118.2437),
        'Chicago': (41.8781, -87.6298),
        'Houston': (29.7604, -95.3698),
        'Phoenix': (33.4484, -112.0740),
        'Philadelphia': (39.9526, -75.1652),
        'San Antonio': (29.4241, -98.4936),
        'San Diego': (32.7157, -117.1611),
        'Austin': (30.2672, -97.7431),
    }
    
    # Try exact match first
    if city_name in coordinates_db:
        return coordinates_db[city_name]
    
    # Try partial match (city name without state)
    city_only = city_name.split(',')[0].strip()
    for known_city, coords in coordinates_db.items():
        if known_city.startswith(city_only):
            return coords
    
    # Default to Oklahoma City coordinates if not found
    return (35.4676, -97.5164)

def generate_city_specific_content(city_name, content_type):
    """Generate city-specific content for different sections."""
    city_only = city_name.split(',')[0].strip()
    
    if content_type == "libraries":
        return [
            f"{city_only} Public Library",
            f"{city_only} Main Library", 
            f"{city_only} Community Library"
        ]
    elif content_type == "bars":
        return [
            f"{city_only} Pub & Tavern",
            f"{city_only} Sports Bar",
            f"{city_only} Local Lounge"
        ]
    elif content_type == "restaurants":
        return [
            f"{city_only} Family Diner",
            f"{city_only} Grill House", 
            f"{city_only} Local Cafe"
        ]
    elif content_type == "barbers":
        return [
            f"{city_only} Classic Barbershop",
            f"{city_only} Modern Cuts",
            f"{city_only} Style Salon"
        ]
    return []

def get_wikipedia_summary(city_name):
    """Get Wikipedia summary for any city."""
    try:
        # Clean city name for Wikipedia API
        clean_city = city_name.split(',')[0].strip().replace(' ', '_')
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_city}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('extract', f"{city_name} is a vibrant community with rich cultural heritage and modern amenities.")
    except:
        pass
    
    # Fallback description
    return f"{city_name} is a vibrant community with a rich history and diverse population. Located in a beautiful region, it offers excellent quality of life with modern amenities, cultural attractions, and economic opportunities for residents and visitors alike."

def replace_html_content(html_content, city_name):
    """Replace all Oklahoma City specific content with new city content."""
    lat, lng = get_city_coordinates(city_name)
    libraries = generate_city_specific_content(city_name, "libraries")
    bars = generate_city_specific_content(city_name, "bars")
    restaurants = generate_city_specific_content(city_name, "restaurants") 
    barbers = generate_city_specific_content(city_name, "barbers")
    wiki_summary = get_wikipedia_summary(city_name)
    
    new_content = html_content
    
    # 1. Replace coordinates (multiple possible patterns)
    print(f"Replacing coordinates with: {lat}, {lng}")
    new_content = re.sub(r'data-lat="[^"]*"', f'data-lat="{lat}"', new_content)
    new_content = re.sub(r'data-lng="[^"]*"', f'data-lng="{lng}"', new_content)
    new_content = re.sub(r'latitude["\']?\s*:\s*[^,\]}]*', f'latitude: {lat}', new_content)
    new_content = re.sub(r'longitude["\']?\s*:\s*[^,\]}]*', f'longitude: {lng}', new_content)
    
    # 2. Replace current local conditions (weather/location references)
    new_content = re.sub(r'Oklahoma City[^<]*(weather|conditions|temperature)', 
                        f'{city_name} \\1', new_content, flags=re.IGNORECASE)
    
    # 3. Replace libraries section - multiple replacement strategies
    libraries_patterns = [
        (r'<h3>[^>]*Local Library Access[^>]*</h3>\s*<ul>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*</ul>', 
         f'<h3>Local Library Access</h3><ul><li>{libraries[0]}</li><li>{libraries[1]}</li><li>{libraries[2]}</li></ul>'),
        
        (r'Local Library Access[^<]*<ul>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*</ul>',
         f'Local Library Access</h3><ul><li>{libraries[0]}</li><li>{libraries[1]}</li><li>{libraries[2]}</li></ul>')
    ]
    
    for pattern, replacement in libraries_patterns:
        new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE | re.DOTALL)
    
    # 4. Replace bars section
    bars_patterns = [
        (r'<h3>[^>]*Local spots to meet[^>]*</h3>\s*<ul>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*</ul>',
         f'<h3>Local Spots to Meet</h3><ul><li>{bars[0]}</li><li>{bars[1]}</li><li>{bars[2]}</li></ul>'),
        
        (r'Local spots to meet[^<]*<ul>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*</ul>',
         f'Local Spots to Meet</h3><ul><li>{bars[0]}</li><li>{bars[1]}</li><li>{bars[2]}</li></ul>')
    ]
    
    for pattern, replacement in bars_patterns:
        new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE | re.DOTALL)
    
    # 5. Replace restaurants section
    restaurants_patterns = [
        (r'<h3>[^>]*restaurants near me[^>]*</h3>\s*<ul>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*</ul>',
         f'<h3>Restaurants Near Me</h3><ul><li>{restaurants[0]}</li><li>{restaurants[1]}</li><li>{restaurants[2]}</li></ul>'),
        
        (r'restaurants near me[^<]*<ul>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*</ul>',
         f'Restaurants Near Me</h3><ul><li>{restaurants[0]}</li><li>{restaurants[1]}</li><li>{restaurants[2]}</li></ul>')
    ]
    
    for pattern, replacement in restaurants_patterns:
        new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE | re.DOTALL)
    
    # 6. Replace barbers section
    barbers_patterns = [
        (r'<h3>[^>]*Get a Haircut and Get a Real Job![^>]*</h3>\s*<ul>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*<li>[^<]*</li>\s*</ul>',
         f'<h3>Get a Haircut and Get a Real Job!</h3><ul><li>{barbers[0]}</li><li>{barbers[1]}</li><li>{barbers[2]}</li></ul>'),
        
        (r'Get a Haircut and Get a Real Job![^<]*<ul>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*<li>[^<]*</li>[^<]*</ul>',
         f'Get a Haircut and Get a Real Job!</h3><ul><li>{barbers[0]}</li><li>{barbers[1]}</li><li>{barbers[2]}</li></ul>')
    ]
    
    for pattern, replacement in barbers_patterns:
        new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE | re.DOTALL)
    
    # 7. Replace Wikipedia paragraph in "The Greatest Time in Human History"
    new_content = re.sub(
        r'Oklahoma City[^<]*(?=</p>)',
        f'{city_name} - {wiki_summary}',
        new_content,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    # 8. Replace ALL remaining instances of Oklahoma City
    new_content = re.sub(r'Oklahoma City', city_name, new_content, flags=re.IGNORECASE)
    
    return new_content

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
    
    repo_name_base = f"{city.replace(' ', '').replace(',', '')}"
    new_repo_name = f"{REPO_PREFIX}{repo_name_base}{REPO_SUFFIX}"
    print(f"\n--- STARTING DEPLOYMENT FOR: {city} ---")
    print(f"Target repository: {new_repo_name}")
    
    # Read and modify HTML content
    base_html_content = read_file(SOURCE_HTML_FILE)
    
    print(f"Replacing content for {city}...")
    new_content = replace_html_content(base_html_content, city)
    
    # Update title
    new_site_title = f"{REPO_PREFIX.strip('-')} {city} {REPO_SUFFIX.strip('-')}"
    new_content = re.sub(r'<title>.*?</title>', f'<title>{new_site_title}</title>', new_content, flags=re.IGNORECASE)
    
    # Connect to GitHub and Create/Get Repo
    repo = None
    try:
        # Get or Create Repository
        try:
            repo = user.get_repo(new_repo_name)
            print(f"Repository exists. Updating content.")
        except Exception:
            print(f"Creating new repository: {new_repo_name}")
            repo = user.create_repo(
                name=new_repo_name,
                description=f"GitHub Pages site for {city} Software Guild",
                private=False,
                auto_init=True
            )
            sleep(5)

        # Commit files
        verification_content, thankyou_html = get_thankyou_content(user.login, new_repo_name)
        
        # Google verification file
        try:
            contents = repo.get_contents(VERIFICATION_FILE_NAME, ref="main")
            repo.update_file(path=VERIFICATION_FILE_NAME, message="Update Google verification", content=verification_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=VERIFICATION_FILE_NAME, message="Add Google verification", content=verification_content, branch="main")
        print(f"Committed {VERIFICATION_FILE_NAME}")

        # Thank you file
        try:
            contents = repo.get_contents(THANKYOU_FILE_NAME, ref="main")
            repo.update_file(path=THANKYOU_FILE_NAME, message="Update thankyou page", content=thankyou_html, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=THANKYOU_FILE_NAME, message="Add thankyou page", content=thankyou_html, branch="main")
        print(f"Committed {THANKYOU_FILE_NAME}")

        # .nojekyll file
        try:
            contents = repo.get_contents(".nojekyll", ref="main")
            repo.update_file(path=".nojekyll", message="Update .nojekyll", content="", sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path=".nojekyll", message="Add .nojekyll", content="", branch="main")
        print("Added/Updated .nojekyll file")

        # Main index.html
        try:
            contents = repo.get_contents("index.html", ref="main")
            repo.update_file(path="index.html", message=f"Update site for {city}", content=new_content, sha=contents.sha, branch="main")
        except Exception:
            repo.create_file(path="index.html", message=f"Deploy site for {city}", content=new_content, branch="main")
        print("Committed updated index.html")

        # Enable GitHub Pages
        pages_api_url = f"https://api.github.com/repos/{user.login}/{new_repo_name}/pages"
        headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
        data = {'source': {'branch': 'main', 'path': '/'}}
        
        r = requests.post(pages_api_url, headers=headers, json=data)
        
        if r.status_code == 201:
            print("GitHub Pages configured")
        elif r.status_code == 409:
            r = requests.put(pages_api_url, headers=headers, json=data)
            if r.status_code == 204:
                print("GitHub Pages updated")

        # Get final URL
        pages_url = f"https://{user.login}.github.io/{new_repo_name}/"
        print(f"Repository URL: {repo.html_url}")
        print(f"Live site URL: {pages_url}")
        print(f"--- {city} DEPLOYMENT COMPLETE ---")

    except Exception as e:
        print(f"Error during {city} deployment: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution function."""
    token = os.environ.get('GH_TOKEN')
    delay = float(os.environ.get('DEPLOY_DELAY', 180))

    if not token:
        raise EnvironmentError("Missing GH_TOKEN environment variable")

    # Read cities from file
    cities_data = read_file(CITIES_FILE)
    all_cities = [c.strip() for c in cities_data.splitlines() if c.strip()]

    if not all_cities:
        print(f"Error: {CITIES_FILE} is empty")
        return

    # Initialize GitHub connection
    try:
        g = Github(token)
        user = g.get_user()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to GitHub: {e}")

    # Process all cities
    for i, city in enumerate(all_cities):
        if i > 0:
            print(f"\n--- Waiting {delay} seconds before next deployment ---")
            sleep(delay)
        
        process_city_deployment(g, user, token, city)
    
    print("\n*** ALL DEPLOYMENTS COMPLETE ***")

if __name__ == "__main__":
    main()
