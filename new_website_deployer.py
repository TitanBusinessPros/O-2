#!/usr/bin/env python3
import os
import sys
import requests
import time
import json
import re
import traceback
from datetime import datetime
from github import Github, GithubException

# Ultra-detailed debugging
def debug_log(message, data=None):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] 🔍 {message}")
    if data is not None:
        print(f"      📊 Data: {str(data)[:500]}...")

def error_log(message, exception=None):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] ❌ {message}")
    if exception:
        print(f"      💥 Exception: {exception}")
        print(f"      📍 Traceback: {traceback.format_exc()}")

def success_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] ✅ {message}")

def validate_html_content(html, city_state):
    """Validate that HTML was properly updated"""
    city, state = city_state.split('-')
    debug_log("VALIDATING HTML CONTENT...")
    
    checks = {
        f"City name '{city}' found": html.count(city) > 0,
        f"State '{state}' found": html.count(state) > 0,
        "Paoli, Oklahoma removed": "Paoli, Oklahoma" not in html,
        "Paoli, OK removed": "Paoli, OK" not in html,
        "Nexus Point section updated": f"The Nexus Point: {city}, {state}" in html,
    }
    
    for check, result in checks.items():
        if result:
            success_log(f"HTML Check: {check}")
        else:
            error_log(f"HTML Check FAILED: {check}")
            
    return all(checks.values())

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

def read_city_from_file():
    """Read city-state from new.txt file"""
    try:
        debug_log("Reading new.txt file...")
        with open('new.txt', 'r') as f:
            content = f.read().strip()
            debug_log("Raw content from new.txt", content)
            
            if '-' in content:
                city, state = content.split('-')
                success_log(f"Parsed city: {city}, state: {state}")
                return content
            else:
                raise ValueError("File should contain city-state format like 'Dallas-Texas'")
    except Exception as e:
        error_log("Failed to read new.txt", e)
        raise

def geocode_city(city_state):
    """Get latitude and longitude for city using Nominatim with proper headers"""
    city, state = city_state.split('-')
    debug_log(f"Geocoding {city}, {state}...")
    time.sleep(1)
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': f"{city}, {state}, USA",
        'format': 'json',
        'limit': 1
    }
    
    headers = {
        'User-Agent': 'EyeTryAICityDeployer/1.0 (https://github.com/TitanBusinessPros/O-2)',
        'Accept': 'application/json'
    }
    
    try:
        debug_log(f"Making request to Nominatim", params)
        response = requests.get(url, params=params, headers=headers, timeout=10)
        debug_log(f"Response status: {response.status_code}")
        
        if response.status_code == 403:
            error_log("Nominatim blocked request (403 Forbidden)")
            return get_state_coordinates(state)
            
        response.raise_for_status()
        
        data = response.json()
        debug_log("Nominatim response data", data)
        
        if not data:
            debug_log(f"No results found for {city_state}")
            return get_state_coordinates(state)
        
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        success_log(f"Coordinates found: {lat}, {lon}")
        return (lat, lon)
        
    except Exception as e:
        error_log(f"Geocoding failed", e)
        return get_state_coordinates(state)

def get_state_coordinates(state):
    """Get approximate coordinates for a state"""
    debug_log(f"Using fallback coordinates for state: {state}")
    state_coords = {
        'Texas': (31.9686, -99.9018), 'TX': (31.9686, -99.9018),
        'Oklahoma': (35.4676, -97.5164), 'OK': (35.4676, -97.5164),
        'California': (36.7783, -119.4179), 'CA': (36.7783, -119.4179),
        'New York': (43.2994, -74.2179), 'NY': (43.2994, -74.2179),
        'Florida': (27.6648, -81.5158), 'FL': (27.6648, -81.5158),
    }
    
    if state in state_coords:
        coords = state_coords[state]
        debug_log(f"Using state coordinates", coords)
        return coords
    else:
        debug_log("Using US center coordinates as fallback")
        return (39.8283, -98.5795)

