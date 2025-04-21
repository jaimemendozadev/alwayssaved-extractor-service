"""
MongoDB util functions file.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from services.aws.ssm import get_secret


def create_mongodb_instance() -> AsyncIOMotorDatabase:
    mongo_db_user = get_secret("/notecasts/MONGO_DB_USER")

    mongo_db_password = get_secret("/notecasts/MONGO_DB_PASSWORD")

    mongo_db_base_uri = get_secret("/notecasts/MONGO_DB_BASE_URI")

    mongo_db_name = get_secret("/notecasts/MONGO_DB_NAME")

    mongo_db_cluster_name = get_secret("/notecasts/MONGO_DB_CLUSTER_NAME")

    if (
        mongo_db_user is None
        or mongo_db_password is None
        or mongo_db_base_uri is None
        or mongo_db_cluster_name is None
        or mongo_db_name is None
    ):
        raise ValueError("MONGO_DB environment variables are not set.")

    connection_string = f"mongodb+srv://{mongo_db_user}:{mongo_db_password}@{mongo_db_base_uri}/{mongo_db_name}?retryWrites=true&w=majority&appName={mongo_db_cluster_name}"

    # Create a new client and connect to the server
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_string)

    # 04-20-25 TODO: Need to validate if DB data persistence works by
    # returning the client or do we have to re-specify the DB name?
    return client[mongo_db_name]
