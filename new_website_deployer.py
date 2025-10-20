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

# Enhanced debugging
def debug_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔍 {message}")

def error_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ❌ {message}")

def success_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ✅ {message}")

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

def read_city_from_file():
    """Read city-state from new.txt file"""
    try:
        debug_log("Reading new.txt file...")
        with open('new.txt', 'r') as f:
            content = f.read().strip()
            if '-' in content:
                success_log(f"Found city-state: {content}")
                return content
            else:
                raise ValueError("File should contain city-state format like 'Dallas-Texas'")
    except FileNotFoundError:
        error_log("new.txt file not found")
        raise Exception("new.txt file not found")
    except Exception as e:
        error_log(f"Error reading new.txt: {e}")
        raise

def geocode_city(city_state):
    """Get latitude and longitude for city using Nominatim with proper headers"""
    city, state = city_state.split('-')
    debug_log(f"Geocoding {city}, {state}...")
    time.sleep(1)  # Rate limiting
    
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
        debug_log(f"Making request to Nominatim: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        debug_log(f"Response status: {response.status_code}")
        
        if response.status_code == 403:
            error_log("Nominatim blocked request (403 Forbidden)")
            return get_state_coordinates(state)
            
        response.raise_for_status()
        
        data = response.json()
        if not data:
            debug_log(f"No results found for {city_state}")
            return get_state_coordinates(state)
        
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        success_log(f"Coordinates found: {lat}, {lon}")
        return (lat, lon)
        
    except requests.exceptions.RequestException as e:
        error_log(f"Geocoding failed: {e}")
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
        debug_log(f"Using state coordinates for {state}: {coords}")
        return coords
    else:
        debug_log("Using US center coordinates as fallback")
        return (39.8283, -98.5795)  # US center

def get_weather_forecast(lat, lon):
    """Get 7-day weather forecast from Open-Meteo"""
    debug_log("Fetching weather data from Open-Meteo...")
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
        success_log("Weather data retrieved successfully")
        return response.json()
    except requests.exceptions.RequestException as e:
        error_log(f"Weather API failed: {e}")
        # Return mock weather data
        debug_log("Using mock weather data as fallback")
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
    time.sleep(1)  # Rate limiting
    
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    search_term = f"{city}, {state}"
    
    headers = {
        'User-Agent': 'EyeTryAICityDeployer/1.0 (https://github.com/TitanBusinessPros/O-2)'
    }
    
    try:
        full_url = url + search_term.replace(' ', '_')
        debug_log(f"Wikipedia URL: {full_url}")
        response = requests.get(full_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        summary = data.get('extract', f"{city}, {state} is a location with rich local history and community.")
        success_log("Wikipedia summary retrieved")
        return summary
    except Exception as e:
        error_log(f"Wikipedia API failed: {e}")
        debug_log("Using default city description")
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
        debug_log(f"Making OverPass query for {category}")
        response = requests.post(url, data=overpass_queries[category], timeout=30)
        response.raise_for_status()
        data = response.json()
        elements = data.get('elements', [])
        success_log(f"Found {len(elements)} {category}")
        return elements
    except Exception as e:
        error_log(f"OverPass query failed for {category}: {e}")
        return []

def process_business_data(businesses, category, city):
    """Process and format business data from OverPass"""
    debug_log(f"Processing {len(businesses)} businesses for {category}")
    processed = []
    for business in businesses[:3]:  # Limit to 3 per category
        name = business.get('tags', {}).get('name', 'Unnamed Business')
        address = business.get('tags', {}).get('addr:street', 'Local Address')
        website = business.get('tags', {}).get('website', '#')
        
        processed.append({
            'name': name,
            'address': address,
            'website': website
        })
    
    # Add fallback examples if no businesses found
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
    
    return processed

def update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data):
    """Update the HTML template with new city data"""
    debug_log("Updating HTML template with new city data...")
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        city, state = city_state.split('-')
        
        # Update city-state references throughout the document
        debug_log("Replacing city references...")
        html_content = html_content.replace('Paoli, Oklahoma', f'{city}, {state}')
        html_content = html_content.replace('Paoli, OK', f'{city}, {state}')
        html_content = re.sub(r'Latitude: [\d.-]+° N', f'Latitude: {lat:.2f}° N', html_content)
        html_content = re.sub(r'Longitude: [\d.-]+° W', f'Longitude: {abs(lon):.2f}° W', html_content)
        
        # Update Nexus Point section
        debug_log("Updating Nexus Point section...")
        nexus_pattern = r'<section id="paoli-ok".*?<p>(.*?)</p>'
        new_nexus_content = f'''
        <section id="paoli-ok" class="section paoli-section">
            <h2 class="section-title">The Nexus Point: {city}, {state}</h2>
            <p>
                {wiki_summary}
            </p>
        </section>
        '''
        html_content = re.sub(nexus_pattern, new_nexus_content, html_content, flags=re.DOTALL)
        
        # Update weather section coordinates
        debug_log("Updating weather coordinates...")
        weather_js_pattern = r'const lat = [\d.-]+;.*?const lon = [\d.-]+;'
        new_weather_js = f'const lat = {lat}; // {city}, {state} Latitude\n            const lon = {lon}; // {city}, {state} Longitude'
        html_content = re.sub(weather_js_pattern, new_weather_js, html_content, flags=re.DOTALL)
        
        # Update local businesses section
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
            section_pattern = f'<h3>{section_title}</h3>.*?</ul>'
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
            html_content = re.sub(section_pattern, new_section, html_content, flags=re.DOTALL)
        
        success_log("HTML template updated successfully")
        return html_content
        
    except Exception as e:
        error_log(f"Error updating HTML template: {e}")
        raise

def create_github_repo(city_state, updated_html):
    """Create new GitHub repository and push files"""
    debug_log("Creating GitHub repository...")
    
    try:
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
                debug_log(f"File {filename} may already exist: {e}")
        
        # Enable GitHub Pages
        try:
            debug_log("Enabling GitHub Pages...")
            repo.create_pages_site(branch="main", path="/")
            success_log("GitHub Pages enabled")
        except Exception as e:
            debug_log(f"GitHub Pages setup may need manual configuration: {e}")
        
        return repo.html_url
        
    except GithubException as e:
        if e.status == 422:  # Repository already exists
            debug_log(f"Repository {repo_name} already exists")
            return f"https://github.com/{user.login}/{repo_name}"
        else:
            error_log(f"GitHub API error: {e}")
            raise

def main():
    debug_log("🚀 Starting website deployment process...")
    debug_log(f"Python version: {sys.version}")
    debug_log(f"Current directory: {os.getcwd()}")
    debug_log(f"Files in directory: {os.listdir('.')}")
    
    try:
        # Read city from file
        city_state = read_city_from_file()
        
        # Get coordinates
        lat, lon = geocode_city(city_state)
        
        # Get weather data
        weather_data = get_weather_forecast(lat, lon)
        
        # Get Wikipedia summary
        wiki_summary = get_wikipedia_summary(city_state)
        
        # Get business data from OverPass with 5-second delays
        business_data = {}
        categories = ['barbers', 'bars', 'diners_cafes', 'libraries', 'attractions_amusements', 'coffee_shops']
        
        for i, category in enumerate(categories):
            businesses = query_overpass(category, lat, lon)
            business_data[category] = process_business_data(businesses, category, city_state.split('-')[0])
            
            if i < len(categories) - 1:  # Don't sleep after last category
                debug_log("Waiting 5 seconds for next OverPass query...")
                time.sleep(5)  # 5 seconds
        
        # Update HTML template
        updated_html = update_html_template(city_state, lat, lon, weather_data, wiki_summary, business_data)
        
        # Create GitHub repository
        repo_url = create_github_repo(city_state, updated_html)
        
        success_log(f"🎉 Deployment completed: {repo_url}")
        
        # Write success file for workflow
        with open('deployment_success.txt', 'w') as f:
            f.write(f"Successfully deployed {city_state} to {repo_url}")
        debug_log("Success file written")
        
    except Exception as e:
        error_log(f"Deployment failed: {e}")
        error_log(f"Traceback: {traceback.format_exc()}")
        
        # Write error file for workflow
        with open('deployment_error.txt', 'w') as f:
            f.write(f"Deployment failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")
        debug_log("Error file written")
        raise

if __name__ == "__main__":
    main()
