import os
import requests
import subprocess
import shutil

# --- Configuration ---
# Your GitHub Username
GITHUB_USERNAME = "titanbusinesspros"
# The token name is 'NEW7', GitHub automatically loads this into the secrets variable
# The GITHUB_TOKEN environment variable MUST be set by the YAML (which it is).
GITHUB_TOKEN = os.environ.get('NEW7') 
# The file that contains the city name (e.g., "Paoli, OK")
CITY_FILE = "new.txt"
# The file containing the HTML content to be deployed
INDEX_FILE = "index.html" 
# The file containing the nojekyll directive
NOJEKYLL_FILE = ".nojekyll" 

# --- Functions ---

def read_and_clean_city_info(filename):
    """Reads the city/state and generates a repo-safe name."""
    try:
        with open(filename, 'r') as f:
            city_state = f.readline().strip()
            if not city_state:
                raise ValueError("City file is empty.")
            
            # Sanitize for URL/Repo name: "Paoli, OK" -> "paoli-ok"
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
        "private": False, # Must be False for free GitHub Pages deployment
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

def push_to_new_repo(repo_name, city_state):
    """Pushes files to the new city-specific repository's main branch."""
    
    # 1. Create a temporary deployment directory to isolate files
    deploy_dir = f"temp_deploy_{repo_name}"
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)
    
    # Copy files into the deployment directory
    shutil.copy(INDEX_FILE, deploy_dir)
    # Ensure .nojekyll is present for correct GitHub Pages rendering
    if os.path.exists(NOJEKYLL_FILE):
        shutil.copy(NOJEKYLL_FILE, deploy_dir)
    else:
         with open(os.path.join(deploy_dir, NOJEKYLL_FILE), 'w') as f:
            pass # Create empty .nojekyll file

    # 2. Change directory and initialize Git
    os.chdir(deploy_dir)
    
    # Configure Git identity for the commit
    subprocess.run(['git', 'config', 'user.name', 'GitHub Actions Bot'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'actions@github.com'], check=True)
    
    # Initialize the repo locally
    subprocess.run(['git', 'init'], check=True)
    
    # Add and commit files
    subprocess.run(['git', 'add', '.'], check=True)
    commit_message = f'Automated deployment for city site: {city_state}'
    subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    
    # 3. Set remote URL using PAT and push
    # The PAT is embedded in the URL to allow writing to the new repo
    remote_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
    
    # Set the branch name to 'main'
    subprocess.run(['git', 'branch', '-M', 'main'], check=True)
    
    print(f"Attempting to push content to the new remote repository...")

    try:
        # Push the 'main' branch to the new remote repository
        subprocess.run(['git', 'push', '-f', remote_url, 'main'], check=True)
        print(f"✅ Deployment for {repo_name} successful.")
        print(f"The new site URL is: https://{GITHUB_USERNAME}.github.io/{repo_name}/")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git Push failed to new repository: {e}")
    finally:
        # Clean up by moving back and removing the temp directory
        os.chdir('..')
        shutil.rmtree(deploy_dir)

# --- Main Execution ---
if __name__ == "__main__":
    city_state, repo_name = read_and_clean_city_info(CITY_FILE)
    
    if repo_name:
        # 1. Create the repository on GitHub (or verify it exists)
        if create_github_repo(repo_name):
            # 2. Push the files to the new repository
            push_to_new_repo(repo_name, city_state)
    else:
        print("Script failed to run: Invalid city information.")
