import subprocess
import lib.config as config
import requests
import random
import string
import os
import lib.bh_utils as bh_utils
import zipfile
import shutil
import json
import time

current_dir = os.getcwd()
docker_compose_dir = config.load_env_variables()["docker_compose_dir"]


def check_is_up():
    # check if bloodhound is up
    try:
        url = config.base_url() + "/api/v2/sso-providers"
        response = requests.get(url, timeout=10)
        # If we get any response (including 429 rate limit), the server is up
        # 200-299: Success
        # 400-499: Client errors (but server is responding)
        # 500-599: Server errors (but server is responding)
        if response.status_code < 600:
            return True
        else:
            print(f"[!] BloodHound returned unexpected status {response.status_code} for {url}")
            return False
    except requests.exceptions.Timeout:
        print(f"[!] Timeout connecting to {config.base_url()} - BloodHound may be starting up")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"[!] Cannot connect to {config.base_url()} - Connection error: {e}")
        return False
    except Exception as e:
        print(f"[!] Error checking BloodHound status: {type(e).__name__}: {e}")
        return False


def start_containers():
    # check for docker compose file
    if os.path.exists(os.path.join(docker_compose_dir, "docker-compose.yml")):
        # docker compose up --remove-orphans -d
        os.system("docker compose up --remove-orphans --pull=always -d")
    elif os.path.exists(os.path.join(current_dir, "docker-compose.yml")):
        # docker compose up --remove-orphans -d
        os.system("docker compose up --remove-orphans --pull=always -d")
    else:
        print("Docker compose file not found")


def stop_containers():
    # check for docker compose file
    if os.path.exists(os.path.join(docker_compose_dir, "docker-compose.yml")):
        # docker compose down
        os.system("docker compose down")
    elif os.path.exists(os.path.join(current_dir, "docker-compose.yml")):
        # docker compose down
        os.system("docker compose down")
    else:
        print("Docker compose file not found")


def restart_containers():
    # check for docker compose file
    if os.path.exists(os.path.join(docker_compose_dir, "docker-compose.yml")):
        # docker compose down
        os.system("docker compose down")
        # docker compose up --remove-orphans -d
        os.system("docker compose up --remove-orphans --pull=always -d")
    elif os.path.exists(os.path.join(current_dir, "docker-compose.yml")):
        # docker compose down
        os.system("docker compose down")
        # docker compose up --remove-orphans -d
        os.system("docker compose up --remove-orphans --pull=always -d")
    else:
        print("Docker compose file not found")


def show_docker_logs():
    # check for docker compose file
    if os.path.exists(os.path.join(docker_compose_dir, "docker-compose.yml")):
        os.system("docker compose logs -f")
    elif os.path.exists(os.path.join(current_dir, "docker-compose.yml")):
        os.system("docker compose logs -f")
    else:
        print("Docker compose file not found")


def get_user_info():
    # GET, /api/v2/self
    method = "GET"
    uri = f"/api/v2/self"
    response = bh_utils.pass_request(method, uri)
    response_json = response.json()
    response_data = response_json["data"]
    if response.status_code == 200:
        return response_data
    else:
        return "Failed to get user info"


def generate_password():
    while True:
        password = "".join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=16))
        if (
            len(password) >= 12  # Ensure at least 12 characters
            and any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c in string.punctuation for c in password)  # Ensure at least one special character
            and sum(c.isdigit() for c in password) >= 1
        ):
            break
    return password


def retrieve_initial_password():
    os.chdir(docker_compose_dir)
    # Run the `docker compose logs` command and capture the output
    logs = subprocess.run(["docker", "compose", "logs"], capture_output=True, text=True).stdout
    os.chdir(current_dir)

    # Filter the lines containing "Initial Password Set To:"
    filtered_logs = [line for line in logs.splitlines() if "Initial Password Set To:" in line]
    # Process the filtered logs to extract the relevant part
    for line in filtered_logs:
        try:
            # Extract the part after the first "#" and then after the second ":"
            password = line.split("#", 1)[1].split(":", 1)[1].strip().split()[0]
            return password
        except IndexError:
            return "No password found"


def login_get_token(method, uri, username, password):
    data = {"login_method": "secret", "username": username, "secret": password}
    headers = {"User-Agent": "bhe-python-sdk 0001", "Content-Type": "application/json"}
    url = config.base_url() + uri
    response = requests.request(method, url, headers=headers, json=data)
    response_json = response.json()

    # Check if 'data' is in the response
    if "data" in response_json:
        # print(f"Login successful: {response_json}")
        this_token = response_json["data"]["session_token"]
        user_id = response_json["data"]["user_id"]
        must_change_password = response_json["data"]["auth_expired"]
        # update the env variables
        if must_change_password is True:
            config.update_env_variables("MUST_CHANGE_PASSWORD", "yes")
        else:
            config.update_env_variables("MUST_CHANGE_PASSWORD", "no")
        return [user_id, this_token, must_change_password]
    else:
        print(f"Login failed: {response_json.get('errors', 'No error message')}")
        return [None, None]  # Return None if login fails


