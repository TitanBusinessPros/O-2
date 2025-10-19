import glob
import os

# --- CONFIGURATION ---
# The exact string in your HTML files that needs to be replaced.
# Found in Eye-Paoli-Gold.html snippet: "Paoli, OK" and `Paoli, OK: ${paoliTimeString}`
OLD_CITY_STATE = "Paoli, OK" 

NEW_CITY_STATE_FILE = "new.txt"
# Find all HTML files in the current directory (change as needed)
FILES_TO_UPDATE = glob.glob('*.html') 
# ---------------------

def get_new_city_state():
    """Reads the new City, State string from the text file."""
    try:
        with open(NEW_CITY_STATE_FILE, 'r') as f:
            # Read the first line and remove any leading/trailing whitespace
            new_city_state = f.readline().strip()
        
        if not new_city_state:
             print(f"Error: '{NEW_CITY_STATE_FILE}' is empty. Cannot update.")
             return None
        return new_city_state
    except FileNotFoundError:
        print(f"Error: The file '{NEW_CITY_STATE_FILE}' was not found. Cannot update.")
        return None

def update_files():
    """Reads the new location and performs the replacement in all specified files."""
    new_location = get_new_city_state()
    if not new_location:
        return

    print(f"Replacing '{OLD_CITY_STATE}' with '{new_location}' in website files...")
    
    for filename in FILES_TO_UPDATE:
        try:
            # 1. Read the entire file content
            with open(filename, 'r') as file:
                file_content = file.read()

            # 2. Perform the global replacement using the Python string replace() method
            updated_content = file_content.replace(OLD_CITY_STATE, new_location)

            # Check if any replacement actually happened
            if updated_content != file_content:
                # 3. Write the updated content back to the file
                with open(filename, 'w') as file:
                    file.write(updated_content)
                print(f"  - Successfully updated: {filename}")
            
        except Exception as e:
            print(f"  - Error processing {filename}: {e}")

if __name__ == "__main__":
    update_files()
