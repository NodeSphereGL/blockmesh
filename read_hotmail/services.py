import os
import requests
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from itertools import cycle

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
            confirmation_link = soup.find("a", text="Confirm Sign Up")
            if confirmation_link and confirmation_link.get("href"):
                return confirmation_link["href"]
    return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Hotmail Services Management"})

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
