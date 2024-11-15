import os
import csv
from collections import defaultdict
from datetime import datetime

# Define paths
proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
data_file = os.path.join(proj_dir, "data/profiles.csv")
docker_dir = os.path.join(proj_dir, "blockmesh_docker")
backup_dir = os.path.join(docker_dir, "bak")
env_file = os.path.join(docker_dir, ".env")

def backup_old_files():
    """Backup old docker-compose files to the bak/ directory."""
    os.makedirs(backup_dir, exist_ok=True)  # Ensure the backup directory exists
    for file in os.listdir(docker_dir):
        if file.startswith("docker-compose-") and file.endswith(".yml"):
            old_file_path = os.path.join(docker_dir, file)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_file_path = os.path.join(backup_dir, f"{file}.{timestamp}.bak")
            os.rename(old_file_path, new_file_path)
            print(f"Backed up {file} to {new_file_path}")

def parse_proxy(proxy):
    try:
        parts = proxy.split(':')
        if len(parts) == 4:
            ip, port, user, password = parts
            return f"http://{user}:{password}@{ip}:{port}"
        else:
            return None
    except Exception as e:
        print(f"Error parsing proxy '{proxy}': {e}")
        return None

def create_services():
    services_by_reference = defaultdict(dict)  # Group services by reference_code
    env_lines = []

    with open(data_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')

        for row in reader:
            # Validate required fields
            email = row["email"]
            password = row["password"]
            proxy = row["proxy"]
            profile_id = row["profile_id"]
            reference_code = row["reference_code"]

            if not email or not password or not proxy:
                continue

            # Format proxy
            formatted_proxy = parse_proxy(proxy)
            if not formatted_proxy:
                print(f"Skipping profile {profile_id} due to invalid proxy format.")
                continue

            # Add service to the appropriate reference_code group
            service_name = f"mesh{profile_id}"
            services_by_reference[reference_code][service_name] = {
                "image": "toanbk/blockmesh:latest",
                "environment": [
                    f"EMAIL=${{EMAIL_{profile_id}}}",
                    f"PASSWORD=${{PASSWORD_{profile_id}}}",
                    f"http_proxy=${{PROXY_{profile_id}}}",
                    f"HTTP_PROXY=${{PROXY_{profile_id}}}",
                    f"https_proxy=${{PROXY_{profile_id}}}",
                    f"HTTPS_PROXY=${{PROXY_{profile_id}}}",
                    f"no_proxy=${{NO_PROXY}}",
                    f"NO_PROXY=${{NO_PROXY}}"
                ],
                "restart": "always"
            }

            # Add to .env
            env_lines.append(f"EMAIL_{profile_id}={email}")
            env_lines.append(f"PASSWORD_{profile_id}='{password}'")
            env_lines.append(f"PROXY_{profile_id}={formatted_proxy}")

    return services_by_reference, env_lines

def write_compose_files(services_by_reference):
    os.makedirs(docker_dir, exist_ok=True)  # Ensure the directory exists

    for reference_code, services in services_by_reference.items():
        compose_file = os.path.join(docker_dir, f"docker-compose-{reference_code}.yml")
        with open(compose_file, 'w', encoding='utf-8') as f:
            # Write networks at the top
            f.write(f"networks:\n")
            f.write(f"  block-mesh-{reference_code}:\n")
            f.write(f"    driver: bridge\n\n")
            # Write services
            f.write("services:\n")
            for service_name, service_data in services.items():
                f.write(f"  {service_name}:\n")
                f.write(f"    image: {service_data['image']}\n")
                f.write(f"    environment:\n")
                for env_var in service_data['environment']:
                    f.write(f"      - {env_var}\n")
                f.write(f"    restart: {service_data['restart']}\n")
        print(f"Docker Compose file written: {compose_file}")

def write_env_file(env_lines):
    os.makedirs(docker_dir, exist_ok=True)  # Ensure the directory exists
    with open(env_file, 'a', encoding='utf-8') as f:
        f.write("\n".join(env_lines) + "\n")
    print(f".env file updated: {env_file}")

if __name__ == "__main__":
    # Step 0: Backup old Docker Compose files
    backup_old_files()

    # Step 1: Create services and environment variables
    services_by_reference, env_lines = create_services()
    if services_by_reference:
        # Step 2: Write Docker Compose files
        write_compose_files(services_by_reference)
        # Step 3: Write .env file
        write_env_file(env_lines)
    else:
        print("No valid profiles found in the CSV file.")
