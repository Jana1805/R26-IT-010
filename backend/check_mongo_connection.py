import asyncio

from app.database.connection import close_mongo_connection, connect_to_mongo


async def main():
    database = await connect_to_mongo()
    print(f"MongoDB ping successful. Database: {database.name}")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
