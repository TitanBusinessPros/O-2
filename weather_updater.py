import requests
import re
from github import Github
from datetime import datetime
import os
from time import sleep

# --- CONFIGURATION ---
REPO_PREFIX = "The-"
REPO_SUFFIX = "-Software-Guild"
# ---------------------

# --- API ENDPOINTS ---
# NOAA requires two calls: /points for grid data, then /forecast for the daily summary
NOAA_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
# ---------------------

def get_noaa_daily_forecast(lat, lon, city):
    """
    Performs the two-step NOAA API call to get the 7-day daily forecast.
    """
    # NOAA requires a unique User-Agent header
    headers = {
        'User-Agent': 'TitanSoftwareGuildUpdater/1.0 (contact@example.com)'
    }
    
    print(f"  -> Fetching NOAA Grid Data for {city} ({lat}, {lon})...")
    
    # STEP 1: Get the forecast grid URL
    try:
        points_url = NOAA_POINTS_URL.format(lat=lat, lon=lon)
        response = requests.get(points_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        forecast_url = response.json()['properties']['forecast']
        
    except Exception as e:
        print(f"  -> ERROR in NOAA Step 1 (Points): {e}")
        return None

    # STEP 2: Get the Daily Forecast (7-day summary)
    print("  -> Fetching Daily Forecast...")
    try:
        response = requests.get(forecast_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        periods = response.json()['properties']['periods']
        
        # Build HTML for the forecast summary
        forecast_html = "<h2>7-Day Forecast (Source: NOAA National Weather Service)</h2>\n"
        forecast_html += "<ul>\n"
        
        # We'll take up to 7 periods (usually Today/Tonight/Tomorrow/etc.)
        for period in periods[:7]:
            name = period['name']
            temp = period.get('temperature', 'N/A')
            forecast = period['detailedForecast']
            
            # Simple list item structure
            forecast_html += f"<li><strong>{name}:</strong> High/Low {temp}°F. {forecast}</li>\n"
            
        forecast_html += "</ul>"
        
        return forecast_html
        
    except Exception as e:
        print(f"  -> ERROR in NOAA Step 2 (Forecast): {e}")
        return None


def update_single_repo(g, repo):
    """Handles file update and commit for one repository."""
    try:
        # 1. Get the current index.html content
        contents = repo.get_contents("index.html")
        html_content = contents.decoded_content.decode()

    except Exception:
        # Skips if the repo is empty or doesn't have an index.html (as requested)
        print("  -> SKIPPED (No index.html found).")
        return

    # 2. Extract Lat/Lon from the HTML
    lat_match = re.search(r'(.*?)', html_content, re.DOTALL)
    lon_match = re.search(r'(.*?)', html_content, re.DOTALL)
    
    # If the standard placeholders are not used, use the coordinates that were inserted by the creation script
    # The creation script placed them here:
    if not lat_match:
        lat_match = re.search(r'(.*)', html_content)
    if not lon_match:
        lon_match = re.search(r'(.*)', html_content)
        
    
    if not lat_match or not lon_match:
        # Check for the coordinates inserted by the creation script logic
        # Assuming the creation script logic is in place, lat/lon will be the next text after the initial comment.
        try:
            # We assume the creation script has replaced the placeholder with the value: 32.7767
            lat = html_content.split('')[1].split('')[1].split('', now_utc)

    # 5. Commit the changes
    commit_message = f"Daily weather update for {city} on {now_utc}"
    
    repo.update_file(
        "index.html",
        commit_message,
        updated_html,
        contents.sha # Required to update a file
    )
    print(f"  -> Successfully committed weather update to {repo.name}.")


def main():
    """Main function to discover all repos and update weather."""
    # 1. AUTHENTICATE
    token = os.environ.get('GH_TOKEN')
    if not token:
        print("FATAL: GH_TOKEN environment variable not set.")
        return

    g = Github(token)
    user = g.get_user()
    
    print("--- STARTING DAILY WEATHER UPDATE ---")

    # 2. DISCOVER ALL REPOSITORIES
    # The search query uses the naming convention to find all relevant repos
    search_query = f"{REPO_PREFIX} in:name {REPO_SUFFIX} in:name user:{user.login}"
    
    # Fetch all matching repos using the GitHub API (This consumes the GH API limit)
    all_repos = g.search_repositories(query=search_query)
    
    repo_list = list(all_repos)
    if not repo_list:
        print("No existing city repositories found matching the naming convention.")
        return

    print(f"Found {len(repo_list)} repositories to update.")
    
    # 3. Iterate through all found repos with a short delay (good practice)
    update_delay = 5 # seconds
    
    for repo in repo_list:
        print(f"\nProcessing repository: {repo.name}")
        update_single_repo(g, repo)
        sleep(update_delay) 
        
    print("\n*** ALL WEATHER UPDATES COMPLETE ***")


if __name__ == "__main__":
    main()
