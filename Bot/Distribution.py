import aiosqlite
import random
import time
import asyncio
import Localize
import Database

from GitApi import validate_username, check_follows_direct


async def pool_task(row, db):
    import Bot
    telegram_id, git_name = row[0], row[1]
    to_follow_list = row[2].split(';')
    user_locale = await Database.get_user_locale(telegram_id)
    for to_follow in to_follow_list:
        if not await check_follows_direct(git_name, to_follow):
            if not await validate_username(to_follow):
                continue
            # get number of already missed days
            cursor = await db.execute("SELECT missed_days FROM Users WHERE telegram_id=?", [telegram_id])
            missed_days = await cursor.fetchone()
            missed_days = missed_days[0] + 1
            # increment those days
            await db.execute("UPDATE Users SET missed_days=? WHERE telegram_id=?", [missed_days, telegram_id])
            # he's a bad boy, don't add him to pools
            # also delete him from feature_pool
            await db.execute("UPDATE Users SET in_feature_pool=0 WHERE telegram_id=?", [telegram_id])
            try:
                # didn't follow in >3 days, don't send new messages
                if missed_days == 3:
                    await Bot.bot.send_message(
                        chat_id=telegram_id,
                        text=Localize.SkippedThree[user_locale]
                    )
                elif missed_days < 3:
                    await Bot.bot.send_message(chat_id=telegram_id, text=Localize.DidNotFollowed[user_locale])
                    str_to_send = ""
                    # make a list of people to follow
                    for i in range(len(to_follow_list)):
                        str_to_send += f"{i}. https://github.com/{to_follow_list[i]}\n"
                    await Bot.bot.send_message(chat_id=telegram_id, text=Localize.YourList[user_locale].format(str_to_send=str_to_send))
            except:
                pass
            return
    # he's a good boy, add him to pools
    await db.execute("UPDATE Users SET in_feature_pool=1,in_send_pool=1,missed_days=0 WHERE telegram_id=?", [telegram_id])
    try:
        await Bot.bot.send_message(chat_id=telegram_id, text=Localize.DidFollowed[user_locale])
    except:
        pass


async def creat_pools():
    async with aiosqlite.connect("git-bot.db") as db:
        # get all people who didn't follow their users yet and thus have in_send_pool == 0
        async with db.execute("SELECT telegram_id,git_name,to_follow_list FROM Users WHERE in_send_pool=0") as cursor:
            rows = await cursor.fetchall()
            await asyncio.gather(*[pool_task(row, db) for row in rows])
            await db.commit()


async def group_task(send_id: int, send_git: str, feature_pool: list):
    featured_group = []
    if len(feature_pool) == 0:
        return [(send_id, send_git), featured_group]

    ind = random.randrange(len(feature_pool))
    sz = len(feature_pool)
    # start iteration from random position and go at most len(feature_pool)
    # because later we will take already visited values
    for i in range(ind, sz + ind):
        # i % sz to remain inside of feature_pool
        feat_id, feat_git = feature_pool[i % sz][0], feature_pool[i % sz][1]
        # if already chosen
        if (feat_id, feat_git) in featured_group:
            continue
        # if the same as us
        if feat_id == send_id:
            continue
        # if already following
        if await check_follows_direct(send_git, feat_git):
            continue
        featured_group.append((feat_id, feat_git))
        # maxlen of group is currently 5
        if len(featured_group) == 5:
            break

    return [(send_id, send_git), featured_group]


async def create_groups() -> list:
    db = await aiosqlite.connect("git-bot.db")
    cursor = await db.execute("SELECT telegram_id,git_name FROM Users WHERE in_send_pool=1")
    # get all people to whom we will send messages
    send_pool = await cursor.fetchall()
    cursor = await db.execute("SELECT telegram_id,git_name FROM Users WHERE in_feature_pool=1")
    # get all people we will feature
    feature_pool = await cursor.fetchall()
    await db.close()
    tasks = []
    for j in range(len(send_pool)):
        send_id, send_git = send_pool[j][0], send_pool[j][1]
        # start choosing the group from random position
        tasks.append(group_task(send_id, send_git, feature_pool))

    groups = await asyncio.gather(*tasks)

    return groups


async def send_message_task(group, db):
    import Bot
    send_id, send_git, featured_group = group[0][0], group[0][1], group[1]
    to_follow_list = []
    for person in featured_group:
        feat_id, feat_git = person[0], person[1]
        to_follow_list.append(feat_git)

    # remove send_id from send_pool
    await db.execute("UPDATE Users SET in_send_pool=0 WHERE telegram_id=?", [send_id])

    # set to_follow_list
    await db.execute("UPDATE Users SET to_follow_list=? WHERE telegram_id=?", [';'.join(to_follow_list), send_id])
    # get his locale
    user_locale = await Database.get_user_locale(send_id)
    str_to_send = ""
    # make a list of people to follow
    for i in range(len(to_follow_list)):
        str_to_send += f"{i}. https://github.com/{to_follow_list[i]}\n"
    # send the list
    try:
        if str_to_send != "":
            await Bot.bot.send_message(chat_id=send_id, text=Localize.YourList[user_locale].format(str_to_send=str_to_send))
        else:
            await Bot.bot.send_message(chat_id=send_id, text=Localize.NoList[user_locale])
    except:
        pass


async def send_messages(groups: list):
    async with aiosqlite.connect("git-bot.db") as db:
        await asyncio.gather(*[send_message_task(group, db) for group in groups])
        await db.commit()


async def create_group_for_user(send_id: int, send_git: str) -> list:
    async with aiosqlite.connect("git-bot.db") as db:
        async with db.execute("SELECT telegram_id,git_name FROM Users WHERE in_feature_pool=1") as cursor:
            # get all people we will feature
            feature_pool = await cursor.fetchall()
            featured_group = await group_task(send_id, send_git, feature_pool)

        return [featured_group]


if __name__ == "__main__":
    pass
