import lib.utils as utils
import lib.queries as queries
import lib.bh_utils as bh_utils
import argparse
import lib.banner as banner
import lib.config as config
import sys
import os
import auth_flow
import time

# bloodhound toolkit cli
docker_compose_dir = config.load_env_variables()["docker_compose_dir"]
neo4j_data_dir = f"{docker_compose_dir}/data/neo4j-data"

# argparse
parser = argparse.ArgumentParser(description="Bloodhound Toolkit CLI")
parser.add_argument("--start-containers", "-start", action="store_true", help="Start docker compose containers")
parser.add_argument("--stop-containers", "-stop", action="store_true", help="Stop docker compose containers")
parser.add_argument("--restart-containers", "-rc", action="store_true", help="Restart docker compose containers")
parser.add_argument("--docker-logs", "-dl", action="store_true", help="Show docker logs")
parser.add_argument(
    "--initial-config",
    "-init",
    action="store_true",
    help="Initial configuration. Will retrieve initial password, change password, create api key and update .env",
)
parser.add_argument(
    "--change-password",
    "-cp",
    action="store_true",
    help="Change password. Set the BHE_NEW_PASSWORD in .env. To be used after initial configuration",
)
parser.add_argument("--list-databases", "-ldb", action="store_true", help="List databases")
parser.add_argument("--current-db", "-db", action="store_true", help="Currently used database")
parser.add_argument("--set-database", "-sdb", help="Change / set database to use")
parser.add_argument("--clear-database", "-cdb", action="store_true", help="Clear database")
parser.add_argument(
    "--import-specterops-queries", "-isq", action="store_true", help="Import SpecterOps queries from github"
)
parser.add_argument("--import-custom-queries", "-icq", help="Import custom queries from file or url")
parser.add_argument("--old", action="store_true", help="Convert legacy query format before importing (use with -icq)")
parser.add_argument("--delete-all-queries", "-dq", action="store_true", help="Delete all custom queries")
parser.add_argument("--retrieve-initial-password", "-rip", action="store_true", help="Retrieve initial password")
parser.add_argument("--create-api-key", "-cak", action="store_true", help="Create API key")
parser.add_argument(
    "--update-api-key", "-uak", action="store_true", help="Update .env with API key (to be used with --create-api-key)"
)
parser.add_argument("--verify-access", "-va", action="store_true", help="Verify access to BloodHound")
parser.add_argument("--upload-collection", "-uc", help="Specify a folder containing json data or a zip file")
parser.add_argument("--run-analysis", "-ra", action="store_true", help="Run analysis on data")
parser.add_argument("--no-banner", "-nb", action="store_true", help="Don't show banner")
args = parser.parse_args()

# if no arguments, print help
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

# if no banner, don't show banner
if args.no_banner:
    banner.generate_banner = lambda: None
else:
    banner.generate_banner()

# start the containers
if args.start_containers:
    utils.start_containers()

# stop the containers
if args.stop_containers:
    utils.stop_containers()

# restart the containers
if args.restart_containers:
    utils.restart_containers()

# show docker logs
if args.docker_logs:
    utils.show_docker_logs()

# verify access to BloodHound
if args.verify_access:
    if bh_utils.verify_access():
        print("Access to BloodHound verified")
    else:
        print("Access to BloodHound failed")

# list the databases
if args.list_databases:
    neo4j_databases = utils.list_neo4j_databases(neo4j_data_dir)
    print(neo4j_databases)


# get the current database
if args.current_db:
    current_db = utils.get_current_db()
    print(f"Currently used database: {current_db}")


# set the current database
if args.set_database:
    NEED_RESTART = False
    # check if bloodhound is up
    if utils.check_is_up():
        NEED_RESTART = True
        print("BH is running, stopping it...")
        utils.stop_containers()

    new_db = args.set_database
    current_db = utils.get_current_db()
    if current_db == new_db:
        print(f"Database already set to: {new_db}")
    else:
        utils.set_current_db(new_db)

    # if we need to restart, start the containers
    if NEED_RESTART:
        print("Starting containers...")
        utils.start_containers()
        # wait for 10 seconds
        time.sleep(10)

        # clear the inject / upload history
        if bh_utils.verify_access():
            utils.clear_inject_history()
    print(f"Database set to: {new_db}")

# retrieve initial password
if args.retrieve_initial_password:
    initial_password = utils.retrieve_initial_password()
    print(f"Initial password: {initial_password}")

# change password
if args.change_password:
    new_password = utils.change_password_api()
    if new_password != "Failed to change password":
        config.update_env_variables("BHE_PASSWORD", new_password)
        config.update_env_variables("BHE_NEW_PASSWORD", "none")
        config.update_env_variables("MUST_CHANGE_PASSWORD", "no")
        print(f"Password changed to: {new_password}")
    else:
        print("Failed to change password")

# create api key
if args.create_api_key:
    api_key = utils.create_api_key()
    data = {
        "id": api_key["id"],
        "key": api_key["key"],
        "name": api_key["name"],
    }
    print(f"API key created:\n{data}")

    # update .env with API key
    if args.update_api_key:
        utils.update_env_api_key(api_key)
        print("API key updated in .env")

# initial configuration
if args.initial_config:
    # run the auth flow
    auth_flow.authenticate()
    print("Initial configuration complete")

# import specterops queries
if args.import_specterops_queries:
    specterops_queries = queries.load_specterops_queries()
    queries.import_queries(specterops_queries)
    print("SpecterOps queries imported")

# import custom queries
if args.import_custom_queries:
    custom_queries = queries.load_custom_queries(args.import_custom_queries)

    # Convert legacy format if --old flag is present
    if args.old:
        # Handle Azure queries structure (object with 'queries' key)
        if isinstance(custom_queries, dict) and "queries" in custom_queries:
            queries_list = custom_queries["queries"]
        else:
            queries_list = custom_queries

        custom_queries = queries.convert_legacy_queries(queries_list)
        print("Legacy queries converted")

    queries.import_queries(custom_queries)
    print("Custom queries imported")

# delete all custom queries
if args.delete_all_queries:
    queries.delete_all_saved_queries()
    print("All custom queries deleted")

# upload collection
if args.upload_collection:
    new_upload = utils.initialize_upload()
    upload_status = utils.get_latest_upload_data()
    upload_id = upload_status["id"]
    utils.upload_file_process(upload_id, args.upload_collection)
    utils.wait_for_upload_complete()

# run analysis
if args.run_analysis:
    utils.run_analysis()
    print("Analysis Lauched")
