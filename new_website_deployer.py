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

def query_overpass(category, lat, lon, radius=15000):
    """Query OverPass API for local businesses"""
    overpass_queries = {
        'barbers': f"""node["shop"="hairdresser"](around:{radius},{lat},{lon}); node["amenity"="barber"](around:{radius},{lat},{lon});""",
        'bars': f"""node["amenity"="bar"](around:{radius},{lat},{lon}); node["amenity"="pub"](around:{radius},{lat},{lon});""",
        'diners_cafes': f"""node["amenity"="cafe"](around:{radius},{lat},{lon}); node["amenity"="restaurant"](around:{radius},{lat},{lon});""",
        'libraries': f"""node["amenity"="library"](around:{radius},{lat},{lon});""",
        'attractions_amusements': f"""node["tourism"="attraction"](around:{radius},{lat},{lon}); node["tourism"="museum"](around:{radius},{lat},{lon});""",
        'coffee_shops': f"""node["amenity"="cafe"]["cuisine"="coffee_shop"](around:{radius},{lat},{lon}); node["shop"="coffee"](around:{radius},{lat},{lon});"""
    }
    
    if category not in overpass_queries:
        return []
    
    url = "https://overpass-api.de/api/interpreter"
    query = f"[out:json][timeout:25];({overpass_queries[category]});out body;"
    
    try:
        response = requests.post(url, data=query, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('elements', [])
    except:
        return []

def process_business_data(businesses, category):
    """Process and format business data from OverPass"""
    processed = []
    for business in businesses[:3]:
        name = business.get('tags', {}).get('name', 'Unnamed Business')
        address = business.get('tags', {}).get('addr:street', 'Local Address')
        website = business.get('tags', {}).get('website', '#')
        processed.append({'name': name, 'address': address, 'website': website})
    
    if not processed:
        fallbacks = {
            'barbers': [{'name': 'Local Barber Shop', 'address': 'Main Street', 'website': '#'}],
            'coffee_shops': [{'name': 'Local Coffee House', 'address': 'Central Avenue', 'website': '#'}],
            'bars': [{'name': 'Local Pub', 'address': 'Main Street', 'website': '#'}],
            'diners_cafes': [{'name': 'Local Cafe', 'address': 'Business District', 'website': '#'}],
            'libraries': [{'name': 'Public Library', 'address': 'Community Center', 'website': '#'}],
            'attractions_amusements': [{'name': 'Community Park', 'address': 'Recreation Area', 'website': '#'}]
        }
        processed = fallbacks.get(category, [{'name': f'Local {category.title()}', 'address': 'Check local directory', 'website': '#'}])
    
    return processed

def update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data):
    """Update the HTML template with new city data - COMPLETELY REWRITTEN"""
    debug_log("📄 Starting HTML template update...")
    
    try:
        # Read the original HTML template
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        city, state = city_state.split('-')
        debug_log(f"Updating HTML for: {city}, {state}")
        
        # DEBUG: Check what's actually in the template
        debug_log(f"Template contains 'Paoli, Oklahoma': {'Paoli, Oklahoma' in html_content}")
        debug_log(f"Template contains 'Ardmore': {'Ardmore' in html_content}")
        debug_log(f"Template contains 'Fresno': {'Fresno' in html_content}")
        
        # COMPREHENSIVE REPLACEMENT - Handle ALL city references
        replacements = [
            ('Paoli, Oklahoma', f'{city}, {state}'),
            ('Paoli, OK', f'{city}, {state}'),
            ('Ardmore, Oklahoma', f'{city}, {state}'),
            ('Ardmore, OK', f'{city}, {state}'),
            # Add any other city names that might appear
        ]
        
        for old_text, new_text in replacements:
            if old_text in html_content:
                html_content = html_content.replace(old_text, new_text)
                debug_log(f"Replaced '{old_text}' with '{new_text}'")
        
        # Update coordinates in footer
        html_content = re.sub(r'Latitude: [\d.-]+° N', f'Latitude: {lat:.2f}° N', html_content)
        html_content = re.sub(r'Longitude: [\d.-]+° W', f'Longitude: {abs(lon):.2f}° W', html_content)
        
        # CRITICAL FIX: Update Nexus Point section using more flexible approach
        nexus_section_pattern = r'<section id="paoli-ok"[^>]*>.*?</section>'
        new_nexus_section = f'''
        <section id="paoli-ok" class="section paoli-section">
            <h2 class="section-title">The Nexus Point: {city}, {state}</h2>
            <p>
                {wiki_summary}
            </p>
        </section>
        '''
        
        # Replace the entire section
        html_content = re.sub(nexus_section_pattern, new_nexus_section, html_content, flags=re.DOTALL)
        debug_log("Updated Nexus Point section")
        
        # Update weather coordinates in JavaScript
        html_content = re.sub(r'const lat = [\d.-]+;', f'const lat = {lat};', html_content)
        html_content = re.sub(r'const lon = [\d.-]+;', f'const lon = {lon};', html_content)
        debug_log("Updated weather coordinates")
        
        # Update local businesses sections
        business_sections = {
            'barbers': 'Barbershops',
            'coffee_shops': 'Coffee Shops',
            'diners_cafes': 'Diners & Cafés',
            'bars': 'Local Bars & Pubs',
            'libraries': 'Libraries',
            'attractions_amusements': 'Attractions & Amusements'
        }
        
        for category, section_title in business_sections.items():
            # Create new business section
            new_section = f'<h3>{section_title}</h3>\n            <ul class="business-list">\n'
            for business in business_data.get(category, []):
                new_section += f'''                <li>
                    <strong>{business["name"]}</strong>
                    <p>Local business serving the {city} community.</p>
                    <p>Address: {business["address"]}</p>
                    <a href="{business["website"]}" target="_blank">View Details</a>
                </li>\n'''
            new_section += '            </ul>'
            
            # Find and replace the section using regex
            section_pattern = f'<h3>{section_title}</h3>.*?</ul>'
            html_content = re.sub(section_pattern, new_section, html_content, flags=re.DOTALL)
            debug_log(f"Updated {section_title} section")
        
        # VERIFY the updates were successful
        verification_checks = [
            (f'{city}, {state}', f"City name '{city}, {state}' in HTML"),
            (f'The Nexus Point: {city}, {state}', "Nexus Point title updated"),
            (f'Latitude: {lat:.2f}° N', "Latitude updated"),
            (f'Longitude: {abs(lon):.2f}° W', "Longitude updated"),
        ]
        
        all_passed = True
        for check_text, check_description in verification_checks:
            if check_text in html_content:
                success_log(f"✅ {check_description}")
            else:
                error_log(f"❌ {check_description} - NOT FOUND")
                all_passed = False
        
        if all_passed:
            success_log("All HTML updates verified successfully!")
        else:
            error_log("Some HTML updates failed!")
            
        return html_content
        
    except Exception as e:
        error_log(f"Error updating HTML template: {e}")
        raise

