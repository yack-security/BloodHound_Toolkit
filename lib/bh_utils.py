import datetime
import hashlib
import hmac
import base64
import requests
from typing import Optional
import lib.config as config
import lib.utils as utils
import json
import sys

do_proxy = False
proxy_url = "http://127.0.0.1:8181"

# https://bloodhound.specterops.io/integrations/bloodhound-api/working-with-api

# load env variables
env = config.load_env_variables()


class Credentials(object):
    def __init__(self, token_id: str, token_key: str) -> None:
        self.token_id = token_id
        self.token_key = token_key


def _request(method: str, path: str, full_url: str = None, body: Optional[bytes] = None) -> requests.Response:
    # check if bloodhound is up
    if utils.check_is_up() is False:
        print("BH is not running, you need to start it first!")
        sys.exit(1)

    # Reload env variables to get the latest token values
    current_env = config.load_env_variables()
    credentials = Credentials(current_env["token_id"], current_env["token_key"])
    # Digester is initialized with HMAC-SHA-256 using the token key as the HMAC digest key.
    digester = hmac.new(credentials.token_key.encode(), None, hashlib.sha256)

    # OperationKey is the first HMAC digest link in the signature chain. This prevents replay attacks that seek to
    # modify the request method or URI. It is composed of concatenating the request method and the request URI with
    # no delimiter and computing the HMAC digest using the token key as the digest secret.
    #
    # Example: GET /api/v2/test/resource HTTP/1.1
    # Signature Component: GET/api/v2/test/resource
    digester.update(f"{method}{path}".encode())

    # Update the digester for further chaining
    digester = hmac.new(digester.digest(), None, hashlib.sha256)

    # DateKey is the next HMAC digest link in the signature chain. This encodes the RFC3339 formatted datetime
    # value as part of the signature to the hour to prevent replay attacks that are older than max two hours. This
    # value is added to the signature chain by cutting off all values from the RFC3339 formatted datetime from the
    # hours value forward:
    #
    # Example: 2020-12-01T23:59:60Z
    # Signature Component: 2020-12-01T23
    datetime_formatted = datetime.datetime.now().astimezone().isoformat("T")
    digester.update(datetime_formatted[:13].encode())

    # Update the digester for further chaining
    digester = hmac.new(digester.digest(), None, hashlib.sha256)

    # Body signing is the last HMAC digest link in the signature chain. This encodes the request body as part of
    # the signature to prevent replay attacks that seek to modify the payload of a signed request. In the case
    # where there is no body content the HMAC digest is computed anyway, simply with no values written to the
    # digester.
    if body is not None:
        digester.update(body)

    if do_proxy:
        response = requests.request(
            method=method,
            url=full_url or path,
            headers={
                "User-Agent": "bhe-python-sdk 0001",
                "Authorization": f"bhesignature {credentials.token_id}",
                "RequestDate": datetime_formatted,
                "Signature": base64.b64encode(digester.digest()),
                "Content-Type": "application/json",
            },
            data=body,
            proxies={"http": proxy_url, "https": proxy_url},
        )
    else:
        response = requests.request(
            method=method,
            url=full_url or path,
            headers={
                "User-Agent": "bhe-python-sdk 0001",
                "Authorization": f"bhesignature {credentials.token_id}",
                "RequestDate": datetime_formatted,
                "Signature": base64.b64encode(digester.digest()),
                "Content-Type": "application/json",
            },
            data=body,
        )
    return response


def pass_request(method, endpoint, body=None):
    current_env = config.load_env_variables()
    full_url = current_env["build_url"] + endpoint
    path = endpoint

    # Convert body to bytes if it's a dict/object
    if body is not None and not isinstance(body, bytes):
        body = json.dumps(body).encode("utf-8")

    response = _request(method, path, full_url, body)
    return response


def verify_access():
    current_env = config.load_env_variables()
    full_url = current_env["build_url"] + "/api/v2/self"
    path = "/api/v2/self"
    # print(full_url)
    response = _request("GET", path, full_url)
    # response_json = response.json()
    if response.status_code == 200:
        return True
    else:
        return False
