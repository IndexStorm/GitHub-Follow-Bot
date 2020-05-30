import aiosqlite


async def add_to_db(user_id: int, username: str, locale: str):
    async with aiosqlite.connect("git-bot.db") as db:
        # in_send_pool=1, in_feature_pool=0
        await db.execute("INSERT INTO Users (telegram_id, git_name, in_send_pool, in_feature_pool, locale) VALUES (?, ?, ?, ?, ?)", [user_id, username, 1, 0, locale])
        await db.commit()


async def update_username(user_id: int, username: str):
    async with aiosqlite.connect("git-bot.db") as db:
        await db.execute("UPDATE Users SET git_name=? WHERE telegram_id=?", [username, user_id])
        await db.commit()


async def update_locale(user_id: int, locale: str):
    async with aiosqlite.connect("git-bot.db") as db:
        await db.execute("UPDATE Users SET locale=? WHERE telegram_id=?", [locale, user_id])
        await db.commit()


async def get_user_locale(user_id: int) -> str:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT locale FROM Users WHERE telegram_id=?", [user_id]) as cursor:
            res = await cursor.fetchone()
            if res:
                return res[0]
            else:
                return None


async def get_missed_days(user_id: int) -> str:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT missed_days FROM Users WHERE telegram_id=?", [user_id]) as cursor:
            res = await cursor.fetchone()
            if res:
                return res[0]
            else:
                return None


async def get_telegram_from_git(username: str) -> int:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT telegram_id FROM Users WHERE git_name=?", [username]) as cursor:
            res = await cursor.fetchone()
            if res:
                return res[0]
            else:
                return None


async def get_git_from_telegram(user_id: int) -> str:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT git_name FROM Users WHERE telegram_id=?", [user_id]) as cursor:
            res = await cursor.fetchone()
            if res:
                return res[0]
            else:
                return None


async def get_to_follow_list(user_id: int) -> list:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT to_follow_list FROM Users WHERE telegram_id=?", [user_id]) as cursor:
            res = await cursor.fetchone()
            if res and res[0] != '':
                return res[0].split(';')
            else:
                return []


if __name__ == "__main__":
    pass