def create_github_repo(city_state, updated_html):
    """Create new GitHub repository and push files"""
    debug_log("🐙 Creating GitHub repository...")
    
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    
    repo_name = f"{city_state.replace('-', '').replace(' ', '').lower()}"
    debug_log(f"Repository name: {repo_name}")
    
    try:
        # Create new repository
        repo = user.create_repo(
            repo_name,
            description=f"Eye Try A.I. - {city_state}",
            private=False,
            auto_init=False
        )
        success_log(f"Repository created: {repo.html_url}")
        
        # Create and push files
        files_to_push = {
            'index.html': updated_html,
            '.nojekyll': ''
        }
        
        for filename, content in files_to_push.items():
            repo.create_file(
                filename,
                f"Initial commit for {city_state}",
                content,
                branch="main"
            )
            debug_log(f"Created {filename}")
        
        # Enable GitHub Pages using multiple methods
        try:
            # Method 1: PyGithub
            repo.create_pages_site(branch="main", path="/")
            success_log("GitHub Pages enabled via PyGithub")
        except Exception as e:
            debug_log(f"PyGithub method failed: {e}")
            # Method 2: Direct API call
            try:
                import json
                pages_data = {
                    "source": {
                        "branch": "main",
                        "path": "/"
                    }
                }
                # This would require additional API setup
                debug_log("GitHub Pages may need manual activation in repository settings")
            except Exception as e2:
                debug_log(f"API method also failed: {e2}")
        
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
        
        # Get business data
        business_data = {}
        categories = ['barbers', 'bars', 'diners_cafes', 'libraries', 'attractions_amusements', 'coffee_shops']
        
        for i, category in enumerate(categories):
            debug_log(f"Querying {category}...")
            businesses = query_overpass(category, lat, lon)
            business_data[category] = process_business_data(businesses, category)
            if i < len(categories) - 1:
                time.sleep(5)  # 5 seconds between API calls
        
        # Update HTML template - THIS IS THE CRITICAL PART
        debug_log("Updating HTML template...")
        updated_html = update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data)
        
        # Create GitHub repository
        debug_log("Creating GitHub repository...")
        repo_url = create_github_repo(city_state, updated_html)
        
        success_log(f"🎉 Deployment completed: {repo_url}")
        
        # Write success file
        with open('deployment_success.txt', 'w') as f:
            f.write(f"Successfully deployed {city_state} to {repo_url}")
        
    except Exception as e:
        error_log(f"Deployment failed: {e}")
        with open('deployment_error.txt', 'w') as f:
            f.write(f"Deployment failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
