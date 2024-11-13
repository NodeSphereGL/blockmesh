import pandas as pd
import subprocess
import os
import sys
import requests
import time

# Define the base path and the Excel file path
base_path = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(base_path, '../data/blockmesh.xlsx')

# Load the Excel file without headers
df = pd.read_excel(excel_path, header=None, engine='openpyxl')

# Define proxy
# proxy = 'http://sp4vawi47u:cqpaGruFLb9~2Rp98y@gate.smartproxy.com:7000'
proxy = 'http://user-sp4vawi47u-sessionduration-1:cqpaGruFLb9~2Rp98y@gate.smartproxy.com:10001'

# Function to get confirmation link with retry logic
def get_confirmation_link(client_id, refresh_token, retries=3, delay=10):
    url = "https://hotmail.nodesphere.net/block-mesh-confirmation"
    payload = {
        "client_id": client_id,
        "refresh_token": refresh_token
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "confirm_link" in data:
                    print("Confirmation link received.")
                    return data["confirm_link"]
            print(f"Attempt {attempt}: Failed to get confirmation link. Status Code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Attempt {attempt}: Request failed with error: {e}")

        # Wait before the next attempt
        time.sleep(delay)

    print("Failed to get confirmation link after retries.")
    return None

# Iterate through the rows, skipping the first row (header)
for index, row in df.iloc[1:].iterrows():  # Start from the second row (index 1)
    # Map Excel columns to indices for readability
    email = row[1]        # Column B
    password = row[2]     # Column C
    refresh_token = row[3]  # Column D
    client_id = row[4]    # Column E
    ref_code = row[5]     # Column F
    status = row[10]      # Column K (for checking 'OK')

    # Check if status is 'OK' or any required field is empty
    if status == 'OK' or pd.isna(email) or pd.isna(password) or pd.isna(ref_code) or pd.isna(proxy):
        continue  # Skip this row

    # Construct the command
    command = [
        "blockmesh-cli", "register",
        "--email", email,
        "--password", f"'{password}'",
        "--invite-code", ref_code
    ]

    # Print the command as a string
    command_str = ' '.join(command)
    print(f"Running command: {command_str} - under proxy: {proxy}")

    # Set up the environment with HTTP proxy
    env = os.environ.copy()
    env["HTTP_PROXY"] = proxy
    env["HTTPS_PROXY"] = proxy
    env["http_proxy"] = proxy
    env["https_proxy"] = proxy

    try:
        # Run the command with the specified proxy
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=env)
        print(result)

        # Check if the command was successful and contains "Successfully registered"
        if result.returncode == 0 and "Successfully registered" in result.stdout:
            # Write "OK" in column K to mark registration success
            df.at[index, 10] = 'OK'

            # Get confirmation link
            confirm_link = get_confirmation_link(client_id, refresh_token)
            if confirm_link:
                try:
                    # Simulate clicking the confirmation link
                    confirm_response = requests.get(confirm_link, proxies={'http': proxy, 'https': proxy})
                    if confirm_response.status_code == 200:
                        print("Confirmation successful.")
                        df.at[index, 6] = 'OK'  # Write 'OK' in column G for confirmation success
                    else:
                        print(f"Confirmation failed. Status code: {confirm_response.status_code}")
                except requests.RequestException as e:
                    print(f"Error confirming registration: {e}")
            else:
                print("Failed to get confirmation link after retries.")
        else:
            print(f"Registration not successful for row {index}: {result.stdout}")

    except subprocess.CalledProcessError as e:
        # Print both stdout and stderr from the error
        print(f"Failed to register for email {email}")
        print("Error Output:")
        print(e.stdout)  # Command's standard output (if any)
        print(e.stderr)  # Command's error output (if any)

# Save the updated Excel file
df.to_excel(excel_path, index=False, header=False, engine='openpyxl')
