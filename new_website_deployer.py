import requests
import time
import os
import re
import json
from datetime import datetime
from github import Github, Auth

def debug_log(message):
    """Enhanced debug logging with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def read_city_file():
    """Read city from new.txt"""
    try:
        with open('new.txt', 'r') as f:
            city_name = f.read().strip()
            debug_log(f"✓ City from new.txt: '{city_name}'")
            return city_name
    except Exception as e:
        debug_log(f"✗ ERROR reading new.txt: {str(e)}")
        return None

def parse_city_state(city_name):
    """Parse city and state from input like 'Dallas-Texas' or 'Dallas Texas'"""
    # Handle different formats
    if '-' in city_name:
        parts = city_name.split('-')
    elif ',' in city_name:
        parts = city_name.split(',')
    else:
        parts = city_name.split()
    
    if len(parts) >= 2:
        city = parts[0].strip()
        state = parts[-1].strip()
    else:
        city = city_name.strip()
        state = None
    
    debug_log(f"✓ Parsed: City='{city}', State='{state}'")
    return city, state

def create_safe_repo_name(city_name):
    """Create repository name without spaces or special characters"""
    safe_name = re.sub(r'[^a-zA-Z0-9]', '-', city_name)
    safe_name = re.sub(r'-+', '-', safe_name).strip('-')
    repo_name = f"The-{safe_name}-Software-Guild"
    debug_log(f"✓ Safe repository name: {repo_name}")
    return repo_name

def geocode_city_enhanced(city_name):
    """Enhanced geocoding with timezone detection"""
    debug_log(f"🌍 Geocoding: {city_name}")
    
    city, state = parse_city_state(city_name)
    
    # Major cities database with timezones
    major_cities = {
        "Nashville": {"lat": "36.1627", "lon": "-86.7816", "display_name": "Nashville, Tennessee, USA", "timezone": "America/Chicago"},
        "Detroit": {"lat": "42.3314", "lon": "-83.0458", "display_name": "Detroit, Michigan, USA", "timezone": "America/Detroit"},
        "Dallas": {"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, Texas, USA", "timezone": "America/Chicago"},
        "Tulsa": {"lat": "36.1540", "lon": "-95.9928", "display_name": "Tulsa, Oklahoma, USA", "timezone": "America/Chicago"},
        "Boston": {"lat": "42.3601", "lon": "-71.0589", "display_name": "Boston, Massachusetts, USA", "timezone": "America/New_York"},
        "Chicago": {"lat": "41.8781", "lon": "-87.6298", "display_name": "Chicago, Illinois, USA", "timezone": "America/Chicago"},
        "New York": {"lat": "40.7128", "lon": "-74.0060", "display_name": "New York, New York, USA", "timezone": "America/New_York"},
        "Los Angeles": {"lat": "34.0522", "lon": "-118.2437", "display_name": "Los Angeles, California, USA", "timezone": "America/Los_Angeles"},
        "Miami": {"lat": "25.7617", "lon": "-80.1918", "display_name": "Miami, Florida, USA", "timezone": "America/New_York"},
        "Seattle": {"lat": "47.6062", "lon": "-122.3321", "display_name": "Seattle, Washington, USA", "timezone": "America/Los_Angeles"},
        "Phoenix": {"lat": "33.4484", "lon": "-112.0740", "display_name": "Phoenix, Arizona, USA", "timezone": "America/Phoenix"},
        "Denver": {"lat": "39.7392", "lon": "-104.9903", "display_name": "Denver, Colorado, USA", "timezone": "America/Denver"},
        "Austin": {"lat": "30.2672", "lon": "-97.7431", "display_name": "Austin, Texas, USA", "timezone": "America/Chicago"},
        "Houston": {"lat": "29.7604", "lon": "-95.3698", "display_name": "Houston, Texas, USA", "timezone": "America/Chicago"},
        "Atlanta": {"lat": "33.7490", "lon": "-84.3880", "display_name": "Atlanta, Georgia, USA", "timezone": "America/New_York"}
    }
    
    if city in major_cities:
        debug_log(f"✓ Using pre-defined coordinates for {city}")
        return major_cities[city]
    
    # Query Nominatim for other cities
    query = f"{city}, {state}, USA" if state else f"{city}, USA"
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
    headers = {'User-Agent': 'EyeTryAI-CityDeployer/1.0 (contact: traxispathfinder@gmail.com)'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.json():
            result = response.json()[0]
            
            # Determine timezone based on longitude
            lon = float(result['lon'])
            if lon < -127 or lon > -114:
                timezone = "America/Los_Angeles"  # Pacific
            elif lon < -114 and lon > -102:
                timezone = "America/Denver"  # Mountain
            elif lon < -102 and lon > -87:
                timezone = "America/Chicago"  # Central
            else:
                timezone = "America/New_York"  # Eastern
            
            result['timezone'] = timezone
            debug_log(f"✓ Found: {result.get('display_name')}")
            debug_log(f"✓ Timezone: {timezone}")
            return result
    except Exception as e:
        debug_log(f"✗ Geocoding error: {str(e)}")
    
    return None

def get_wikipedia_summary_enhanced(city_name):
    """Get Wikipedia data with citation"""
    debug_log(f"📚 Fetching Wikipedia for {city_name}")
    
    city, state = parse_city_state(city_name)
    
    try:
        # Try with state first
        if state:
            search_term = f"{city}, {state}"
        else:
            search_term = city
            
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search_term.replace(' ', '_').replace(',', '')}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            extract = data.get('extract', '')
            if extract:
                # Add citation
                extract += f" <small><em>(Source: Wikipedia/Wikimedia Foundation, {datetime.now().strftime('%Y')})</em></small>"
                debug_log(f"✓ Wikipedia success with citation")
                return extract
    except Exception as e:
        debug_log(f"✗ Wikipedia failed: {str(e)}")
    
    # Fallback with citation
    fallback = f"{city_name} is a vibrant community with a rich history and growing technology sector. <small><em>(Local information pending)</em></small>"
    return fallback

def query_overpass_enhanced(amenity_type, lat, lon, city_name, radius=0.3):
    """Enhanced Overpass query with nearby city fallback"""
    bbox = f"{float(lat)-radius},{float(lon)-radius},{float(lat)+radius},{float(lon)+radius}"
    
    # Enhanced queries for better results
    queries = {
        'libraries': '[out:json];(node["amenity"="library"](BBOX);way["amenity"="library"](BBOX);relation["amenity"="library"](BBOX););out center;',
        'bars': '[out:json];(node["amenity"="bar"](BBOX);node["amenity"="pub"](BBOX);way["amenity"="bar"](BBOX);way["amenity"="pub"](BBOX););out center;',
        'restaurants': '[out:json];(node["amenity"="restaurant"](BBOX);node["amenity"="cafe"](BBOX);way["amenity"="restaurant"](BBOX););out center;',
        'barbers': '[out:json];(node["shop"="hairdresser"](BBOX);node["shop"="barber"](BBOX);way["shop"="hairdresser"](BBOX););out center;',
        'coffee': '[out:json];(node["amenity"="cafe"](BBOX);node["cuisine"="coffee_shop"](BBOX);way["amenity"="cafe"](BBOX););out center;',
        'attractions': '[out:json];(node["tourism"~"attraction|museum|gallery|theme_park"](BBOX);way["tourism"~"attraction|museum|gallery|theme_park"](BBOX););out center;'
    }
    
    query = queries.get(amenity_type, '').replace('BBOX', bbox)
    
    debug_log(f"🔍 Querying Overpass for {amenity_type} in {city_name}...")
    
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=30,
            headers={'User-Agent': 'EyeTryAI-CityDeployer/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            
            # Filter out unnamed places and process results
            named_elements = []
            for elem in elements:
                tags = elem.get('tags', {})
                if tags.get('name'):
                    # Calculate distance from center
                    elem_lat = elem.get('lat') or elem.get('center', {}).get('lat')
                    elem_lon = elem.get('lon') or elem.get('center', {}).get('lon')
                    if elem_lat and elem_lon:
                        distance = ((float(elem_lat) - float(lat))**2 + (float(elem_lon) - float(lon))**2)**0.5
                        elem['distance'] = distance
                        named_elements.append(elem)
            
            # Sort by distance
            named_elements.sort(key=lambda x: x.get('distance', 999))
            
            debug_log(f"✓ Found {len(named_elements)} named {amenity_type}")
            
            # If not enough results, try larger radius
            if len(named_elements) < 3 and radius < 1.0:
                debug_log(f"⟳ Expanding search radius for {amenity_type}...")
                time.sleep(10)  # Required delay before retry
                return query_overpass_enhanced(amenity_type, lat, lon, city_name, radius=radius+0.3)
            
            return named_elements[:10]  # Return top 10 for selection
        else:
            debug_log(f"✗ Overpass error: {response.status_code}")
    except Exception as e:
        debug_log(f"✗ Overpass exception: {str(e)}")
    
    return []

def format_business_html(businesses, business_type, city_name):
    """Format businesses into HTML with proper structure"""
    html = f"<h3>{business_type}</h3>\n<ul class=\"business-list\">\n"
    
    count = 0
    for biz in businesses:
        if count >= 3:
            break
            
        tags = biz.get('tags', {})
        name = tags.get('name', 'Unknown Business')
        
        # Get address components
        street = tags.get('addr:street', '')
        housenumber = tags.get('addr:housenumber', '')
        city = tags.get('addr:city', city_name)
        postcode = tags.get('addr:postcode', '')
        
        # Build address
        address_parts = []
        if housenumber and street:
            address_parts.append(f"{housenumber} {street}")
        elif street:
            address_parts.append(street)
        
        if city:
            address_parts.append(city)
        if postcode:
            address_parts.append(f"OK {postcode}")
        
        address = ", ".join(address_parts) if address_parts else f"Located in {city_name} area"
        
        # Description based on type
        descriptions = {
            'Barbershops': tags.get('description', 'Professional haircuts and grooming services'),
            'Coffee Shops': tags.get('description', 'Fresh coffee and specialty drinks'),
            'Diners & Cafés': tags.get('cuisine', 'American cuisine and local favorites'),
            'Local Bars & Pubs': tags.get('description', 'Local gathering spot for drinks and entertainment'),
            'Libraries': tags.get('description', 'Community library and information services'),
            'Attractions & Amusements': tags.get('description', 'Local point of interest')
        }
        
        description = descriptions.get(business_type, 'Local business')
        
        # Add phone if available
        phone = tags.get('phone', tags.get('contact:phone', ''))
        
        # Add website if available
        website = tags.get('website', tags.get('contact:website', ''))
        
        html += f"""                <li>
                    <strong>{name}</strong>
                    <p>{description}</p>
                    <p>Address: {address}</p>"""
        
        if phone:
            html += f"\n                    <p>Phone: {phone}</p>"
        
        if website:
            html += f'\n                    <a href="{website}" target="_blank">Visit Website</a>'
        else:
            html += f'\n                    <a href="https://www.google.com/search?q={name.replace(" ", "+")}+{city_name.replace(" ", "+")}" target="_blank">Search on Google</a>'
        
        html += "\n                </li>\n"
        count += 1
    
    # If we don't have enough businesses, add placeholder
    while count < 3:
        count += 1
        nearby_text = f"(Check nearby areas for more {business_type.lower()})"
        html += f"""                <li>
                    <strong>Additional {business_type[:-1]} Coming Soon</strong>
                    <p>More local businesses being added</p>
                    <p>{nearby_text}</p>
                    <a href="https://www.google.com/search?q={business_type.replace(" ", "+")}+near+{city_name.replace(" ", "+")}" target="_blank">Search for More</a>
                </li>\n"""
    
    html += "            </ul>"
    return html

def create_website_content_enhanced(city_name, location_data, wikipedia_text, amenities):
    """Enhanced content creation with all replacements"""
    debug_log("📝 Creating enhanced website content...")
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        debug_log(f"✗ Cannot read index.html: {str(e)}")
        return None
    
    city, state = parse_city_state(city_name)
    full_city_name = f"{city}, {state}" if state else city
    
    # Replace all city references
    # Find and replace Paoli references
    content = re.sub(r'Paoli, Oklahoma', full_city_name, content)
    content = re.sub(r'Paoli', city, content)
    
    # Replace Ardmore references
    content = re.sub(r'Ardmore, OK', full_city_name, content)
    content = re.sub(r'Ardmore', city, content)
    
    # Replace any other Oklahoma City references
    content = re.sub(r'Oklahoma City', city, content)
    content = re.sub(r'OKC', city, content)
    
    # Replace coordinates in footer
    lat = location_data.get('lat', '0')
    lon = location_data.get('lon', '0')
    
    # Format coordinates for display
    lat_display = f"{abs(float(lat)):.2f}° {'N' if float(lat) > 0 else 'S'}"
    lon_display = f"{abs(float(lon)):.2f}° {'W' if float(lon) < 0 else 'E'}"
    
    # Replace footer coordinates with citation
    footer_text = f"{full_city_name} | Latitude: {lat_display}, Longitude: {lon_display}"
    footer_text += "\n            <p><small>Location data © OpenStreetMap contributors & Nominatim</small></p>"
    
    # Find and replace footer paragraph
    content = re.sub(
        r'<p>.*?Latitude:.*?Longitude:.*?</p>',
        f'<p>{footer_text}</p>',
        content,
        flags=re.DOTALL
    )
    
    # Replace coordinates in JavaScript for weather
    content = re.sub(r'const lat = [\d\.\-]+;', f'const lat = {lat};', content)
    content = re.sub(r'const lon = [\d\.\-]+;', f'const lon = {lon};', content)
    
    # Replace timezone in JavaScript
    timezone = location_data.get('timezone', 'America/Chicago')
    content = re.sub(
        r"timeZone: '[^']+'",
        f"timeZone: '{timezone}'",
        content
    )
    
    # Update the clock display text
    content = re.sub(
        r'timeElement\.innerHTML = `[^:]+:',
        f'timeElement.innerHTML = `{city}:',
        content
    )
    
    # Replace "The Nexus Point" section with Wikipedia text
    nexus_section = f"""<h2 class="section-title">The Nexus Point: {full_city_name}</h2>
            <p>
                {wikipedia_text}
            </p>"""
    
    # Find and replace the Nexus Point section
    content = re.sub(
        r'<h2 class="section-title">The Nexus Point:.*?</h2>.*?<p>.*?</p>',
        nexus_section,
        content,
        flags=re.DOTALL
    )
    
    # Update weather section subtitle
    content = re.sub(
        r'<p class="section-subtitle">A prediction of the elemental forces in.*?</p>',
        f'<p class="section-subtitle">A prediction of the elemental forces in {full_city_name}. <small>(Data: Open-Meteo.com)</small></p>',
        content
    )
    
    # Replace local businesses section
    businesses_html = f"""<h2 class="section-title">Local Businesses In & Near {full_city_name}</h2>
            <p class="section-subtitle">A curated directory of quality local spots in our community.</p>

            """
    
    # Add each business category
    business_categories = [
        ('barbers', 'Barbershops'),
        ('coffee', 'Coffee Shops'),
        ('restaurants', 'Diners & Cafés'),
        ('bars', 'Local Bars & Pubs'),
        ('libraries', 'Libraries')
    ]
    
    for amenity_key, display_name in business_categories:
        if amenity_key in amenities and amenities[amenity_key]:
            businesses_html += format_business_html(amenities[amenity_key], display_name, city) + "\n            \n            "
        else:
            # Add placeholder if no data
            businesses_html += f"<h3>{display_name}</h3>\n<ul class=\"business-list\">\n"
            businesses_html += f"""                <li>
                    <strong>Local {display_name} Information</strong>
                    <p>Business information being updated for {city} area</p>
                    <p>Check back soon for local listings</p>
                    <a href="https://www.google.com/search?q={display_name.replace(' ', '+')}+{city.replace(' ', '+')}" target="_blank">Search on Google</a>
                </li>
            </ul>\n            \n            """
    
    # Find and replace the entire local businesses section
    content = re.sub(
        r'<section id="local-businesses".*?</section>',
        f'<section id="local-businesses" class="section local-business-section">\n            {businesses_html}</section>',
        content,
        flags=re.DOTALL
    )
    
    # Replace attractions section if we have data
    if 'attractions' in amenities and amenities['attractions']:
        attractions_html = f"""<h2 class="section-title">Attractions & Amusements</h2>
            <p class="section-subtitle">Must-see local destinations in {full_city_name}.</p>

            <ul class="attraction-list">"""
        
        count = 0
        for attraction in amenities['attractions'][:3]:
            tags = attraction.get('tags', {})
            name = tags.get('name', 'Local Attraction')
            description = tags.get('description', tags.get('tourism', 'Point of interest'))
            website = tags.get('website', '')
            
            attractions_html += f"""
                <li>
                    <strong>{name}</strong>
                    <p>{description}</p>"""
            
            if website:
                attractions_html += f'\n                    <a href="{website}" target="_blank">View Website</a>'
            else:
                attractions_html += f'\n                    <a href="https://www.google.com/search?q={name.replace(" ", "+")}+{city.replace(" ", "+")}" target="_blank">Learn More</a>'
            
            attractions_html += "\n                </li>"
            count += 1
        
        attractions_html += "\n            </ul>"
        
        # Replace attractions section
        content = re.sub(
            r'<section id="attractions".*?</section>',
            f'<section id="attractions" class="section">\n            {attractions_html}\n        </section>',
            content,
            flags=re.DOTALL
        )
    
    # Update club section
    content = re.sub(
        r'Start the.*? A\.I\. Club',
        f'Start the {city} A.I. Club',
        content
    )
    
    content = re.sub(
        r'founding members in.*? to launch',
        f'founding members in {full_city_name} to launch',
        content
    )
    
    debug_log("✓ All template replacements completed")
    return content

def enable_github_pages(repo):
    """Enable GitHub Pages on the repository"""
    debug_log("🌐 Enabling GitHub Pages...")
    try:
        # First check if Pages is already enabled
        try:
            pages_info = repo.get_pages()
            debug_log(f"✓ GitHub Pages already enabled: {pages_info.html_url}")
            return True
        except:
            # Enable Pages via API
            headers = {
                "Authorization": f"token {os.getenv('GH_TOKEN')}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            response = requests.post(
                f"https://api.github.com/repos/{repo.owner.login}/{repo.name}/pages",
                headers=headers,
                json=data
            )
            if response.status_code in [200, 201]:
                debug_log("✓ GitHub Pages enabled successfully")
                return True
            else:
                debug_log(f"⚠ Could not auto-enable Pages: {response.status_code}")
                return False
    except Exception as e:
        debug_log(f"⚠ Pages enablement issue: {str(e)}")
        return False

def create_nojekyll(repo):
    """Create .nojekyll file to disable Jekyll processing"""
    try:
        repo.create_file(".nojekyll", "Add .nojekyll", "")
        debug_log("✓ Created .nojekyll file")
    except:
        debug_log("ℹ .nojekyll already exists or couldn't be created")

def deploy_to_github(repo_name, content):
    """Deploy to GitHub using repo secret"""
    debug_log(f"🚀 Deploying to GitHub: {repo_name}")
    
    try:
        # Use GH_TOKEN from repository secret
        token = os.getenv('GH_TOKEN')
        if not token:
            debug_log("✗ GH_TOKEN (NEW7) not found in environment!")
            return False
        
        debug_log("✓ GitHub token found, authenticating...")
        
        # Use proper authentication
        g = Github(auth=Auth.Token(token))
        user = g.get_user()
        
        # Create repo
        try:
            repo = user.get_repo(repo_name)
            debug_log(f"✓ Repository exists: {repo_name}")
        except:
            repo = user.create_repo(
                repo_name, 
                auto_init=False, 
                description=f"AI Software Guild Website - Powered by Eye Try A.I.",
                homepage=f"https://{user.login}.github.io/{repo_name}"
            )
            debug_log(f"✓ Created repository: {repo_name}")
        
        # Create/update index.html
        try:
            contents = repo.get_contents("index.html")
            repo.update_file("index.html", f"Update {repo_name} website", content, contents.sha)
            debug_log("✓ Updated index.html")
        except:
            repo.create_file("index.html", f"Deploy {repo_name} website", content)
            debug_log("✓ Created index.html")
        
        # Add .nojekyll file
        create_nojekyll(repo)
        
        # Enable GitHub Pages
        enable_github_pages(repo)
        
        debug_log("=" * 60)
        debug_log("🎉 DEPLOYMENT SUCCESSFUL!")
        debug_log(f"📁 Repository: https://github.com/{user.login}/{repo_name}")
        debug_log(f"🌐 Pages URL: https://{user.login}.github.io/{repo_name}")
        debug_log(f"⚙️ Settings: https://github.com/{user.login}/{repo_name}/settings/pages")
        debug_log("=" * 60)
        return True
        
    except Exception as e:
        debug_log(f"✗ GitHub deployment failed: {str(e)}")
        import traceback
        debug_log(traceback.format_exc())
        return False

def main():
    debug_log("=" * 60)
    debug_log("🚀 EYE TRY A.I. CITY WEBSITE DEPLOYER")
    debug_log("=" * 60)
    
    # 1. Read city
    city_name = read_city_file()
    if not city_name:
        debug_log("✗ No city name found in new.txt")
        return
    
    # 2. Create safe repository name
    repo_name = create_safe_repo_name(city_name)
    
    # 3. Geocode with enhanced features
    location = geocode_city_enhanced(city_name)
    if not location:
        debug_log("✗ Could not geocode location")
        return
    
    # 4. Get Wikipedia data with citation
    wiki_text = get_wikipedia_summary_enhanced(city_name)
    
    # 5. Query amenities with proper 10-second delays
    amenities = {}
    amenity_types = ['libraries', 'bars', 'restaurants', 'barbers', 'coffee', 'attractions']
    
    debug_log("-" * 40)
    debug_log("📍 Querying local businesses...")
    debug_log("⏱️ Note: 10-second delay between each query (Overpass API requirement)")
    debug_log("-" * 40)
    
    for i, amenity in enumerate(amenity_types):
        amenities[amenity] = query_overpass_enhanced(amenity, location['lat'], location['lon'], city_name)
        
        if i < len(amenity_types) - 1:
            debug_log(f"⏱️ Waiting 10 seconds before next query ({i+1}/{len(amenity_types)-1})...")
            time.sleep(10)  # CRITICAL: 10-second delay as requested
    
    debug_log("-" * 40)
    debug_log("✓ All business queries completed")
    debug_log("-" * 40)
    
    # 6. Create enhanced website content
    content = create_website_content_enhanced(city_name, location, wiki_text, amenities)
    if not content:
        debug_log("✗ Failed to create website content")
        return
    
    # 7. Deploy to GitHub
    if deploy_to_github(repo_name, content):
        debug_log(f"\n✅ {city_name} website successfully deployed!")
        debug_log("\n💡 IMPORTANT NOTES:")
        debug_log("1. GitHub Pages may take 5-10 minutes to activate")
        debug_log("2. If site doesn't appear, manually enable Pages:")
        debug_log(f"   - Go to repository settings")
        debug_log(f"   - Select 'Pages' from sidebar")
        debug_log(f"   - Source: 'Deploy from a branch'")
        debug_log(f"   - Branch: 'main' / folder: '/'")
        debug_log(f"   - Click 'Save'")
        debug_log("\n📋 CITATIONS INCLUDED:")
        debug_log("   • Wikipedia/Wikimedia - City information")
        debug_log("   • OpenStreetMap/Nominatim - Location data")
        debug_log("   • Open-Meteo.com - Weather forecasts")
    else:
        debug_log("✗ Deployment failed - check error messages above")

if __name__ == "__main__":
    main()
