import requests
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_new_token(client_id, refresh_token):
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    payload = {
        'client_id': client_id,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'offline_access https://graph.microsoft.com/Mail.ReadWrite'
    }
    response = requests.post(url, data=payload)
    return response.json()

def get_messages(token, folder='inbox'):
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    messages = response.json()
    
    # Loại bỏ phần '@odata.context' nếu có
    if '@odata.context' in messages:
        del messages['@odata.context']
    
    return messages

def get_hotmail_messages(client_id, refresh_token):
    token_response = get_new_token(client_id, refresh_token)
    access_token = token_response.get('access_token')

    if access_token:
        # get mail inbox
        inbox_messages = get_messages(access_token, 'inbox')
        # print("Inbox Messages:", json.dumps(inbox_messages, indent=2))
        
        # get junk email
        spam_messages = get_messages(access_token, 'junkemail')
        # print("Spam Messages:", json.dumps(spam_messages, indent=2))
        # Merge the `value` lists
        merged_messages = {"value": inbox_messages["value"] + spam_messages["value"]}
        return merged_messages
    else:
        print("Cannot get mailbox: Missing or invalid access token.")
        return {"value": []}
    

def extract_confirmation_link(messages):
    for message in messages.get("value", []):
        if message.get("subject") == "Confirmation Email from BlockMesh Network":
            body_content = message.get("body", {}).get("content", "")
            soup = BeautifulSoup(body_content, 'html.parser')
            confirmation_link = soup.find("a", class_="button")
            if confirmation_link and confirmation_link.get("href"):
                return confirmation_link["href"]
    return None

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

    messages = get_hotmail_messages(client_id, refresh_token)
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

    messages = get_hotmail_messages(client_id, refresh_token)
    if messages is None:
        return jsonify({"error": "Failed to retrieve messages"}), 500
    
    confirm_link = extract_teneo_confirmation_link(messages)
    if confirm_link:
        return jsonify({"confirm_link": confirm_link}), 200
    else:
        return jsonify({"error": "Confirmation email not found"}), 404

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=6669)
