#!/usr/bin/env python3
import paramiko
import paramiko.client
import requests
import hashlib
import base64
from dotenv import load_dotenv
import os
import logging

# Load environment variables from the .env file
load_dotenv()
# Set up logging
logging_file_path = os.getenv("LOGGING_FILE_PATH")
logging_level = os.getenv("LOGGING_LEVEL")

main_file_path = os.getenv("MAIN_FILE_PATH")
replicas = os.getenv("REPLICAS_IPS").split(",")

ssh_user = os.getenv("SSH_USER")
ssh_key_path = os.getenv("SSH_KEY_PATH")

# Validate environment variables
if not logging_file_path:
    logging.error("LOGGING_FILE_PATH environment variable is not set or empty.")
    exit(1)

if not logging_level:
    logging.error("LOGGING_LEVEL environment variable is not set or empty.")
    exit(1)

if not main_file_path:
    logging.error("MAIN_FILE_PATH environment variable is not set or empty.")
    exit(1)

if not ssh_user:
    logging.error("SSH_USER environment variable is not set or empty.")
    exit(1)

if not ssh_key_path:
    logging.error("SSH_KEY_PATH environment variable is not set or empty.")
    exit(1)
if not replicas:
    logging.error("REPLICAS_IPS environment variable is not set or empty.")
    exit(1)


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
    logging.info("Starting DNSMasq sync process...")
    # Get local file hash
    local_file_hash = sha256sum(main_file_path)
    logging.info(f"Local file hash: {local_file_hash}")
    for host in replicas:
        logging.info(f"Connecting to {host}...")
        ssh = paramiko.client.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(host, username=ssh_user, pkey=ssh_key_path)
        logging.info(f"Connected to {host}.")
        # Get remote file hash
        stdin, stdout, stderr = ssh.exec_command(f"sha256sum {main_file_path}")
        remote_file_hash = stdout.read().decode().split()[0]
        logging.info(f"Remote file hash for {host}: {remote_file_hash}")
        # Compare hashes
        if local_file_hash != remote_file_hash:
            logging.info(f"Hashes do not match for {host}. Updating file...")
            # Get the file content
            with open(main_file_path, 'r') as file:
                content = file.read()
            # Update the local file
            update_local_file(content, main_file_path)
            # Upload the file to the remote server
            sftp = ssh.open_sftp()
            sftp.put(main_file_path, main_file_path)
            sftp.close()
            logging.info(f"File updated on {host}.")
            logging.info("Reloading DNS...")
            _stdin, _stdout,_stderr = ssh.exec_command("pihole reloaddns")
            logging.info("DNS reloaded.")


        else:
            logging.info(f"Hashes match for {host}. No update needed.")
        ssh.close()
        logging.info(f"Disconnected from {host}.")
    logging.info("DNSMasq sync process completed.")
        

    
    


if __name__ == "__main__":
    main()