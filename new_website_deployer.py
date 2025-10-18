import re
import os
from bs4 import BeautifulSoup

# The HTML file to be read and written to
HTML_FILENAME = "Final1.html"
# The text file containing the target city
LOCATION_FILENAME = "new.txt"

# --- Configuration and Data Simulation ---

# Default paragraph for when no specific Wikipedia summary is found (Task 5 in O-2-TASK.txt)
FALLBACK_PARAGRAPH_TEMPLATE = (
    "Starting a software guild in {City} brings together developers, designers, and tech enthusiasts "
    "to foster a strong sense of community and shared growth. A guild provides a structured environment "
    "for collaboration, where members can exchange knowledge, mentor newcomers, and work on local "
    "or open-source projects. It serves as a bridge between aspiring programmers and experienced "
    "professionals, helping to close skill gaps and encourage lifelong learning. By organizing "
    "workshops, coding sessions, and networking events, the guild strengthens the local tech ecosystem "
    "and inspires innovation. It also creates opportunities for partnerships with schools, businesses, "
    "and startups, stimulating economic growth and job creation. A software guild encourages ethical "
    "coding practices and a culture of craftsmanship, promoting quality and accountability in the tech "
    "community. Members benefit from both personal and professional development through peer feedback "
    "and shared problem-solving. Ultimately, a software guild transforms a city into a hub of creativity, "
    "collaboration, and technological advancement that benefits everyone involved."
)

# Simulated data for various cities
CITY_DATA = {
    "Dallas-Texas": {
        "city_display": "Dallas, Texas",
        "latitude": "32.7767° N",
        "longitude": "96.7970° W",
        "wiki_summary": "Dallas is a major commercial and cultural hub of the region, known for its significant historical role in the oil and cotton industries and its emergence as a powerful center for information technology and finance. The city is defined by its modern architecture and a commitment to arts and culture.",
        "libraries": ["Dallas Central Library", "J. Erik Jonsson Central Library", "Caruth Park Library"],
        "bars": ["The Rustic", "Parliament", "Midnight Rambler"],
        "restaurants": ["Pecan Lodge", "Uchi Dallas", "Town Hearth"],
        "barbers": ["Deep Ellum Barbers", "The Gents Place", "Blade Craft Barber Academy"]
    },
    "Broken-Bow-Oklahoma": {
        "city_display": "Broken Bow, Oklahoma",
        "latitude": "34.0381° N",
        "longitude": "94.7430° W",
        "wiki_summary": "Broken Bow is known as the gateway to Beavers Bend State Park and Broken Bow Lake, making it a popular destination for tourism, fishing, and boating. The town's economy is historically tied to the timber industry, and it offers a quiet, nature-focused community life.",
        "libraries": ["Broken Bow Public Library", "McCurtain County Library", "Idabel Public Library (Nearby)"],
        "bars": ["Beavers Bend Brewery (Nearby)", "Hochatown Distilling Co.", "Grateful Head Pizza Oven & Tap Room"],
        "restaurants": ["Hochatown BBQ", "Abendigos Grill & Patio", "The Blue Rooster"],
        "barbers": ["Broken Bow Barbershop", "The Cut Above", "McCurtain County Hair"]
    },
    "Stillwater-Oklahoma": {
        "city_display": "Stillwater, Oklahoma",
        "latitude": "36.1156° N",
        "longitude": "97.0583° W",
        "wiki_summary": None, # Simulating no wiki entry to trigger fallback (Task 5 in O-2-TASK.txt)
        "libraries": ["Stillwater Public Library", "Oklahoma State University Library", "Cimarron Library (Nearby)"],
        "bars": ["The World Famous Tumbleweed", "Iron Monk Brewery", "College Bar"],
        "restaurants": ["Eskimo Joe's", "The Garage", "Hideaway Pizza"],
        "barbers": ["The Stillwater Barbershop", "Headlines Barbershop", "The Campus Cut"]
    },
    "Oklahoma-City-Oklahoma": {
        "city_display": "Oklahoma City, Oklahoma",
        "latitude": "35.4676° N",
        "longitude": "97.5164° W",
        "wiki_summary": "Oklahoma City is the capital and largest city of Oklahoma. It's known for its cattle markets, large energy sector, and a vibrant cultural scene, including the revitalized Bricktown Entertainment District. It is also home to the OKC Thunder NBA team.",
        "libraries": ["Ronald J. Norick Downtown Library", "Belle Isle Library", "Southern Oaks Library"],
        "bars": ["Ponyboy", "The Jones Assembly", "OKC Taproom"],
        "restaurants": ["Vast", "Fuzzy's Taco Shop", "Mary Eddy's Kitchen x Lounge"],
        "barbers": ["The Barbershop OKC", "The Steady Hand", "Straight Edge Barbershop"]
    }
}

