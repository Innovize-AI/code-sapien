import asyncpg
import asyncio
import os

async def test_connection():
    try:
        conn = await asyncpg.connect(user= os.getenv("DB_USER"),
            password="shpIs1n6G9rGBrCj",
            host="db.vayskszslzgapdpkhych.supabase.co" ,
            port=5432 ,
            database="postgres",
            ssl="require"
        )
        print("Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_connection())
