from app.config import get_settings

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import PyMongoError
except ImportError:
    AsyncIOMotorClient = None
    PyMongoError = Exception

settings = get_settings()
MONGO_URL = settings.mongo_url
DATABASE_NAME = settings.database_name

client = None
database = None

async def connect_to_mongo():
    global client, database
    if AsyncIOMotorClient is None:
        raise RuntimeError("MongoDB driver is not installed. Run: python -m pip install -r requirements.txt")

    try:
        client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=settings.db_server_selection_timeout_ms,
        )
        database = client[DATABASE_NAME]
        await client.admin.command('ping')
        print(f"Connected to MongoDB database: {DATABASE_NAME}")
        return database
    except PyMongoError as exc:
        client = None
        database = None
        raise RuntimeError(f"Failed to connect to MongoDB: {exc}") from exc

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")

def get_database():
    if database is None:
        raise RuntimeError("MongoDB is not connected")
    return database
