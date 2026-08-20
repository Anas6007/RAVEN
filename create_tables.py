import asyncio

from database.init import create_tables


async def create():

    await create_tables()

    print("✅ تم إنشاء قاعدة البيانات بنجاح")


if __name__ == "__main__":
    asyncio.run(create())
