import requests
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_hotmail_messages(client_id, refresh_token):
    url = "https://script.google.com/macros/s/AKfycbxNTf4uHwwwwAxOvA_svRIB50aUw5UwvXXR_pUjdeOorO61uzrWG0o2xtzSsN22UZivVA/exec"
    payload = {
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def extract_confirmation_link(messages):
    for message in messages.get("value", []):
        if message.get("subject") == "Confirmation Email from BlockMesh Network":
            body_content = message.get("body", {}).get("content", "")
            soup = BeautifulSoup(body_content, 'html.parser')
            confirmation_link = soup.find("a", class_="button")
            if confirmation_link and confirmation_link.get("href"):
                return confirmation_link["href"]
    return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Hotmail Services Management"})

@app.route('/block-mesh-confirmation', methods=['POST'])
def get_confirmation_link():
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

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=6669)
