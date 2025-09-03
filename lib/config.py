import os
import dotenv

dotenv.load_dotenv()

# load env variables
# setup base url


# load env variables
def load_env_variables():
    return {
        "base_url": os.getenv("BHE_DOMAIN"),
        "base_port": os.getenv("BHE_PORT"),
        "base_scheme": os.getenv("BHE_SCHEME"),
        "build_url": f"{os.getenv('BHE_SCHEME')}://{os.getenv('BHE_DOMAIN')}:{os.getenv('BHE_PORT')}",
        "token_id": os.getenv("BHE_TOKEN_ID"),
        "token_key": os.getenv("BHE_TOKEN_KEY"),
        "username": os.getenv("BHE_USERNAME"),
        "must_change_password": os.getenv("MUST_CHANGE_PASSWORD"),
        "initial_password": os.getenv("BHE_INITIAL_PASSWORD"),
        "password": os.getenv("BHE_PASSWORD"),
        "new_password": os.getenv("BHE_NEW_PASSWORD"),
        "debug": os.getenv("DEBUG"),
        "neo4j_database_name": os.getenv("NEO4J_DATABASE_NAME"),
        "neo4j_data_dir": os.getenv("NEO4J_DATA_DIR"),
        "docker_compose_dir": os.getenv("DOCKER_COMPOSE_DIR"),
    }


def base_url():
    env = load_env_variables()
    return env["build_url"]


def update_env_variables(key: str, value: str):
    """
    Update environment variable in both os.environ and .env file
    """
    os.environ[key] = value

    # Read the current .env file
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        with open(env_file_path, "r") as file:
            lines = file.readlines()

        # Update or add the key-value pair
        key_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break

        if not key_found:
            lines.append(f"{key}={value}\n")

        # Write back to .env file
        with open(env_file_path, "w") as file:
            file.writelines(lines)
    else:
        # Create new .env file if it doesn't exist
        with open(env_file_path, "w") as file:
            file.write(f"{key}={value}\n")