def change_password(method, uri, bearer_token, current_password, new_password):
    data = {"current_secret": current_password, "needs_password_reset": False, "secret": new_password}
    headers = {
        "User-Agent": "bhe-python-sdk 0001",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }
    url = config.base_url() + uri
    response = requests.request(method, url, headers=headers, json=data)
    print(f"change_password new password: {new_password}")
    return response


def change_password_api():
    current_password = config.load_env_variables()["password"]
    new_password = config.load_env_variables()["new_password"]
    if new_password == "none" or new_password == current_password:
        new_password = generate_password()
        config.update_env_variables("BHE_NEW_PASSWORD", new_password)
    user_id = get_user_info()["id"]
    method = "PUT"
    uri = f"/api/v2/bloodhound-users/{user_id}/secret"
    data = {"current_secret": current_password, "needs_password_reset": False, "secret": new_password}
    response = bh_utils.pass_request(method, uri, data)
    if response.status_code == 200:
        return new_password
    else:
        return "Failed to change password"


def change_initial_password(BH_NEW_PASS_TEMP, user_id, bearer_token, BH_INIT_PASS):
    change_password("PUT", f"/api/v2/bloodhound-users/{user_id}/secret", bearer_token, BH_INIT_PASS, BH_NEW_PASS_TEMP)
    print(f"New password: {BH_NEW_PASS_TEMP}")
    return BH_NEW_PASS_TEMP


def create_initial_api_key(bearer_token, user_id, token_name):
    # POST, /api/v2/bloodhound-users/:user_id/api-key
    method = "POST"
    uri = f"/api/v2/tokens"
    data = {"token_name": token_name, "user_id": user_id}
    headers = {
        "User-Agent": "bhe-python-sdk 0001",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }
    url = config.base_url() + uri
    response = requests.request(method, url, headers=headers, json=data)
    return response.json()


def create_api_key(token_name="New Token from BHTK"):
    # POST, /api/v2/tokens
    user_id = get_user_info()["id"]
    method = "POST"
    uri = f"/api/v2/tokens"
    data = {"token_name": token_name, "user_id": user_id}
    response = bh_utils.pass_request(method, uri, data)
    response_json = response.json()
    response_data = response_json["data"]
    return response_data


def update_env_api_key(api_key_response):
    token_name = api_key_response["data"]["name"]
    token_id = api_key_response["data"]["id"]
    token_key = api_key_response["data"]["key"]

    config.update_env_variables("BHE_TOKEN_ID", token_id)
    config.update_env_variables("BHE_TOKEN_KEY", token_key)
    return [token_id, token_key, token_name]


def list_neo4j_databases(neo4j_data_dir=os.path.join(os.getcwd(), "data", "neo4j-data")):
    # list the directories in the neo4j data directory
    # return the directories
    neo4j_data_dir = os.path.join(neo4j_data_dir, "databases")
    directories = [
        d
        for d in os.listdir(neo4j_data_dir)
        if d not in ["system", "logs", "store_lock", "transactions", "server_id", "dbms", "databases"]
    ]
    return directories


def get_current_db():
    # GET, /api/v2/database
    current_db = config.load_env_variables()["neo4j_database_name"]

    return current_db


def set_current_db(db_name):
    # set the current database in the .env file
    config.update_env_variables("NEO4J_DATABASE_NAME", db_name)
    return db_name


# /api/v2/clear-database
# {"deleteAssetGroupSelectors":[],"deleteCollectedGraphData":false,"deleteDataQualityHistory":false,"deleteFileIngestHistory":true,"deleteSourceKinds":[]}
def clear_inject_history():
    data = {
        "deleteAssetGroupSelectors": [],
        "deleteCollectedGraphData": False,
        "deleteDataQualityHistory": False,
        "deleteFileIngestHistory": True,
        "deleteSourceKinds": [],
    }
    response = bh_utils.pass_request("POST", "/api/v2/clear-database", data)
    if response.status_code == 200:
        return "Database cleared"
    else:
        return "Failed to clear database"


def delete_all_data():
    data = {
        "deleteAssetGroupSelectors": [1, 2],
        "deleteCollectedGraphData": False,
        "deleteDataQualityHistory": True,
        "deleteFileIngestHistory": True,
        "deleteSourceKinds": [1, 2, 0],
    }
    response = bh_utils.pass_request("POST", "/api/v2/clear-database", data)
    if response.status_code == 200:
        return "All data deleted"
    else:
        return "Failed to delete all data"