def get_weather_forecast(lat, lon):
    """Get 7-day weather forecast from Open-Meteo"""
    debug_log("Fetching weather data...")
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
        data = response.json()
        success_log("Weather data retrieved")
        debug_log("Weather data sample", list(data['daily'].keys()))
        return data
    except Exception as e:
        error_log("Weather API failed", e)
        debug_log("Using mock weather data")
        return {
            'daily': {
                'time': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06', '2024-01-07'],
                'temperature_2m_max': [75, 78, 80, 77, 79, 81, 76],
                'temperature_2m_min': [60, 62, 64, 61, 63, 65, 59],
                'weathercode': [1, 2, 3, 1, 2, 3, 1]
            }
        }

def get_wikipedia_summary(city_state):
    """Get city summary from Wikipedia API"""
    city, state = city_state.split('-')
    debug_log(f"Fetching Wikipedia summary for {city}, {state}...")
    time.sleep(1)
    
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    search_term = f"{city}, {state}"
    
    headers = {
        'User-Agent': 'EyeTryAICityDeployer/1.0 (https://github.com/TitanBusinessPros/O-2)'
    }
    
    try:
        full_url = url + search_term.replace(' ', '_')
        debug_log(f"Wikipedia URL", full_url)
        response = requests.get(full_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        summary = data.get('extract', f"{city}, {state} is a location with rich local history and community.")
        success_log("Wikipedia summary retrieved")
        debug_log("Summary preview", summary[:100] + "...")
        return summary
    except Exception as e:
        error_log("Wikipedia API failed", e)
        debug_log("Using default description")
        return f"{city}, {state} is a community with unique local character and growing opportunities for digital innovation and business development."

def query_overpass(category, lat, lon, radius=15000):
    """Query OverPass API for local businesses"""
    debug_log(f"Querying OverPass for {category}...")
    
    overpass_queries = {
        'barbers': f"""
        [out:json][timeout:25];
        (
          node["shop"="hairdresser"](around:{radius},{lat},{lon});
          node["amenity"="barber"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        'bars': f"""
        [out:json][timeout:25];
        (
          node["amenity"="bar"](around:{radius},{lat},{lon});
          node["amenity"="pub"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        'diners_cafes': f"""
        [out:json][timeout:25];
        (
          node["amenity"="cafe"](around:{radius},{lat},{lon});
          node["amenity"="restaurant"](around:{radius},{lat},{lon});
          node["amenity"="fast_food"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        'libraries': f"""
        [out:json][timeout:25];
        (
          node["amenity"="library"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        'attractions_amusements': f"""
        [out:json][timeout:25];
        (
          node["tourism"="attraction"](around:{radius},{lat},{lon});
          node["tourism"="museum"](around:{radius},{lat},{lon});
          node["leisure"="park"](around:{radius},{lat},{lon});
        );
        out body;
        """,
        'coffee_shops': f"""
        [out:json][timeout:25];
        (
          node["amenity"="cafe"]["cuisine"="coffee_shop"](around:{radius},{lat},{lon});
          node["shop"="coffee"](around:{radius},{lat},{lon});
        );
        out body;
        """
    }
    
    if category not in overpass_queries:
        error_log(f"Unknown category: {category}")
        return []
    
    url = "https://overpass-api.de/api/interpreter"
    
    try:
        debug_log(f"Making OverPass query")
        response = requests.post(url, data=overpass_queries[category], timeout=30)
        response.raise_for_status()
        data = response.json()
        elements = data.get('elements', [])
        success_log(f"Found {len(elements)} {category}")
        if elements:
            debug_log(f"First business", elements[0].get('tags', {}).get('name', 'Unnamed'))
        return elements
    except Exception as e:
        error_log(f"OverPass query failed", e)
        return []

def process_business_data(businesses, category, city):
    """Process and format business data from OverPass"""
    debug_log(f"Processing {len(businesses)} businesses for {category}")
    processed = []
    for business in businesses[:3]:
        name = business.get('tags', {}).get('name', 'Unnamed Business')
        address = business.get('tags', {}).get('addr:street', 'Local Address')
        website = business.get('tags', {}).get('website', '#')
        
        processed.append({
            'name': name,
            'address': address,
            'website': website
        })
    
    if not processed:
        debug_log(f"No businesses found for {category}, using fallback data")
        fallbacks = {
            'barbers': [
                {'name': 'Local Barber Shop', 'address': 'Main Street', 'website': '#'},
                {'name': 'Professional Cuts', 'address': 'Downtown Area', 'website': '#'}
            ],
            'coffee_shops': [
                {'name': 'Local Coffee House', 'address': 'Central Avenue', 'website': '#'},
                {'name': 'Downtown Cafe', 'address': 'Business District', 'website': '#'}
            ],
            'bars': [
                {'name': 'Local Pub', 'address': 'Main Street', 'website': '#'},
                {'name': 'City Bar', 'address': 'Downtown Area', 'website': '#'}
            ],
            'diners_cafes': [
                {'name': 'Family Diner', 'address': 'Central Avenue', 'website': '#'},
                {'name': 'Local Cafe', 'address': 'Business District', 'website': '#'}
            ],
            'libraries': [
                {'name': 'Public Library', 'address': 'Community Center', 'website': '#'}
            ],
            'attractions_amusements': [
                {'name': 'Community Park', 'address': 'Recreation Area', 'website': '#'},
                {'name': 'Local Museum', 'address': 'Cultural District', 'website': '#'}
            ]
        }
        processed = fallbacks.get(category, [{'name': f'Local {category.title()}', 'address': 'Check local directory', 'website': '#'}])
    
    debug_log(f"Processed {len(processed)} businesses for {category}")
    return processed

def update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data):
    """Update the HTML template with new city data"""
    debug_log("📄 Starting HTML template update...")
    
    try:
        # Read original HTML
        debug_log("Reading original index.html...")
        with open('index.html', 'r', encoding='utf-8') as f:
            original_html = f.read()
        
        debug_log(f"Original HTML size: {len(original_html)} chars")
        debug_log("Checking original HTML content...")
        
        # Check what's actually in the original HTML
        if "Paoli, Oklahoma" in original_html:
            debug_log("✅ Found 'Paoli, Oklahoma' in original HTML")
        else:
            debug_log("❌ 'Paoli, Oklahoma' NOT found in original HTML - this is unexpected!")
            
        if "Ardmore" in original_html:
            debug_log("⚠️ Found 'Ardmore' in original HTML - this might be the issue!")
        
        html_content = original_html
        city, state = city_state.split('-')
        
        # Update city-state references
        debug_log("Replacing city references...")
        replacements = [
            ('Paoli, Oklahoma', f'{city}, {state}'),
            ('Paoli, OK', f'{city}, {state}'),
        ]
        
        for old, new in replacements:
            count = html_content.count(old)
            if count > 0:
                html_content = html_content.replace(old, new)
                debug_log(f"Replaced '{old}' with '{new}' ({count} occurrences)")
            else:
                debug_log(f"⚠️ '{old}' not found in HTML")
        
        # Update coordinates in footer
        debug_log("Updating coordinates...")
        html_content = re.sub(r'Latitude: [\d.-]+° N', f'Latitude: {lat:.2f}° N', html_content)
        html_content = re.sub(r'Longitude: [\d.-]+° W', f'Longitude: {abs(lon):.2f}° W', html_content)
        
        # Update Nexus Point section - FIXED REGEX
        debug_log("Updating Nexus Point section...")
        # More specific regex to catch the entire section
        nexus_pattern = r'<section id="paoli-ok"[^>]*>.*?<h2[^>]*>.*?</h2>.*?<p>.*?</p>.*?</section>'
        new_nexus_content = f'''
        <section id="paoli-ok" class="section paoli-section">
            <h2 class="section-title">The Nexus Point: {city}, {state}</h2>
            <p>
                {wiki_summary}
            </p>
        </section>
        '''
        
        nexus_matches = re.findall(nexus_pattern, html_content, re.DOTALL)
        debug_log(f"Found {len(nexus_matches)} Nexus Point sections")
        
        if nexus_matches:
            html_content = re.sub(nexus_pattern, new_nexus_content, html_content, flags=re.DOTALL)
            debug_log("Nexus Point section replaced")
        else:
            error_log("No Nexus Point section found to replace!")
            # Try alternative approach
            if "The Nexus Point:" in html_content:
                html_content = html_content.replace("The Nexus Point: Paoli, Oklahoma", f"The Nexus Point: {city}, {state}")
                debug_log("Used alternative replacement for Nexus Point")
        
        # Update weather section coordinates - FIXED REGEX
        debug_log("Updating weather coordinates...")
        weather_js_pattern = r'const lat = [\d.-]+;\s*//.*?\s*const lon = [\d.-]+;\s*//.*?'
        new_weather_js = f'const lat = {lat}; // {city}, {state} Latitude\n            const lon = {lon}; // {city}, {state} Longitude'
        
        weather_matches = re.findall(weather_js_pattern, html_content, re.DOTALL)
        debug_log(f"Found {len(weather_matches)} weather coordinate patterns")
        
        if weather_matches:
            html_content = re.sub(weather_js_pattern, new_weather_js, html_content, flags=re.DOTALL)
            debug_log("Weather coordinates replaced")
        else:
            error_log("No weather coordinates found to replace!")
        
        # Update local businesses sections
        debug_log("Updating local businesses...")
        business_sections = {
            'barbers': 'Barbershops',
            'coffee_shops': 'Coffee Shops', 
            'diners_cafes': 'Diners & Cafés',
            'bars': 'Local Bars & Pubs',
            'libraries': 'Libraries',
            'attractions_amusements': 'Attractions & Amusements'
        }
        
        for category, section_title in business_sections.items():
            debug_log(f"Updating {section_title}...")
            # More flexible pattern to match the section
            section_pattern = f'<h3>{section_title}</h3>.*?<ul class="business-list">.*?</ul>'
            new_section = f'<h3>{section_title}</h3>\n            <ul class="business-list">\n'
            
            for business in business_data.get(category, []):
                new_section += f'''
                <li>
                    <strong>{business["name"]}</strong>
                    <p>Local business serving the {city} community.</p>
                    <p>Address: {business["address"]}</p>
                    <a href="{business["website"]}" target="_blank">View Details</a>
                </li>
                '''
            
            new_section += '            </ul>'
            
            section_matches = re.findall(section_pattern, html_content, re.DOTALL)
            if section_matches:
                html_content = re.sub(section_pattern, new_section, html_content, flags=re.DOTALL)
                debug_log(f"Updated {section_title} section")
            else:
                debug_log(f"⚠️ {section_title} section not found")
        
        # Validate the updates
        debug_log("Validating HTML updates...")
        is_valid = validate_html_content(html_content, city_state)
        
        if is_valid:
            success_log("HTML template successfully updated and validated")
        else:
            error_log("HTML validation failed - some updates may not have been applied")
            
        debug_log(f"Final HTML size: {len(html_content)} chars")
        
        return html_content
        
    except Exception as e:
        error_log("Error updating HTML template", e)
        raise

def create_github_repo(city_state, updated_html):
    """Create new GitHub repository and push files"""
    debug_log("🐙 Starting GitHub repository creation...")
    
    try:
        debug_log("Initializing GitHub client...")
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        debug_log(f"Authenticated as: {user.login}")
        
        repo_name = f"{city_state.replace('-', '').replace(' ', '').lower()}"
        debug_log(f"Repository name: {repo_name}")
        
        # Create new repository
        debug_log("Creating repository...")
        repo = user.create_repo(
            repo_name,
            description=f"Eye Try A.I. - {city_state}",
            private=False,
            auto_init=False
        )
        success_log(f"Repository created: {repo.html_url}")
        
        # Create and push files
        debug_log("Creating files in repository...")
        files_to_push = {
            'index.html': updated_html,
            '.nojekyll': ''
        }
        
        for filename, content in files_to_push.items():
            try:
                repo.create_file(
                    filename,
                    f"Initial commit for {city_state}",
                    content,
                    branch="main"
                )
                success_log(f"Created {filename} in repository")
            except GithubException as e:
                debug_log(f"File {filename} creation issue", e)
        
        # Enable GitHub Pages with better error handling
        debug_log("Enabling GitHub Pages...")
        try:
            # Method 1: Try the direct approach
            repo.create_pages_site(branch="main", path="/")
            success_log("GitHub Pages enabled via create_pages_site")
        except Exception as e1:
            debug_log(f"Method 1 failed", e1)
            try:
                # Method 2: Try alternative approach
                repo.edit(has_pages=True, pages_branch="main")
                success_log("GitHub Pages enabled via edit method")
            except Exception as e2:
                error_log("Both GitHub Pages methods failed", e2)
                debug_log("GitHub Pages may need to be enabled manually in repository settings")
        
        # Verify the repository
        debug_log("Verifying repository setup...")
        try:
            contents = repo.get_contents("")
            file_count = len([item for item in contents if item.type == 'file'])
            debug_log(f"Repository has {file_count} files")
        except Exception as e:
            debug_log("Could not verify repository contents", e)
        
        return repo.html_url
        
    except GithubException as e:
        if e.status == 422:
            debug_log(f"Repository {repo_name} already exists")
            return f"https://github.com/{user.login}/{repo_name}"
        else:
            error_log("GitHub API error", e)
            raise

def main():
    debug_log("🚀 STARTING WEBSITE DEPLOYMENT PROCESS")
    debug_log(f"Python version: {sys.version}")
    debug_log(f"Current directory: {os.getcwd()}")
    debug_log(f"Files in directory: {os.listdir('.')}")
    debug_log(f"GITHUB_TOKEN present: {bool(GITHUB_TOKEN)}")
    
    try:
        # Read city from file
        city_state = read_city_from_file()
        debug_log(f"Processing city: {city_state}")
        
        # Get coordinates
        lat, lon = geocode_city(city_state)
        debug_log(f"Using coordinates: {lat}, {lon}")
        
        # Get weather data
        weather_data = get_weather_forecast(lat, lon)
        
        # Get Wikipedia summary  
        wiki_summary = get_wikipedia_summary(city_state)
        
        # Get business data from OverPass
        business_data = {}
        categories = ['barbers', 'bars', 'diners_cafes', 'libraries', 'attractions_amusements', 'coffee_shops']
        
        for i, category in enumerate(categories):
            debug_log(f"Processing category {i+1}/{len(categories)}: {category}")
            businesses = query_overpass(category, lat, lon)
            business_data[category] = process_business_data(businesses, category, city_state.split('-')[0])
            
            if i < len(categories) - 1:
                debug_log("Waiting 5 seconds before next API call...")
                time.sleep(5)
        
        # Update HTML template
        debug_log("Starting HTML template update...")
        updated_html = update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data)
        
        # Create GitHub repository
        debug_log("Creating GitHub repository...")
        repo_url = create_github_repo(city_state, updated_html)
        
        success_log(f"🎉 DEPLOYMENT COMPLETED: {repo_url}")
        
        # Write success file
        with open('deployment_success.txt', 'w') as f:
            f.write(f"Successfully deployed {city_state} to {repo_url}")
        debug_log("Success file written")
        
    except Exception as e:
        error_log("💥 DEPLOYMENT FAILED", e)
        
        # Write detailed error file
        with open('deployment_error.txt', 'w') as f:
            f.write(f"Deployment failed for {city_state}\n")
            f.write(f"Error: {str(e)}\n\n")
            f.write(f"Traceback:\n{traceback.format_exc()}")
        debug_log("Error file written")
        raise

if __name__ == "__main__":
    main()
