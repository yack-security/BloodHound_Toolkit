#!/usr/bin/env python3

import os
import sys
from lib.config import load_env_variables, update_env_variables
from lib.bh_utils import verify_access
from lib.utils import (
    login_get_token,
    create_initial_api_key,
    update_env_api_key,
    change_password,
    generate_password,
    retrieve_initial_password,
)

rate_limit_sleep = 0.2


def debug_print(message):
    if os.getenv("DEBUG", "").lower() == "true":
        print(message)


# 1. Check if we have token_id and token_key
#    1.1. If yes, validate them with API
#        1.1.1. If valid → Continue with tokens
#        1.1.2. If invalid → Go to step 2
#    1.2. If no tokens → Go to step 2

# 2. Check if we have username and password
#    2.1. If yes, attempt login
#        2.1.1. If successful → Generate new tokens → Save to env → Continue
#        2.1.2. If failed (bad credentials) → try to get the initial password from docker logs
#            2.1.2.1. if we get the initial password → login with it → change to configured password → continue flow
#            2.1.2.2. if we don't get the initial password → exit with error (no valid auth method)
#        2.1.3. If failed (password change required) → change password and login → generate new tokens → save to env → continue
#    2.2. If no credentials → Exit with error (no valid auth method)

# 3. verify if we have a valid token


def authenticate():
    debug_print("Starting authentication...")

    env_vars = load_env_variables()

    # Try existing tokens first
    if env_vars.get("token_id") and env_vars.get("token_key"):
        if verify_access():
            debug_print("Existing tokens work fine")
            sleep(rate_limit_sleep)
            return True
        debug_print("Tokens expired, need to re-authenticate")

    # Get credentials
    username = os.getenv("BHE_USERNAME")
    password = os.getenv("BHE_PASSWORD")

    if password == "none":
        password = generate_password()
        update_env_variables("BHE_PASSWORD", password)

    if not username or not password:
        debug_print("Missing username or password")
        return False

    # Try login
    result = login_get_token("POST", "/api/v2/login", username, password)
    sleep(rate_limit_sleep)

    if not result or not result[0]:
        # Login failed, try with initial password from docker
        debug_print("Login failed, checking docker logs for initial password...")
        initial_password = retrieve_initial_password()

        if not initial_password or initial_password == "No password found":
            debug_print("No initial password found")
            return False

        update_env_variables("BHE_INITIAL_PASSWORD", initial_password)
        result = login_get_token("POST", "/api/v2/login", username, initial_password)
        sleep(rate_limit_sleep)

        if not result or not result[0]:
            debug_print("Initial password also failed")
            return False

        user_id, session_token, must_change_password = result

        # Change from initial to configured password
        response = change_password(
            "PUT", f"/api/v2/bloodhound-users/{user_id}/secret", session_token, initial_password, password
        )
        sleep(rate_limit_sleep)

        if response.status_code != 200:
            debug_print("Failed to change password")
            return False

        update_env_variables("BHE_PASSWORD", password)
        result = login_get_token("POST", "/api/v2/login", username, password)
        sleep(rate_limit_sleep)
        if not result or not result[0]:
            return False

    user_id, session_token, must_change_password = result

    # Handle forced password change
    if must_change_password:
        new_password = os.getenv("BHE_NEW_PASSWORD")

        if new_password == "none" or new_password == password:
            new_password = generate_password()
            update_env_variables("BHE_NEW_PASSWORD", new_password)

        response = change_password(
            "PUT", f"/api/v2/bloodhound-users/{user_id}/secret", session_token, password, new_password
        )
        sleep(rate_limit_sleep)
        if response.status_code != 200:
            debug_print("Password change failed")
            return False

        update_env_variables("BHE_PASSWORD", new_password)
        update_env_variables("BHE_NEW_PASSWORD", "none")

        result = login_get_token("POST", "/api/v2/login", username, new_password)
        sleep(rate_limit_sleep)
        if not result or not result[0]:
            return False

        user_id, session_token, _ = result

    # Create API tokens
    api_response = create_initial_api_key(session_token, user_id, "BHTK Token")

    if "data" not in api_response:
        debug_print("Failed to create API tokens")
        return False

    token_id, token_key, _ = update_env_api_key(api_response)
    debug_print(f"Created new tokens (ID: {token_id[:8]}...)")

    # Verify tokens work
    if verify_access():
        debug_print("Authentication successful")
        return True
    else:
        debug_print("New tokens don't work")
        return False
