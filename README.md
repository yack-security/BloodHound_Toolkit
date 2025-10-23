# BloodHound Toolkit

## Description

Toolkit for interacting with BloodHound API.

This is early stage, use it at your own risk.

## Requirements

You only need the requirements below ( you don't need to have BloodHound running). All the necessary steps are automated.

- git
- Python 3.10+
- Docker
- Docker Compose

## Setup

```bash
# clone the repository
git clone https://github.com/yack-security/BloodHound_Toolkit.git
cd BloodHound_Toolkit
# install dependencies
pip3 install -r requirements.txt
# copy env.example and bloodhound.config.json.example
# modify if you need to
cp env.example .env
cp bloodhound.config.json.example bloodhound.config.json

# you can also edit docker-compose.yml if you need to

# starting for the first time
python3 bhtk.py -start
python3 bhtk.py -init
```

## Usage

### CLI

```bash
python3 bhtk.py -h
```

```txt
usage: bhtk.py [-h] [--start-containers] [--stop-containers] [--restart-containers] [--docker-logs] [--initial-config] [--change-password] [--list-databases] [--current-db]
               [--set-database SET_DATABASE] [--clear-database] [--import-specterops-queries] [--import-custom-queries IMPORT_CUSTOM_QUERIES] [--old] [--delete-all-queries]
               [--retrieve-initial-password] [--create-api-key] [--update-api-key] [--verify-access] [--upload-collection UPLOAD_COLLECTION] [--run-analysis] [--no-banner] [--set-queries-public]

Bloodhound Toolkit CLI

options:
  -h, --help            show this help message and exit
  --start-containers, -start
                        Start docker compose containers
  --stop-containers, -stop
                        Stop docker compose containers
  --restart-containers, -rc
                        Restart docker compose containers
  --docker-logs, -dl    Show docker logs
  --initial-config, -init
                        Initial configuration. Will retrieve initial password, change password, create api key and update .env
  --change-password, -cp
                        Change password. Set the BHE_NEW_PASSWORD in .env. To be used after initial configuration
  --list-databases, -ldb
                        List databases
  --current-db, -db     Currently used database
  --set-database SET_DATABASE, -sdb SET_DATABASE
                        Change / set database to use
  --clear-database, -cdb
                        Clear database
  --import-specterops-queries, -isq
                        Import SpecterOps queries from github
  --import-custom-queries IMPORT_CUSTOM_QUERIES, -icq IMPORT_CUSTOM_QUERIES
                        Import custom queries from file or url
  --old                 Convert legacy query format before importing (use with -icq)
  --delete-all-queries, -dq
                        Delete all custom queries
  --retrieve-initial-password, -rip
                        Retrieve initial password
  --create-api-key, -cak
                        Create API key
  --update-api-key, -uak
                        Update .env with API key (to be used with --create-api-key)
  --verify-access, -va  Verify access to BloodHound
  --upload-collection UPLOAD_COLLECTION, -uc UPLOAD_COLLECTION
                        Specify a folder containing json data or a zip file
  --run-analysis, -ra   Run analysis on data
  --no-banner, -nb      Don't show banner
  --set-queries-public, -sqp
                        Set queries permissions to public
```

#### Examples

Upload collection. Both folder and zip file are supported.

```bash
python3 bhtk.py -uc ../folder/with/collector/output/data
python3 bhtk.py -uc ../folder/with/collector/output/data.zip
```

Clear all data in BloodHound

```bash
python3 bhtk.py -cdb
```

Importing custom queries

```bash
# Import SpecterOps [queries](https://queries.specterops.io/)
python3 bhtk.py -isq
# Import custom queries from file or url
python3 bhtk.py -icq data/queries/custom.json
python3 bhtk.py -icq https://raw.githubusercontent.com/yack-security/BloodHound_Toolkit/main/data/queries/custom.json

# try --old flag if you are importing legacy queries

# Delete all custom queries
python3 bhtk.py -dq
```

### Python lib

```python
from lib.config import load_env_variables, update_env_variables
import lib.bh_utils as bh_utils
import lib.queries as queries
import auth_flow as auth_flow

# initial config
auth_flow.authenticate()
print("Initial configuration complete")
```

## Todo

- [ ] Add proxy as arg instead of hardcoded

## Credits