def run_analysis():
    # PUT, /api/v2/analysis
    response = bh_utils.pass_request("PUT", "/api/v2/analysis", {})
    if response.status_code == 202:
        return "Analysis started"
    else:
        return "Failed to start analysis"


def datapipe_status():
    # GET, /api/v2/datapipe/status
    response = bh_utils.pass_request("GET", "/api/v2/datapipe/status")
    if response.status_code == 200:
        return response.json()
    else:
        return "Failed to get datapipe status"


def initialize_upload():
    # POST, /api/v2/file-upload/start
    response = bh_utils.pass_request("POST", "/api/v2/file-upload/start", {})
    if response.status_code == 201:
        return response.json()["data"]
    else:
        return "Failed to initialize upload"


def end_upload(upload_id):
    # POST, /api/v2/file-upload/:upload_id/end
    response = bh_utils.pass_request("POST", f"/api/v2/file-upload/{upload_id}/end", {})
    if response.status_code == 200:
        return "Upload ended"
    else:
        return "Failed to end upload"


def upload_file(upload_id, data):
    # POST, /api/v2/file-upload/:upload_id
    response = bh_utils.pass_request("POST", f"/api/v2/file-upload/{upload_id}", data)
    if response.status_code == 200:
        return "File uploaded"
    else:
        return "Failed to upload file"


def upload_file_process(upload_id, data_path):
    try:
        current_dir = os.getcwd()
        # POST, /api/v2/file-upload/:upload_id
        # check if data_path is a dir or a zip file
        # if is a zip, unzip it to a temp dir (data/temp)
        # if is a dir, copy the dir to data/temp
        if data_path.endswith(".zip"):
            with zipfile.ZipFile(data_path, "r") as zip_ref:
                zip_ref.extractall(os.path.join(current_dir, "data", "temp"))
            data_path = os.path.join(current_dir, "data", "temp")
        else:
            # make sure data/temp exists
            if not os.path.exists(os.path.join(current_dir, "data", "temp")):
                os.makedirs(os.path.join(current_dir, "data", "temp"))
            # copy the folder content to data/temp
            for file in os.listdir(data_path):
                if file.endswith(".json"):
                    shutil.copy(os.path.join(data_path, file), os.path.join(current_dir, "data", "temp"))
            data_path = os.path.join(current_dir, "data", "temp")
        temp_dir = os.path.join(current_dir, "data", "temp")
        # parse json in the dir
        for file in os.listdir(temp_dir):
            if file.endswith(".json"):
                print(f"Uploading {file}")
                with open(os.path.join(temp_dir, file), "r") as f:
                    json_data = json.load(f)
                    # print(json_data)
                    upload_file(upload_id, json_data)
        # end the upload
        print(f"Ending upload {upload_id}")
        end_upload(upload_id)
        # delete the temp dir
        shutil.rmtree(temp_dir)
        return "File upload process completed"
    except Exception as e:
        print(f"Error uploading file: {e}")
        # end the upload
        print(f"Ending upload {upload_id}")
        end_upload(upload_id)
        # delete the temp dir
        shutil.rmtree(temp_dir)
        return f"Failed to upload file: {e}"


def get_latest_upload_data():
    # GET, /api/v2/file-upload?skip=0&limit=10&sort_by=-id
    response = bh_utils.pass_request("GET", f"/api/v2/file-upload?skip=0&limit=10&sort_by=-id")
    if response.status_code == 200:
        response_json = response.json()
        response_data = response_json["data"][0]
        return response_data
    else:
        return "Failed to get upload status"


def check_upload_file_status(data):
    status = data["status"]
    # Simple status checking
    if status == 2:  # Complete
        return {"status": "complete"}
    elif status == 8:  # Partially Complete
        return {"status": "partially_complete"}
    elif status in [3, 4, 5, -1]:  # Canceled, Timed Out, Failed, Invalid
        return {"status": "failed"}
    elif status in [0, 1, 6, 7]:  # Ready, Running, Ingesting, Analyzing
        return {"status": "in_progress"}
    else:
        return {"status": "failed"}


def wait_for_upload_complete():
    upload_status_data = get_latest_upload_data()
    upload_status_check = check_upload_file_status(upload_status_data)

    while upload_status_check["status"] == "in_progress":
        print(upload_status_check)
        time.sleep(15)
        upload_status_data = get_latest_upload_data()
        upload_status_check = check_upload_file_status(upload_status_data)

    if upload_status_check["status"] == "complete":
        print(f"[+] Data import completed: {upload_status_check['status']}")
    elif upload_status_check["status"] == "partially_complete":
        print(f"[+] Data import partially completed: {upload_status_check['status']}")
    elif upload_status_check["status"] == "failed":
        print(f"[-] Data import failed: {upload_status_check['status']}")
