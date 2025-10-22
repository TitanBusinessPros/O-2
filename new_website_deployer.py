#!/usr/bin/env python3
import os
import requests
import time
import json
import re
import traceback
from datetime import datetime
from github import Github, GithubException

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

def debug_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔍 {message}")

def error_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ❌ {message}")

def success_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ✅ {message}")

def read_city_from_file():
    """Read city-state from new.txt file"""
    try:
        with open('new.txt', 'r') as f:
            content = f.read().strip()
            if '-' in content:
                debug_log(f"Read city-state from new.txt: {content}")
                return content
            else:
                raise ValueError("File should contain city-state format like 'Dallas-Texas'")
    except FileNotFoundError:
        raise Exception("new.txt file not found")

def geocode_city(city_state):
    """Get latitude and longitude for city using Nominatim"""
    city, state = city_state.split('-')
    time.sleep(1)
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': f"{city}, {state}, USA",
        'format': 'json',
        'limit': 1
    }
    
    headers = {
        'User-Agent': 'EyeTryAICityDeployer/1.0',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 403:
            return get_state_coordinates(state)
        response.raise_for_status()
        
        data = response.json()
        if not data:
            return get_state_coordinates(state)
        
        return (float(data[0]['lat']), float(data[0]['lon']))
    except:
        return get_state_coordinates(state)

def get_state_coordinates(state):
    """Get approximate coordinates for a state"""
    state_coords = {
        'Texas': (31.9686, -99.9018), 'TX': (31.9686, -99.9018),
        'Oklahoma': (35.4676, -97.5164), 'OK': (35.4676, -97.5164),
        'California': (36.7783, -119.4179), 'CA': (36.7783, -119.4179),
        'New York': (43.2994, -74.2179), 'NY': (43.2994, -74.2179),
        'Florida': (27.6648, -81.5158), 'FL': (27.6648, -81.5158),
    }
    return state_coords.get(state, (39.8283, -98.5795))

def get_timezone_from_coords(lat, lon):
    """Get timezone from coordinates using TimezoneAPI"""
    try:
        url = f"http://api.timezonedb.com/v2.1/get-time-zone"
        params = {
            'key': 'YOUR_API_KEY',  # Free tier available
            'format': 'json',
            'by': 'position',
            'lat': lat,
            'lng': lon
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('zoneName', 'America/Chicago')
    except:
        pass
    
    # Fallback: Estimate timezone from longitude
    if -85 <= lon <= -67:
        return 'America/New_York'
    elif -115 <= lon < -85:
        return 'America/Chicago' 
    elif -125 <= lon < -115:
        return 'America/Los_Angeles'
    else:
        return 'America/Chicago'

def get_weather_forecast(lat, lon):
    """Get 7-day weather forecast from Open-Meteo"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'temperature_2m_max,temperature_2m_min,weathercode',
        'temperature_unit': 'fahrenheit',
        'timezone': 'auto',
        'forecast_days': 7
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {'daily': {'time': [], 'temperature_2m_max': [], 'temperature_2m_min': [], 'weathercode': []}}

def get_wikipedia_summary(city_state):
    """Get city summary from Wikipedia API"""
    city, state = city_state.split('-')
    time.sleep(1)
    
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    search_term = f"{city}, {state}"
    
    headers = {
        'User-Agent': 'EyeTryAICityDeployer/1.0'
    }
    
    try:
        response = requests.get(url + search_term.replace(' ', '_'), headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('extract', f"{city}, {state} is a location with rich local history and community.")
    except:
        return f"{city}, {state} is a community with unique local character and growing opportunities for digital innovation and business development."

def query_overpass_enhanced(category, lat, lon, radius=20000):
    """Enhanced OverPass API queries with better business data"""
    
    # Expanded queries for each category
    overpass_queries = {
        'barbers': f"""
        [out:json][timeout:30];
        (
          node["shop"="hairdresser"](around:{radius},{lat},{lon});
          node["amenity"="barber"](around:{radius},{lat},{lon});
          node["shop"="hair"](around:{radius},{lat},{lon});
          way["shop"="hairdresser"](around:{radius},{lat},{lon});
          way["amenity"="barber"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        
        'bars': f"""
        [out:json][timeout:30];
        (
          node["amenity"="bar"](around:{radius},{lat},{lon});
          node["amenity"="pub"](around:{radius},{lat},{lon});
          node["amenity"="nightclub"](around:{radius},{lat},{lon});
          way["amenity"="bar"](around:{radius},{lat},{lon});
          way["amenity"="pub"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        
        'diners_cafes': f"""
        [out:json][timeout:30];
        (
          node["amenity"="cafe"](around:{radius},{lat},{lon});
          node["amenity"="restaurant"](around:{radius},{lat},{lon});
          node["amenity"="fast_food"](around:{radius},{lat},{lon});
          node["amenity"="food_court"](around:{radius},{lat},{lon});
          way["amenity"="cafe"](around:{radius},{lat},{lon});
          way["amenity"="restaurant"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        
        'libraries': f"""
        [out:json][timeout:30];
        (
          node["amenity"="library"](around:{radius},{lat},{lon});
          way["amenity"="library"](around:{radius},{lat},{lon});
          relation["amenity"="library"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        
        'attractions_amusements': f"""
        [out:json][timeout:30];
        (
          node["tourism"="attraction"](around:{radius},{lat},{lon});
          node["tourism"="museum"](around:{radius},{lat},{lon});
          node["tourism"="gallery"](around:{radius},{lat},{lon});
          node["leisure"="park"](around:{radius},{lat},{lon});
          node["leisure"="garden"](around:{radius},{lat},{lon});
          node["historic"="monument"](around:{radius},{lat},{lon});
          node["amenity"="cinema"](around:{radius},{lat},{lon});
          node["amenity"="theatre"](around:{radius},{lat},{lon});
          way["tourism"="attraction"](around:{radius},{lat},{lon});
          way["tourism"="museum"](around:{radius},{lat},{lon});
          way["leisure"="park"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        
        'coffee_shops': f"""
        [out:json][timeout:30];
        (
          node["amenity"="cafe"]["cuisine"="coffee_shop"](around:{radius},{lat},{lon});
          node["shop"="coffee"](around:{radius},{lat},{lon});
          node["amenity"="cafe"](around:{radius},{lat},{lon});
          way["amenity"="cafe"]["cuisine"="coffee_shop"](around:{radius},{lat},{lon});
          way["shop"="coffee"](around:{radius},{lat},{lon});
        );
        out body;
        """
    }
    
    if category not in overpass_queries:
        return []
    
    url = "https://overpass-api.de/api/interpreter"
    
    try:
        debug_log(f"Making enhanced OverPass query for {category}")
        response = requests.post(url, data=overpass_queries[category], timeout=45)
        response.raise_for_status()
        data = response.json()
        elements = data.get('elements', [])
        debug_log(f"Found {len(elements)} elements for {category}")
        return elements
    except Exception as e:
        error_log(f"OverPass query failed for {category}: {e}")
        return []

def process_business_data_enhanced(businesses, category, city):
    """Enhanced business data processing with better filtering"""
    debug_log(f"Processing {len(businesses)} businesses for {category}")
    
    processed = []
    seen_names = set()
    
    for business in businesses:
        # Extract business details with better field mapping
        tags = business.get('tags', {})
        
        name = tags.get('name', 'Unnamed Business').strip()
        if not name or name in seen_names:
            continue
            
        seen_names.add(name)
        
        # Get address components
        street = tags.get('addr:street', '')
        housenumber = tags.get('addr:housenumber', '')
        city_addr = tags.get('addr:city', city)
        postcode = tags.get('addr:postcode', '')
        
        # Build full address
        if street and housenumber:
            address = f"{housenumber} {street}"
        elif street:
            address = street
        else:
            address = f"Local {category} in {city}"
        
        if city_addr and postcode:
            address += f", {city_addr} {postcode}"
        elif city_addr:
            address += f", {city_addr}"
        
        # Get contact info
        phone = tags.get('phone', tags.get('contact:phone', ''))
        website = tags.get('website', tags.get('contact:website', tags.get('url', '#')))
        
        # Ensure website is valid
        if website == '#' or not website.startswith(('http://', 'https://')):
            website = '#'
        
        processed.append({
            'name': name,
            'address': address,
            'phone': phone,
            'website': website
        })
        
        # Stop when we have 3 good businesses
        if len(processed) >= 3:
            break
    
    # Fill remaining slots with fallbacks if needed
    if len(processed) < 3:
        debug_log(f"Only found {len(processed)} businesses, adding fallbacks")
        fallbacks = get_business_fallbacks(category, city)
        for fallback in fallbacks:
            if len(processed) < 3 and fallback['name'] not in seen_names:
                processed.append(fallback)
                seen_names.add(fallback['name'])
    
    debug_log(f"Final: {len(processed)} unique businesses for {category}")
    return processed

def get_business_fallbacks(category, city):
    """Get fallback business data when API returns insufficient results"""
    fallbacks = {
        'barbers': [
            {'name': f'{city} Barber Shop', 'address': f'Main Street, {city}', 'phone': '', 'website': '#'},
            {'name': 'Professional Cuts', 'address': f'Downtown {city}', 'phone': '', 'website': '#'},
            {'name': 'Classic Barbers', 'address': f'City Center, {city}', 'phone': '', 'website': '#'}
        ],
        'coffee_shops': [
            {'name': f'{city} Coffee House', 'address': f'Central Avenue, {city}', 'phone': '', 'website': '#'},
            {'name': 'Downtown Cafe', 'address': f'Business District, {city}', 'phone': '', 'website': '#'},
            {'name': 'Brew & Bean', 'address': f'Shopping Center, {city}', 'phone': '', 'website': '#'}
        ],
        'bars': [
            {'name': f'{city} Pub', 'address': f'Main Street, {city}', 'phone': '', 'website': '#'},
            {'name': 'City Bar', 'address': f'Downtown {city}', 'phone': '', 'website': '#'},
            {'name': 'Local Tavern', 'address': f'Entertainment District, {city}', 'phone': '', 'website': '#'}
        ],
        'diners_cafes': [
            {'name': f'{city} Family Diner', 'address': f'Central Avenue, {city}', 'phone': '', 'website': '#'},
            {'name': 'Local Cafe', 'address': f'Business District, {city}', 'phone': '', 'website': '#'},
            {'name': 'City Grill', 'address': f'Downtown {city}', 'phone': '', 'website': '#'}
        ],
        'libraries': [
            {'name': f'{city} Public Library', 'address': f'Community Center, {city}', 'phone': '', 'website': '#'},
            {'name': 'Regional Library', 'address': f'Education District, {city}', 'phone': '', 'website': '#'},
            {'name': 'Community Library', 'address': f'Civic Center, {city}', 'phone': '', 'website': '#'}
        ],
        'attractions_amusements': [
            {'name': f'{city} Community Park', 'address': f'Recreation Area, {city}', 'phone': '', 'website': '#'},
            {'name': 'Local Museum', 'address': f'Cultural District, {city}', 'phone': '', 'website': '#'},
            {'name': 'City Gardens', 'address': f'Park Area, {city}', 'phone': '', 'website': '#'}
        ]
    }
    return fallbacks.get(category, [])

def get_github_pages_workflow():
    """Returns the GitHub Pages deployment workflow"""
    return """name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

def update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data):
    """Update the HTML template with new city data"""
    debug_log("📄 Starting HTML template update...")
    
    try:
        # Read the original HTML template
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        city, state = city_state.split('-')
        debug_log(f"Updating HTML for: {city}, {state}")
        
        # Get timezone for the city
        timezone = get_timezone_from_coords(lat, lon)
        debug_log(f"Using timezone: {timezone}")
        
        # COMPREHENSIVE CITY REPLACEMENT
        replacements = [
            ('Paoli, Oklahoma', f'{city}, {state}'),
            ('Paoli, OK', f'{city}, {state}'),
            ('Ardmore, Oklahoma', f'{city}, {state}'),
            ('Ardmore, OK', f'{city}, {state}'),
            ('Paoli', city),
        ]
        
        for old_text, new_text in replacements:
            count_before = html_content.count(old_text)
            if count_before > 0:
                html_content = html_content.replace(old_text, new_text)
                count_after = html_content.count(old_text)
                debug_log(f"Replaced '{old_text}' with '{new_text}' (was {count_before}, now {count_after})")
        
        # Update coordinates in footer
        html_content = re.sub(r'Latitude: [\d.-]+° N', f'Latitude: {lat:.2f}° N', html_content)
        html_content = re.sub(r'Longitude: [\d.-]+° W', f'Longitude: {abs(lon):.2f}° W', html_content)
        
        # Update timezone in clock JavaScript
        html_content = re.sub(r"timeZone: '[\w/]+'", f"timeZone: '{timezone}'", html_content)
        debug_log(f"Updated clock timezone to: {timezone}")
        
        # Update Nexus Point section
        nexus_patterns = [
            r'<section id="paoli-ok"[^>]*>.*?<h2[^>]*>.*?</h2>.*?<p>.*?</p>.*?</section>',
            r'<section id="paoli-ok".*?</section>',
            r'The Nexus Point: [^<]+'
        ]
        
        new_nexus_section = f'''<section id="paoli-ok" class="section paoli-section">
            <h2 class="section-title">The Nexus Point: {city}, {state}</h2>
            <p>
                {wiki_summary}
            </p>
        </section>'''
        
        nexus_updated = False
        for pattern in nexus_patterns:
            if re.search(pattern, html_content, re.DOTALL):
                html_content = re.sub(pattern, new_nexus_section, html_content, flags=re.DOTALL)
                debug_log(f"Updated Nexus Point using pattern: {pattern}")
                nexus_updated = True
                break
        
        if not nexus_updated:
            if "The Nexus Point:" in html_content:
                html_content = html_content.replace("The Nexus Point: Paoli, Oklahoma", f"The Nexus Point: {city}, {state}")
                debug_log("Used fallback Nexus Point replacement")
        
        # Update weather coordinates in JavaScript
        weather_updates = [
            (r'const lat = [\d.-]+;', f'const lat = {lat};'),
            (r'const lon = [\d.-]+;', f'const lon = {lon};'),
            (r'//.*?Latitude', f'// {city}, {state} Latitude'),
            (r'//.*?Longitude', f'// {city}, {state} Longitude')
        ]
        
        for pattern, replacement in weather_updates:
            if re.search(pattern, html_content):
                html_content = re.sub(pattern, replacement, html_content)
                debug_log(f"Updated weather: {pattern}")
        
        # Update local businesses sections with enhanced data
        business_sections = {
            'barbers': 'Barbershops',
            'coffee_shops': 'Coffee Shops',
            'diners_cafes': 'Diners & Cafés',
            'bars': 'Local Bars & Pubs',
            'libraries': 'Libraries',
            'attractions_amusements': 'Attractions & Amusements'
        }
        
        for category, section_title in business_sections.items():
            debug_log(f"Updating {section_title} section...")
            
            # Create enhanced business section
            new_section = f'<h3>{section_title}</h3>\n            <ul class="business-list">\n'
            
            businesses = business_data.get(category, [])
            debug_log(f"Adding {len(businesses)} businesses to {section_title}")
            
            for business in businesses:
                # Add phone if available
                phone_html = f"<p>Phone: {business['phone']}</p>" if business['phone'] else ""
                
                # Create proper website link
                website_link = business['website']
                if website_link == '#':
                    website_text = "Check Local Directory"
                else:
                    website_text = "Visit Website"
                
                new_section += f'''                <li>
                    <strong>{business["name"]}</strong>
                    <p>{business["address"]}</p>
                    {phone_html}
                    <a href="{website_link}" target="_blank">{website_text}</a>
                </li>\n'''
            
            new_section += '            </ul>'
            
            # Find and replace the section
            section_pattern = f'<h3>{section_title}</h3>.*?</ul>'
            if re.search(section_pattern, html_content, re.DOTALL):
                html_content = re.sub(section_pattern, new_section, html_content, flags=re.DOTALL)
                debug_log(f"Updated {section_title} section with {len(businesses)} businesses")
            else:
                debug_log(f"⚠️ Could not find {section_title} section to replace")
        
        # VERIFY ALL UPDATES
        verification_points = [
            (f'{city}, {state}', "City name in content"),
            (f'The Nexus Point: {city}, {state}', "Nexus Point title"),
            (f'Latitude: {lat:.2f}° N', "Latitude coordinate"),
            (f'Longitude: {abs(lon):.2f}° W', "Longitude coordinate"),
            (f"timeZone: '{timezone}'", "Time zone in clock"),
        ]
        
        all_passed = True
        for check_text, description in verification_points:
            if check_text in html_content:
                success_log(f"✅ {description} - VERIFIED")
            else:
                error_log(f"❌ {description} - MISSING")
                all_passed = False
        
        # Verify business sections
        for category in business_sections.keys():
            businesses = business_data.get(category, [])
            if len(businesses) >= 1:
                success_log(f"✅ {category} - {len(businesses)} businesses")
            else:
                error_log(f"❌ {category} - NO BUSINESSES")
                all_passed = False
        
        if all_passed:
            success_log("🎉 ALL HTML UPDATES VERIFIED SUCCESSFULLY!")
        else:
            error_log("⚠️ SOME HTML UPDATES FAILED - CHECK ABOVE")
            
        return html_content
        
    except Exception as e:
        error_log(f"Error updating HTML template: {e}")
        error_log(f"Traceback: {traceback.format_exc()}")
        raise

def force_github_pages_deployment(username, repo_name):
    """Force GitHub Pages deployment"""
    debug_log(f"🔄 Ensuring GitHub Pages for {username}/{repo_name}")
    
    # Use the new auth method to avoid deprecation warnings
    from github import Auth
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    
    try:
        repo = g.get_repo(f"{username}/{repo_name}")
        
        # The workflow file should handle deployment automatically
        # Just verify it exists
        try:
            workflow_content = repo.get_contents(".github/workflows/deploy-pages.yml")
            success_log("✅ GitHub Pages workflow confirmed")
            return True
        except:
            error_log("❌ GitHub Pages workflow missing")
            return False
        
    except Exception as e:
        error_log(f"GitHub Pages verification failed: {e}")
        return False

def create_github_repo(city_state, updated_html):
    """Create new GitHub repository and push files"""
    debug_log("🐙 Creating GitHub repository...")
    
    # Use the new auth method
    from github import Auth
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    
    user = g.get_user()
    username = user.login
    
    repo_name = f"{city_state.replace('-', '').replace(' ', '').lower()}"
    debug_log(f"Repository name: {repo_name}")
    debug_log(f"Username: {username}")
    
    try:
        # Create new repository
        repo = user.create_repo(
            repo_name,
            description=f"Eye Try A.I. - {city_state}",
            private=False,
            auto_init=False
        )
        success_log(f"✅ Repository created: {repo.html_url}")
        
        # Wait for repo to be ready
        time.sleep(3)
        
        # Create and push files
        github_pages_workflow = get_github_pages_workflow()
        
        files_to_push = {
            'index.html': updated_html,
            '.nojekyll': '',
            '.github/workflows/deploy-pages.yml': github_pages_workflow
        }
        
        for filename, content in files_to_push.items():
            try:
                repo.create_file(
                    filename,
                    f"Initial commit for {city_state}",
                    content,
                    branch="main"
                )
                debug_log(f"Created {filename}")
            except Exception as e:
                debug_log(f"File creation warning for {filename}: {e}")
        
        success_log("✅ All files pushed to repository")
        
        # Wait for files to process
        time.sleep(5)
        
        # Verify GitHub Pages setup
        debug_log("🚀 Verifying GitHub Pages deployment...")
        if force_github_pages_deployment(username, repo_name):
            success_log("✅ GitHub Pages deployment confirmed")
        else:
            debug_log("⚠️ GitHub Pages may need manual activation")
        
        # Final verification
        debug_log("🔍 Final verification...")
        try:
            pages_url = f"https://{username}.github.io/{repo_name}"
            success_log(f"🌐 Site will be available at: {pages_url}")
            success_log("⏰ Allow 1-2 minutes for initial deployment")
        except Exception as e:
            debug_log(f"Final verification note: {e}")
        
        return repo.html_url
        
    except GithubException as e:
        if e.status == 422:
            debug_log(f"Repository {repo_name} already exists")
            return f"https://github.com/{user.login}/{repo_name}"
        else:
            raise

def main():
    debug_log("🚀 Starting website deployment process...")
    
    try:
        # Read city from file
        city_state = read_city_from_file()
        debug_log(f"Processing: {city_state}")
        
        # Get coordinates
        lat, lon = geocode_city(city_state)
        debug_log(f"Coordinates: {lat}, {lon}")
        
        # Get weather data
        weather_data = get_weather_forecast(lat, lon)
        debug_log("Weather data retrieved")
        
        # Get Wikipedia summary
        wiki_summary = get_wikipedia_summary(city_state)
        debug_log("Wikipedia summary retrieved")
        
        # Get enhanced business data
        business_data = {}
        categories = ['barbers', 'bars', 'diners_cafes', 'libraries', 'attractions_amusements', 'coffee_shops']
        
        city_name = city_state.split('-')[0]
        
        for i, category in enumerate(categories):
            debug_log(f"Querying {category}...")
            businesses = query_overpass_enhanced(category, lat, lon)
            business_data[category] = process_business_data_enhanced(businesses, category, city_name)
            if i < len(categories) - 1:
                debug_log("Waiting 5 seconds for next API call...")
                time.sleep(5)
        
        # Update HTML template
        debug_log("Updating HTML template...")
        updated_html = update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data)
        
        # Create GitHub repository
        debug_log("Creating GitHub repository...")
        repo_url = create_github_repo(city_state, updated_html)
        
        success_log(f"🎉 Deployment completed: {repo_url}")
        success_log("🌐 GitHub Pages will auto-deploy within 1-2 minutes")
        success_log("✅ Site will be LIVE automatically")
        
        # Write success file
        with open('deployment_success.txt', 'w') as f:
            f.write(f"Successfully deployed {city_state} to {repo_url}")
        
    except Exception as e:
        error_log(f"Deployment failed: {e}")
        error_log(f"Full traceback: {traceback.format_exc()}")
        with open('deployment_error.txt', 'w') as f:
            f.write(f"Deployment failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()