def load_target_city(location_file=LOCATION_FILENAME):
    """Reads the target city/state from the location file (new.txt)."""
    try:
        with open(location_file, 'r') as f:
            # Strip whitespace and normalize to the expected key format
            city_key = f.read().strip().replace(' ', '-').title()
        
        if city_key in CITY_DATA:
            print(f"Successfully loaded city: {city_key}")
            return city_key, CITY_DATA[city_key]
        else:
            print(f"Error: City '{city_key}' not found in simulated data. Using default (OKC).")
            return "Oklahoma-City-Oklahoma", CITY_DATA["Oklahoma-City-Oklahoma"]

    except FileNotFoundError:
        print(f"Error: Location file '{location_file}' not found. Using default (OKC).")
        return "Oklahoma-City-Oklahoma", CITY_DATA["Oklahoma-City-Oklahoma"]


def create_list_items(data_list):
    """Creates a BeautifulSoup tag object containing <li> elements from a list of strings."""
    # Use an unattached BeautifulSoup instance to create new tags
    builder = BeautifulSoup('', 'html.parser')
    ul_content = builder.new_tag('ul', class_='content-list')
    for item in data_list:
        li = builder.new_tag('li')
        li.string = item
        ul_content.append(li)
    return ul_content.contents


def update_html_content(html_file=HTML_FILENAME):
    """
    Performs all content updates in the HTML file based on the target city.
    """
    print(f"Starting update process for {html_file}...")
    
    city_key, data = load_target_city()
    display_name = data["city_display"]
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except FileNotFoundError:
        print(f"FATAL ERROR: HTML file '{html_file}' not found.")
        return

    # --- 1. Replace Coordinates (Task 1) ---
    coord_span = soup.find(id="footer-coordinates")
    if coord_span:
        coord_span.string = f"Lat: {data['latitude']}, Lon: {data['longitude']}"
        print(f"Updated coordinates to {data['latitude']}, {data['longitude']}")

    # --- 2. Replace all City Name placehoders (Task 2) ---
    city_placeholders = [
        soup.find(id="local-city-name"), # Header H1
        soup.find(id="welcome-city-name"), # Welcome H2
        soup.find(id="local-conditions-city-name") # Local Conditions Strong Tag
    ]
    
    for element in city_placeholders:
        if element:
            # Check for the local-conditions special case to maintain the strong tag content
            if element.get('id') == "local-conditions-city-name":
                 element.string = display_name
            elif element.get('id') == "local-city-name":
                 element.string = f"{display_name}"
            elif element.get('id') == "welcome-city-name":
                 element.string = f"{display_name}"

    # Update <title> and <meta> description
    title_tag = soup.find('title')
    if title_tag:
        title_tag.string = f"The Titan Software Guild: {display_name} Deployment Hub"
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        meta_desc['content'] = f"Join The Titan Software Guild in {display_name}! Master software, AI, and coding with local resources and community support."
    
    print(f"Updated all city name references to: {display_name}")

    # --- 3. Replace Libraries, Bars, Restaurants, Barbers lists (Tasks 3, 4, 5, 6) ---
    
    # Define a helper function to replace a list by ID
    def replace_list(list_id, new_data):
        target_ul = soup.find(id=list_id)
        if target_ul:
            # Clear all existing content
            target_ul.clear()
            # Append new <li> elements
            new_items = create_list_items(new_data)
            for item in new_items:
                target_ul.append(item)
            print(f"Updated list: {list_id} with {len(new_data)} items.")

    replace_list("libraries-list", data["libraries"])
    replace_list("bars-list", data["bars"])
    replace_list("restaurants-list", data["restaurants"])
    replace_list("barbers-list", data["barbers"])

    # --- 4. Replace Wikipedia Description (Task 7 & 8 in plan / Task 5 in O-2-TASK.txt) ---
    wiki_p = soup.find(id="wiki-description")
    if wiki_p:
        summary = data["wiki_summary"]
        
        if summary:
            # Task 7: Use the retrieved summary
            wiki_p.string = summary
            print("Updated wiki description with specific city summary.")
        else:
            # Task 8 / Task 5: Use the fallback paragraph
            fallback_text = FALLBACK_PARAGRAPH_TEMPLATE.format(City=display_name)
            wiki_p.string = fallback_text
            print("Updated wiki description with fallback paragraph.")

    # --- Write the final modified HTML back to the file ---
    with open(html_file, 'w', encoding='utf-8') as f:
        # Use pretty_print=True for better formatting retention
        f.write(str(soup.prettify()))
    
    print(f"Content replacement complete. {html_file} has been updated for {display_name}.")


if __name__ == "__main__":
    update_html_content()
