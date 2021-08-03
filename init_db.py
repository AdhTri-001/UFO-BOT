import asyncpg
from asyncio import run
Queries= '''CREATE TABLE giveaways (
    winner_count smallint,
    message_id numeric(18,0) NOT NULL,
    "timestamp" integer,
    prize text,
    guild_id numeric(18,0),
    channel_id numeric(18,0)
);
CREATE TABLE guildsettings (
    guild_id numeric(18,0) UNIQUE NOT NULL,
    prefix text,
    modrole_id numeric(18,0),
    muterole_id numeric(18,0),
    logch numeric(18,0),
    greetch numeric(18,0),
    discmds text[],
    warns json,
    greetmsg text,
    ranks text[],
    logging text[],
    logs jsonb[],
    kickat integer DEFAULT 0,
    banat integer DEFAULT 0,
    startrole_id numeric(18,0),
    mutedmems numeric(18,0)[],
    blackch numeric(18,0)[],
    PRIMARY KEY (guild_id)
);
CREATE TABLE snipes (
    channel_id numeric(18,0) UNIQUE NOT NULL,
    "timestamp" integer NOT NULL,
    message_content text,
    user_id numeric(18,0),
    PRIMARY KEY (channel_id)
);
CREATE TABLE tempbans (
    user_id numeric(18,0),
    guild_id numeric(18,0),
    "timestamp" integer
);
CREATE TABLE timers (
    reminder_id serial PRIMARY KEY,
    channel_id numeric(18,0),
    reason text,
    "timestamp" integer
);'''
async def main():
    db: asyncpg.Connection= await asyncpg.connect('postgres://ufobot:yoyome9104@localhost:5432/ufobotdb')
    print(await db.fetch('SELECT datname FROM pg_database WHERE datistemplate = false;'))
    for query in Queries.split(';'):
        print(query)
        await db.execute(query)
    print(await db.fetch('SELECT table_schema,table_name FROM information_schema.tables'))
    await db.close()

if __name__ == '__main__':
    print(run(main()))