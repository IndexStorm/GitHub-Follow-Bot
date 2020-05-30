import random
import aiohttp


def get_gh_token() -> str:
    # https://github.com/settings/tokens
    # repo -> public_repo
    tokens = ['GITHUB_TOKEN',
              'GITHUB_TOKEN']
    return random.choice(tokens)


def get_headers() -> dict:
    return {
        'User-Agent': "GitHub's-best-Friend!",
        'Authorization': f'token {get_gh_token()}'
    }


async def validate_username(user: str) -> bool:
    u = f'https://api.github.com/users/{user}'
    connector = aiohttp.TCPConnector(limit=1000)  # check limits
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(u, headers=get_headers()) as resp:
            await resp.text()
            await session.close()
            return resp.status == 200


async def check_follows_direct(user: str, by_user: str) -> bool:
    u = f'https://api.github.com/users/{user}/following/{by_user}'
    connector = aiohttp.TCPConnector(limit=1000)  # check limits
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(u, headers=get_headers()) as resp:
            await resp.text()
            await session.close()
            return resp.status == 204

if __name__ == "__main__":
    pass
