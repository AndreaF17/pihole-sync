#!/usr/bin/env python3
import requests
import hashlib
import base64
from dotenv import load_dotenv
import os
import logging

# Load environment variables from the .env file
load_dotenv()
token = os.getenv("GITHUB_TOKEN")
repo = os.getenv("GITHUB_REPO")
branch = os.getenv("GITHUB_BRANCH")
repo_folder_path = os.getenv("GITHUB_FOLDER_PATH")
local_folder_path = os.getenv("LOCAL_FOLDER_PATH")
logging_file_path = os.getenv("LOGGING_FILE_PATH")
logging_level = os.getenv("LOGGING_LEVEL")

# Configure logging
logging.basicConfig(filename=logging_file_path, level=logging_level, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging_level)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

def reload_dns():
    logging.info("Reloading DNS...")
    os.system("pihole reloaddns")
    logging.info("DNS reloaded.")

def sha256sum(filename):
    with open(filename, 'rb', buffering=0) as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def update_local_file(content, local_file_path):
    with open(local_file_path, 'w') as file:
        file.write(content)
        logging.info(f"File {local_file_path} updated successfully.")

def main():
    url = f"https://api.github.com/repos/{repo}/contents/{repo_folder_path}?ref={branch}"
    response = requests.get(url, headers={"Authorization": f"token {token}"})
    files = response.json()
    remote_files = {file['name'] for file in files if file['name'].endswith('.conf')}
    local_files = {file for file in os.listdir(local_folder_path) if file.endswith('.conf')}

    # Delete local files that are not in the remote repository
    for local_file in local_files - remote_files:
        local_file_path = os.path.join(local_folder_path, local_file)
        logging.info(f"Deleting local file {local_file_path} as it is not present in the remote repository.")
        os.remove(local_file_path)
        reload_dns()

    # Update or add files from the remote repository
    for file in files:
        if file['name'].endswith('.conf'):
            file_name = file['name']
            local_file_path = os.path.join(local_folder_path, file_name)
            content = requests.get(file['download_url']).text
            if os.path.exists(local_file_path):
                logging.info(f"File {local_file_path} exists.")
                local_file_sha256 = sha256sum(local_file_path)
                if hashlib.sha256(content.encode("utf-8")).hexdigest() != local_file_sha256:
                    logging.info(f"File {local_file_path} has been modified.")
                    update_local_file(content, local_file_path)
                    reload_dns()
                else:
                    logging.info(f"File {local_file_path} has not been modified.")
            else:
                logging.info(f"File {local_file_path} does not exist.")
                update_local_file(content, local_file_path)
                reload_dns()

if __name__ == "__main__":
    main()