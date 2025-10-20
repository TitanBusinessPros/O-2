import os
import time
import requests
import json
from github import Github

# User-Agent for API requests
USER_AGENT = "EyeTryAI-Website-Deployer/1.0 (https://github.com/TitanBusinessPros)"

def get_coordinates(city_state):
    """Get latitude and longitude from Nominatim"""
    city, state = city_state.split('-')
    url = f"https://nominatim.openstreetmap.org/search"
    params = {
        'q': f"{city}, {state}, USA",
        'format': 'json',
        'limit': 1
    }
    headers = {'User-Agent': USER_AGENT}
    
    response = requests.get(url, params=params, headers=headers)
    time.sleep(1)  # Respect Nominatim rate limits
    
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        return float(data['lat']), float(data['lon'])
    return None, None

def get_wikipedia_summary(city_state):
    """Get Wikipedia summary for the city"""
    city, state = city_state.split('-')
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city},_{state}"
    headers = {'User-Agent': USER_AGENT}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('extract', '')
    
    # Fallback to search API
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'extracts',
        'exintro': True,
        'explaintext': True,
        'titles': f"{city}, {state}"
    }
    
    response = requests.get(search_url, params=params, headers=headers)
    if response.status_code == 200:
        pages = response.json().get('query', {}).get('pages', {})
        for page in pages.values():
            return page.get('extract', '')
    
    return f"{city}, {state}, is a community rich in local heritage and character."

def get_nearby_city(lat, lon, radius=50000):
    """Get nearby city for fallback data"""
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["place"~"city|town"](around:{radius},{lat},{lon});
    );
    out body 1;
    """
    
    headers = {'User-Agent': USER_AGENT}
    response = requests.post(url, data={'data': query}, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('elements'):
            return data['elements'][0].get('tags', {}).get('name', None)
    return None

def get_overpass_data(lat, lon, amenity_type, radius=15000):
    """Query Overpass API for businesses"""
    url = "https://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
      way["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
    );
    out body 3;
    """
    
    headers = {'User-Agent': USER_AGENT}
    response = requests.post(url, data={'data': query}, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('elements', [])
    return []

def format_business_html(businesses, category_name):
    """Format business data into HTML"""
    if not businesses:
        return f"<li><strong>No {category_name} found</strong><p>Check nearby areas for services.</p></li>"
    
    html = ""
    for biz in businesses[:3]:  # Top 3
        tags = biz.get('tags', {})
        name = tags.get('name', 'Local Business')
        address = tags.get('addr:street', 'Address not available')
        city = tags.get('addr:city', '')
        
        html += f"""<li>
                    <strong>{name}</strong>
                    <p>{address}, {city}</p>
                    <a href="https://www.google.com/search?q={name.replace(' ', '+')}" target="_blank">Verify on Google</a>
                </li>
                """
    
    return html

def update_html_template(template_path, city_state, lat, lon, wiki_text, business_data):
    """Update the HTML template with new city data"""
    city, state = city_state.split('-')
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Replace city-state references
    html = html.replace('Paoli, Oklahoma', f'{city}, {state}')
    html = html.replace('Paoli, OK', f'{city}, {state.upper()[:2]}')
    html = html.replace('Paoli', city)
    
    # Update coordinates
    html = html.replace('34.83', f'{lat:.2f}')
    html = html.replace('97.26', f'{abs(lon):.2f}')
    
    # Update Wikipedia section
    wiki_section = f"""<section id="paoli-ok" class="section paoli-section">
            <h2 class="section-title">The Nexus Point: {city}, {state}</h2>
            <p>
                {wiki_text}
            </p>
        </section>"""
    
    # Replace the nexus section
    start = html.find('<section id="paoli-ok"')
    end = html.find('</section>', start) + len('</section>')
    html = html[:start] + wiki_section + html[end:]
    
    # Update business sections
    for category, data in business_data.items():
        # Find and replace each business category
        html = html.replace(f'<h3>{category}</h3>', f'<h3>{category}</h3>\n<ul class="business-list">\n{data}\n</ul>')
    
    # Update weather coordinates in JavaScript
    html = html.replace('const lat = 34.83;', f'const lat = {lat};')
    html = html.replace('const lon = -97.26;', f'const lon = {lon};')
    
    return html

def create_github_repo(github_token, repo_name, html_content):
    """Create new GitHub repository and push files"""
    g = Github(github_token)
    user = g.get_user()
    
    # Create new repository
    repo = user.create_repo(
        repo_name,
        description=f"AI-generated website for {repo_name}",
        private=False,
        auto_init=False
    )
    
    print(f"Created repository: {repo.full_name}")
    
    # Push files
    repo.create_file("index.html", "Initial commit", html_content, branch="main")
    repo.create_file(".nojekyll", "Add .nojekyll", "", branch="main")
    
    # Enable GitHub Pages
    try:
        repo.enable_pages(branch="main", path="/")
        print(f"GitHub Pages enabled at: https://{user.login}.github.io/{repo_name}/")
    except Exception as e:
        print(f"Note: Enable GitHub Pages manually - {e}")
    
    return repo

def main():
    # Read city from new.txt
    with open('new.txt', 'r') as f:
        city_state = f.read().strip()
    
    print(f"Processing: {city_state}")
    
    # Get coordinates
    lat, lon = get_coordinates(city_state)
    if not lat:
        print("Error: Could not find coordinates")
        return
    
    print(f"Coordinates: {lat}, {lon}")
    
    # Get Wikipedia summary
    wiki_text = get_wikipedia_summary(city_state)
    print("Wikipedia summary retrieved")
    
    # Get business data with 5-minute delays
    business_data = {}
    
    categories = {
        'Barbershops': 'barber',
        'Coffee Shops': 'cafe',
        'Diners & Cafés': 'restaurant',
        'Local Bars & Pubs': 'bar',
        'Libraries': 'library',
        'Attractions & Amusements': 'attraction'
    }
    
    for i, (category, amenity) in enumerate(categories.items()):
        print(f"Fetching {category}...")
        businesses = get_overpass_data(lat, lon, amenity)
        
        # If no results, try nearby city
        if not businesses:
            print(f"No {category} found, checking nearby areas...")
            nearby_city = get_nearby_city(lat, lon)
            if nearby_city:
                print(f"Using data from nearby: {nearby_city}")
        
        business_data[category] = format_business_html(businesses, category)
        
        # 5-minute sleep between API calls (except last one)
        if i < len(categories) - 1:
            print("Waiting 5 minutes before next API call...")
            time.sleep(300)
    
    # Update HTML template
    html_content = update_html_template('index.html', city_state, lat, lon, wiki_text, business_data)
    
    # Create GitHub repository
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_name = city_state.replace(' ', '-')
    
    create_github_repo(github_token, repo_name, html_content)
    
    print(f"✅ Deployment complete for {city_state}")

if __name__ == "__main__":
    main()
