import os
import requests
import json
import time
import random
import re

from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from itertools import cycle
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load proxies and prepare a round-robin iterator
def load_proxies():
    # Dynamically resolve the path to `proxy.txt`
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of the current script
    proxy_file = os.path.join(script_dir, '../data/proxy.txt')  # Path to proxy.txt
    proxies = []
    with open(proxy_file, 'r') as file:
        for line in file:
            # Each line: domain:port:user:pass
            parts = line.strip().split(':')
            if len(parts) == 4:
                domain, port, user, password = parts
                proxy_url = f"http://{user}:{password}@{domain}:{port}"
                proxies.append({
                    "http": proxy_url,
                    "https": proxy_url
                })
    return cycle(proxies)  # Create a round-robin iterator

proxy_pool = load_proxies()

# Function to get a single proxy
def get_proxy():
    return next(proxy_pool)


def get_random_proxy_key():
    """
    Select a random proxy key from the list of keys.
    """
    # Get proxy keys from .env file
    proxy_keys = os.getenv("PROXY_KEYS", "").split(",")

    if not proxy_keys or proxy_keys == [""]:
        raise ValueError("No proxy keys found in .env file. Please set PROXY_KEYS.")
    
    return random.choice(proxy_keys)

def get_rotate_proxy():
    """
    Get a rotating proxy using the specified rules with multiple proxy keys.
    
    :param proxy_keys: A list of proxy keys to use for the API requests.
    :return: A dictionary containing the proxy details (e.g., IP and port), or None if all attempts fail.
    """
    base_url = "https://wwproxy.com/api/client/proxy"
    headers = {"Content-Type": "application/json"}
    
    # Step 1: Get a random proxy key
    proxy_key = get_random_proxy_key()
    print(f"Selected proxy key: {proxy_key}")
    
    # Step 2: Call the `available` API
    available_url = f"{base_url}/available?key={proxy_key}&provinceId=-1"
    try:
        response = requests.get(available_url, headers=headers)
        response_data = response.json()
        
        if response_data.get("status") == "OK" and "proxy" in response_data.get("data", {}):
            print("Successfully retrieved proxy from 'available' API.")
            return response_data["data"]["proxy"]
        else:
            print("Failed to get proxy from 'available' API:", response_data.get("message"))
    except requests.RequestException as e:
        print(f"Error calling 'available' API: {e}")
    
    # Step 3: Fall back to the `current` API with retries
    current_url = f"{base_url}/current?key={proxy_key}"
    retry_attempts = 3
    for attempt in range(retry_attempts):
        try:
            response = requests.get(current_url, headers=headers)
            response_data = response.json()
            
            if response_data.get("status") == "OK" and "proxy" in response_data.get("data", {}):
                print(f"Successfully retrieved proxy from 'current' API on attempt {attempt + 1}.")
                return response_data["data"]["proxy"]
            else:
                print(f"Attempt {attempt + 1} failed for 'current' API:", response_data.get("message"))
        except requests.RequestException as e:
            print(f"Error calling 'current' API on attempt {attempt + 1}: {e}")
        
        # Delay before retrying
        if attempt < retry_attempts - 1:
            print("Retrying in 3 seconds...")
            time.sleep(3)
    
    print("All attempts to retrieve proxy failed.")
    return None

# Function to get a new token
def get_new_token(client_id, refresh_token, proxy):
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    payload = {
        'client_id': client_id,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'offline_access https://graph.microsoft.com/Mail.ReadWrite'
    }
    response = requests.post(url, data=payload, proxies=proxy)
    return response.json()

# Function to fetch messages
def get_messages(token, folder, proxy):
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers, proxies=proxy)
    messages = response.json()
    
    # Remove '@odata.context' if present
    if '@odata.context' in messages:
        del messages['@odata.context']
    
    return messages

# Get Hotmail messages
def get_hotmail_messages(client_id, refresh_token, proxy):
    token_response = get_new_token(client_id, refresh_token, proxy)
    print(f"New token: {token_response}")
    access_token = token_response.get('access_token')

    if access_token:
        # Fetch inbox and spam messages
        inbox_messages = get_messages(access_token, 'inbox', proxy)
        spam_messages = get_messages(access_token, 'junkemail', proxy)
        
        # Merge the `value` lists
        merged_messages = {"value": inbox_messages.get("value", []) + spam_messages.get("value", [])}
        return merged_messages
    else:
        print("Cannot get mailbox: Missing or invalid access token.")
        return {"value": []}

# Extract confirmation links for BlockMesh
def extract_confirmation_link(messages):
    for message in messages.get("value", []):
        if message.get("subject") == "Confirmation Email from BlockMesh Network":
            body_content = message.get("body", {}).get("content", "")
            soup = BeautifulSoup(body_content, 'html.parser')
            confirmation_link = soup.find("a", class_="button")
            if confirmation_link and confirmation_link.get("href"):
                return confirmation_link["href"]
    return None

# Extract confirmation links for Teneo
def extract_teneo_confirmation_link(messages):
    for message in messages.get("value", []):
        sender_address = (
                message.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
            )
        if sender_address != "nreply@noreply.teneo.pro":
            continue  # Skip if the sender's address does not match
        
        if message.get("subject") == "Confirm Your Signup":
            body_content = message.get("body", {}).get("content", "")
            soup = BeautifulSoup(body_content, 'html.parser')
            confirmation_link = soup.find("a", string=re.compile(r"Confirm Sign Up"))
            if confirmation_link and confirmation_link.get("href"):
                return confirmation_link["href"]
    return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Hotmail Services Management"})

# Define the /get-proxy endpoint
@app.route('/get-proxy', methods=['GET'])
def get_proxy_endpoint():
    proxy = get_rotate_proxy()
    if proxy:
        return proxy, 200  # Return the proxy as plain text
    else:
        return "No proxy available", 500  # Return error if no proxy is retrieved

@app.route('/block-mesh-confirmation', methods=['POST'])
def get_blockmesh_confirmation_link():
    data = request.get_json()
    client_id = data.get("client_id")
    refresh_token = data.get("refresh_token")

    if not client_id or not refresh_token:
        return jsonify({"error": "client_id and refresh_token are required"}), 400

    proxy = get_proxy()  # Select a single proxy for this request
    print(f"get data under proxy: {proxy}")
    
    messages = get_hotmail_messages(client_id, refresh_token, proxy)
    if messages is None:
        return jsonify({"error": "Failed to retrieve messages"}), 500

    confirm_link = extract_confirmation_link(messages)
    if confirm_link:
        return jsonify({"confirm_link": confirm_link}), 200
    else:
        return jsonify({"error": "Confirmation email not found"}), 404


@app.route('/teneo-confirmation', methods=['POST'])
def get_teneo_confirmation_link():
    data = request.get_json()
    client_id = data.get("client_id")
    refresh_token = data.get("refresh_token")

    if not client_id or not refresh_token:
        return jsonify({"error": "client_id and refresh_token are required"}), 400

    proxy = get_proxy()  # Select a single proxy for this request
    print(f"get data under proxy: {proxy}")

    messages = get_hotmail_messages(client_id, refresh_token, proxy)
    if messages is None:
        return jsonify({"error": "Failed to retrieve messages"}), 500
    
    confirm_link = extract_teneo_confirmation_link(messages)
    if confirm_link:
        return jsonify({"confirm_link": confirm_link}), 200
    else:
        return jsonify({"error": "Confirmation email not found"}), 404

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=6669)
