import os
import requests
import subprocess
import shutil

# --- Configuration ---
GITHUB_USERNAME = "titanbusinesspros"
GITHUB_TOKEN = os.environ.get('NEW7') 
CITY_FILE = "new.txt"

# 🛑 CRITICAL FIX: Use the actual source file name
SOURCE_HTML_FILE = "Eye-Paoli-Gold.html"
# 🛑 CRITICAL FIX: The file MUST be renamed to index.html for GitHub Pages to serve the root site
TARGET_DEPLOY_FILE = "index.html" 

NOJEKYLL_FILE = ".nojekyll" 

# --- Functions ---

def read_and_clean_city_info(filename):
    """Reads the city/state and generates a repo-safe name."""
    try:
        with open(filename, 'r') as f:
            city_state = f.readline().strip()
            if not city_state:
                raise ValueError("City file is empty.")
            
            repo_name = city_state.lower().replace(', ', '-').replace(' ', '-')
            return city_state, repo_name
    except Exception as e:
        print(f"Error reading city file: {e}")
        return None, None

def create_github_repo(repo_name):
    """Creates a new, public GitHub repository using the API."""
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN (NEW7) not found in environment variables.")
        return False
        
    api_url = f"https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "name": repo_name,
        "description": f"Dynamic GitHub Pages site for {repo_name}",
        "private": False, 
    }

    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Repository '{repo_name}' created successfully.")
        return True
    elif response.status_code == 422 and "name already exists" in response.text:
        print(f"⚠️ Repository '{repo_name}' already exists. Continuing to deployment.")
        return True
    else:
        print(f"❌ Failed to create repository '{repo_name}'. Status: {response.status_code}")
        print("API Response:", response.json())
        return False

def activate_github_pages(repo_name):
    """ACTIVATES GitHub Pages on the new repository after files are pushed."""
    print(f"Attempting to activate GitHub Pages for {repo_name}...")
    
    api_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
      "source": {
        "branch": "main",
        "path": "/"
      }
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code == 201 or response.status_code == 409:
        print(f"✅ GitHub Pages activated successfully for {repo_name} (or was already active).")
        return True
    else:
        print(f"❌ Failed to activate GitHub Pages for {repo_name}. Status: {response.status_code}")
        print("API Response:", response.json())
        return False


def push_to_new_repo(repo_name, city_state):
    """Pushes files to the new city-specific repository's main branch."""
    
    # 1. Create temporary deployment directory
    deploy_dir = f"temp_deploy_{repo_name}"
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)
    
    # 🛑 CRITICAL FIX: Copy the source file and rename it to the target name (index.html)
    if os.path.exists(SOURCE_HTML_FILE):
        shutil.copy(SOURCE_HTML_FILE, os.path.join(deploy_dir, TARGET_DEPLOY_FILE))
    else:
        print(f"❌ ERROR: Source file '{SOURCE_HTML_FILE}' not found in the repository.")
        return False
        
    # Copy .nojekyll
    if os.path.exists(NOJEKYLL_FILE):
        shutil.copy(NOJEKYLL_FILE, deploy_dir)
    else:
         with open(os.path.join(deploy_dir, NOJEKYLL_FILE), 'w') as f:
            pass

    # 2. Initialize Git and commit
    os.chdir(deploy_dir)
    
    subprocess.run(['git', 'config', 'user.name', 'GitHub Actions Bot'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'actions@github.com'], check=True)
    
    subprocess.run(['git', 'init'], check=True)
    subprocess.run(['git', 'add', TARGET_DEPLOY_FILE, NOJEKYLL_FILE], check=True)
    commit_message = f'Automated deployment for city site: {city_state}'
    subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    
    # 3. Set remote URL and push
    remote_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
    
    subprocess.run(['git', 'branch', '-M', 'main'], check=True)
    
    success = False
    try:
        subprocess.run(['git', 'push', '-f', remote_url, 'main'], check=True)
        print(f"✅ Git push successful for {repo_name}.")
        success = True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git Push failed to new repository: {e}")
    finally:
        os.chdir('..')
        shutil.rmtree(deploy_dir)
        return success

# --- Main Execution ---
if __name__ == "__main__":
    # Check if the required files exist before starting
    if not os.path.exists(CITY_FILE):
        print(f"FATAL ERROR: Required file '{CITY_FILE}' not found.")
        exit(1)
    if not os.path.exists(SOURCE_HTML_FILE):
        print(f"FATAL ERROR: Source HTML file '{SOURCE_HTML_FILE}' not found.")
        exit(1)
        
    city_state, repo_name = read_and_clean_city_info(CITY_FILE)
    
    if repo_name:
        # 1. Create the repository on GitHub
        if create_github_repo(repo_name):
            # 2. Push the files to the new repository
            if push_to_new_repo(repo_name, city_state):
                # 3. Activate GitHub Pages after files are pushed
                activate_github_pages(repo_name)
    else:
        print("Script failed to run: Invalid city information.")
