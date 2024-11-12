import pandas as pd
import subprocess
import os
import sys

# Define the base path and the Excel file path
base_path = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(base_path, '../data/blockmesh.xlsx')

# Load the Excel file without headers
df = pd.read_excel(excel_path, header=None, engine='openpyxl')

# Iterate through the rows, skipping the first row (header)
for index, row in df.iloc[1:].iterrows():  # Start from the second row (index 1)
    # Map Excel columns to indices for readability
    email = row[1]        # Column B
    password = row[2]     # Column C
    ref_code = row[5]     # Column F
    proxy = row[6]        # Column G
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

    # Set up the environment with HTTP proxy
    env = os.environ.copy()
    env["HTTP_PROXY"] = proxy
    env["HTTPS_PROXY"] = proxy
    env["http_proxy"] = proxy
    env["https_proxy"] = proxy

    try:
        # Print the command as a string
        command_str = ' ' . join(command)
        print(f"Running command: {command_str} - under proxy: {proxy}")

        # Run the command with the specified proxy
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=env)
        print(result)

        # Check if the command was successful and contains "Successfully registered"
        if result.returncode == 0 and "Successfully registered" in result.stdout:
            df.at[index, 10] = 'OK'  # Mark as OK in column K
        else:
            print(f"Registration not successful for row {index}: {result.stdout}")

    except subprocess.CalledProcessError as e:
        # Print both stdout and stderr from the error
        print(f"Failed to register for email {email}")
        print("Error Output:")
        print(e.stdout)  # Command's standard output (if any)
        print(e.stderr)  # Command's error output (if any)

    break

# Save the updated Excel file
df.to_excel(excel_path, index=False, header=False, engine='openpyxl')
