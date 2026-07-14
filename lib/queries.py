import requests
import json
import lib.bh_utils as bh_utils
from time import sleep
from urllib.parse import quote

# queries from specterops load https://github.com/SpecterOps/BloodHoundQueryLibrary/releases/latest/download/Queries.json
# import queries that are not '"prebuilt": true,"'


def load_specterops_queries():
    url = "https://github.com/SpecterOps/BloodHoundQueryLibrary/releases/latest/download/Queries.json"
    response = requests.get(url)
    queries = response.json()
    filtered_queries = [query for query in queries if not query.get("prebuilt", False)]
    return filtered_queries


# load custom queries from file or url
def _load_json_from_file_or_url(file_or_url):
    try:
        if file_or_url.startswith("http"):
            response = requests.get(file_or_url, timeout=30)
            response.raise_for_status()
            payload = response.json()
        else:
            with open(file_or_url, "r") as file:
                payload = json.load(file)
        return payload
    except requests.RequestException as exc:
        raise ValueError(f"Failed to load JSON from {file_or_url}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read JSON from {file_or_url}: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"Failed to parse JSON from {file_or_url}: {exc}") from exc


def load_custom_queries(file_or_url):
    return _load_json_from_file_or_url(file_or_url)


def load_custom_icons(file_or_url):
    return _load_json_from_file_or_url(file_or_url)


def import_queries(queries):
    count = 0
    for query in queries:
        # print(query)
        # ("POST", "/api/v2/saved-queries", body)
        bh_utils.pass_request("POST", "/api/v2/saved-queries", query)
        print(f"[{count}] Imported query: {query.get('name')}")
        count += 1
        sleep(0.2)


def get_custom_node(kind_name):
    encoded_kind_name = quote(kind_name, safe="")
    return bh_utils.pass_request("GET", f"/api/v2/custom-nodes/{encoded_kind_name}")


def import_custom_icons(custom_icons):
    if not isinstance(custom_icons, dict):
        print("Custom icon import expects a JSON object with a 'custom_types' mapping")
        return False

    custom_types = custom_icons.get("custom_types")
    if not isinstance(custom_types, dict) or len(custom_types) == 0:
        print("Custom icon import expects a JSON object with a non-empty 'custom_types' mapping")
        return False

    validation_errors = []
    for kind_name, kind_config in custom_types.items():
        if not isinstance(kind_config, dict):
            validation_errors.append(f" - {kind_name}: config must be a JSON object")
            continue

        icon_config = kind_config.get("icon")
        if not isinstance(icon_config, dict):
            validation_errors.append(f" - {kind_name}: missing 'icon' object")
            continue

        for field_name in ("type", "name"):
            field_value = icon_config.get(field_name)
            if not isinstance(field_value, str) or len(field_value.strip()) == 0:
                validation_errors.append(f" - {kind_name}: icon.{field_name} must be a non-empty string")

        if "color" in icon_config:
            color_value = icon_config.get("color")
            if not isinstance(color_value, str) or len(color_value.strip()) == 0:
                validation_errors.append(f" - {kind_name}: icon.color must be a non-empty string when provided")

    if validation_errors:
        print("Custom icon import payload is invalid:")
        for validation_error in validation_errors:
            print(validation_error)
        return False

    duplicate_kinds = []
    failed_checks = []

    for kind_name in custom_types:
        response = get_custom_node(kind_name)
        if response.status_code == 200:
            duplicate_kinds.append(kind_name)
        elif response.status_code != 404:
            failed_checks.append((kind_name, response.status_code, response.text))

    if failed_checks:
        print("Failed to validate custom icon import before creating new node kinds:")
        for kind_name, status_code, response_text in failed_checks:
            print(f" - {kind_name}: HTTP {status_code}")
            if response_text:
                print(response_text)
        return False

    if duplicate_kinds:
        print("Import aborted. These custom node kinds already exist:")
        for kind_name in duplicate_kinds:
            print(f" - {kind_name}")
        return False

    response = bh_utils.pass_request("POST", "/api/v2/custom-nodes", custom_icons)
    if response.status_code == 200 or response.status_code == 201:
        print(f"Imported custom icons for {len(custom_types)} custom node kinds")
        return True

    print(f"Failed to import custom icons (HTTP {response.status_code})")
    print(response.text)
    return False


def delete_all_saved_queries():
    count = 0
    for query in get_saved_queries():
        bh_utils.pass_request("DELETE", f"/api/v2/saved-queries/{query.get('id')}")
        print(f"[{count}] Deleted query: {query.get('name')}")
        count += 1
        sleep(0.2)


# get all saved queries
def get_saved_queries():
    return bh_utils.pass_request("GET", "/api/v2/saved-queries").json()["data"]


# set to Public by default
def set_query_scope(query_id, public=True, users=None):
    if users is None:
        users = []
    payload = {"public": public, "user_ids": users}
    request_response = bh_utils.pass_request("PUT", f"/api/v2/saved-queries/{query_id}/permissions", payload)
    # print(request_response.text)
    if (
        request_response.status_code == 200
        or request_response.status_code == 201
        or request_response.status_code == 204
    ):
        print(f"Query {query_id} scope set to {public} for users {users}")
    else:
        print(f"Failed to set query {query_id} scope to {public} for users {users}")


# set to Public by default
def set_queries_permissions(public=True, users=None):
    queries_list = get_saved_queries()
    # iterate over all saved queries
    for query in queries_list:
        query_id = query.get("id")
        # query_name = query.get("name")
        # query_scope = query.get("scope")
        # print(f"[{query_id}] Query: {query_name}, Scope: {query_scope}")
        if users is not None:
            set_query_scope(query_id, public, users)
        else:
            set_query_scope(query_id, public)
        sleep(0.2)


def convert_legacy_queries(queries):
    converted_queries = []

    for query in queries:
        # Skip queries with separator lines in name
        if "--------------" in query.get("name", ""):
            continue

        # Extract query from queryList if it exists (Azure format)
        if "queryList" in query and query["queryList"]:
            query_text = query["queryList"][0].get("query", "")
        else:
            query_text = query.get("query", "")

        # Skip if no query text
        if not query_text:
            continue

        # Create the converted query in BloodHound format
        converted_query = {
            "name": f"{query.get('category', 'Unknown')} - {query.get('name', 'Unnamed Query')}",
            "query": query_text,
        }

        converted_queries.append(converted_query)

    return converted_queries
