import requests
import json
import lib.bh_utils as bh_utils

# queries from specterops load https://raw.githubusercontent.com/SpecterOps/BloodHoundQueryLibrary/refs/heads/main/Queries.json
# import queries that are not '"prebuilt": true,"'


def load_specterops_queries():
    url = "https://raw.githubusercontent.com/SpecterOps/BloodHoundQueryLibrary/refs/heads/main/Queries.json"
    response = requests.get(url)
    queries = response.json()
    filtered_queries = [query for query in queries if not query.get("prebuilt", False)]
    return filtered_queries


# load custom queries from file or url
def load_custom_queries(file_or_url):
    if file_or_url.startswith("http"):
        response = requests.get(file_or_url)
        queries = response.json()
    else:
        with open(file_or_url, "r") as file:
            queries = json.load(file)
    return queries


def import_queries(queries):
    count = 0
    for query in queries:
        # print(query)
        # ("POST", "/api/v2/saved-queries", body)
        bh_utils.pass_request("POST", "/api/v2/saved-queries", query)
        print(f"[{count}] Imported query: {query.get('name')}")
        count += 1


def delete_all_saved_queries():
    count = 0
    for query in get_saved_queries():
        bh_utils.pass_request("DELETE", f"/api/v2/saved-queries/{query.get('id')}")
        print(f"[{count}] Deleted query: {query.get('name')}")
        count += 1


def get_saved_queries():
    return bh_utils.pass_request("GET", "/api/v2/saved-queries").json()["data"]


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
