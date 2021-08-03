from datetime import datetime
import re
from time import time
import discord
import sys, traceback
from os import listdir
import asyncpg
from json import dump, load
from discord.ext import commands
from asyncio import sleep, wait, FIRST_COMPLETED

# help command, noice!
class Help(commands.MinimalHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.command_attrs= {'name': 'help', 'aliases': ['commands'], 'help': 'Provides help to the command or Category(First letter capital)'}

    def get_command_help(self, command):
        cmd_help= '```'
        cmd_help+= self.get_command_signature(command) + '```'
        cmd_help+= f'{command.help}' if command.help else '\`\`No help given``'
        cmd_help+= f'\n{command.description}' if command.description else ''
        return cmd_help

    async def command_callback(self, ctx, *, command= None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cog = bot.get_cog(command.capitalize())
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine
        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    async def filter_commands(self, commands: list, disabled_commands):
        if disabled_commands:
            def command_check(command):
                return not (command.hidden or command.name in disabled_commands)
            commands= list(filter(command_check, commands))
        else:
            commands= [command for command in commands if not command.hidden]
        def commandname(command):
            return command.name
        commands.sort(key = commandname)
        return commands

    # @UFO bot help
    async def send_bot_help(self, mapping):
        prefix= await MyUFO.get_prefix(self.context.message)
        embed= discord.Embed(
            title= 'UFO Bot help!',
            color= discord.Color.blurple() if self.context.me.color == discord.Color.default() else self.context.me.color,
            description= ' '.join("Use {0}help <command_name> to get help for that command.|\
                Use {0}help <Category_name> to get help for that command.(Case Sensitive)|\
                **DO NOT USE MORE THAN 9 commands within 20 seconds if you don't wanna get bot banned.**".split(' ')).replace('|','\n').format(prefix[0])
        )
        disabled_commands= MyUFO.cache.get(self.context.guild.id, {"discmds":[]}).get("discmds")
        modules_list= '➤ '+ '\n➤ '.join(['`{:<25} {}`'.format(cog.qualified_name, len(cog.get_commands())) for cog in mapping.keys() if cog and cog.get_commands()])
        pags= [dict(name= 'Module  \u200b  \u200b  \u200b  \u200b  \u200b  \u200b  \u200b  \u200bCommand count', value= modules_list)]
        for key in mapping.keys():
            commands= await self.filter_commands(mapping[key], disabled_commands)
            mapping[key]= commands
            if key and mapping[key]:
                pags.append({'name': key.qualified_name, 'value': '`'+'`  `'.join([command.name for command in commands])+'`'})
        embed.add_field(**pags[0])
        pag_now= 0
        page_no= range(1, len(pags)+1)
        def check(r, u):
            return str(r.emoji) in ['◀', '⏹', '▶'] and u.id== self.context.author.id and r.message.id == msg.id
        def check2(rrr: discord.RawReactionActionEvent):
            return str(rrr.emoji) in ['◀', '▶'] and rrr.user_id == self.context.author.id and rrr.message_id == msg.id
        embed.set_footer(text= f'Page 1/{len(pags)}')
        msg: discord.Message= await self.context.send(embed= embed)
        await msg.add_reaction('◀')
        await msg.add_reaction('⏹')
        await msg.add_reaction('▶')
        for i in range(0, 25):
            done, pending = await wait([self.context.bot.wait_for('raw_reaction_remove', timeout= 45, check= check2),
                self.context.bot.wait_for('reaction_add', timeout= 45, check= check)
                ], return_when= FIRST_COMPLETED)
            try:
                res = done.pop().result()
                if isinstance(res, discord.RawReactionActionEvent):
                    emo= str(res.emoji)
                else:
                    emo= str(res[0].emoji)
                if emo == '◀':
                    pag_now-=1
                    if abs(pag_now) == len(pags): pag_now= 0
                elif emo == '⏹':
                    raise Exception
                else:
                    pag_now+=1
                    if abs(pag_now) == len(pags): pag_now= 0
            except:
                try: await msg.clear_reactions()
                except: pass
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()
                break
            for future in done:
                future.exception()
            for future in pending:
                future.cancel()
            embed.clear_fields()
            embed.add_field(**pags[pag_now])
            embed.set_footer(text= f'Page {page_no[pag_now]}/{len(pags)}')
            await msg.edit(embed= embed)
        await msg.edit(content= '**Pagination Ended**')

    # @UFO bot help <command>
    async def send_command_help(self, command):
        if command.hidden:
            return await self.send_error_message(f'No command called "{command}" found.')
        category= command.cog_name
        embed= discord.Embed(
            title= str(command),
            color= self.context.me.color,
            description= self.get_command_help(command),
            timestamp= datetime.utcnow()
        )
        embed.set_author(name= str(self.context.author), icon_url= self.context.author.avatar_url)
        embed.add_field(name= "Aliases", value= ", ".join(command.aliases)) if command.aliases else None
        embed.add_field(name= "Category", value= category if category else "No Category.")
        await self.context.send(embed= embed)

    # @UFO bot help <group>
    async def send_group_help(self, group):
        category= group.cog_name
        embed= discord.Embed(
            title= str(group),
            color= self.context.me.color,
            description= self.get_command_help(group),
            timestamp= datetime.utcnow()
        )
        embed.set_author(name= str(self.context.author), icon_url= self.context.author.avatar_url)
        embed.add_field(name= "Aliases", value= ", ".join(group.aliases)) if group.aliases else None
        subhelp = []
        for command in group.commands:
            signature= self.get_command_signature(command)
            signature= signature.replace(command.name, '|'.join([command.name]+command.aliases))
            cmddata= signature.split(command.name, 1)
            cmddata[1]= re.sub(r'=.{2,}\]', ']', cmddata[1])
            signature= command.name.join(cmddata)
            subhelp.append(f"`{signature}` - {command.help or 'No help given'}")
        embed.add_field(name= "Subcommands", value= "\n".join(subhelp), inline= False)
        embed.add_field(name= "Category", value= category if category else "No Category.")
        await self.context.send(embed= embed)

    # @UFO bot help <cog>
    async def send_cog_help(self, cog):
        entries= []
        disabled_commands= await self.context.bot.db.fetchval(f'SELECT discmds FROM guildsettings WHERE guild_id= {self.context.guild.id}')
        commands= await self.filter_commands(cog.get_commands(), disabled_commands)
        for command in commands:
            signature= self.get_command_signature(command)
            cmddata= signature.split(command.name, 1)
            cmddata[1]= re.sub(r'=.{2,}\]', ']', cmddata[1])
            signature= command.name.join(cmddata)
            entries.append(f'`{signature}`')
        embed= discord.Embed(title= cog.qualified_name, description= '\n'.join(entries), color= self.context.me.color, timestamp= datetime.utcnow())
        embed.set_author(name= str(self.context.author), icon_url= self.context.author.avatar_url)
        await self.context.send(embed= embed)

    # Errors
    async def send_error_message(self, error):
        embed= discord.Embed(description= f":x: {error}")
        embed.set_author(name= str(self.context.author), icon_url= self.context.author.avatar_url)
        await self.context.send(embed= embed)

# My bot class more noice.
class Ufo_bot(commands.Bot):

    def __init__(self, command_prefix, help_command, description, **options):
        self.commandusers= {}
        self.mutemem= []
        self.errorcount= 0
        self.db= None
        self.cache= {"guild_id":{"prefix":'.', "discmds": []}}
        self.inited= False
        self.commandused= 0
        self._help_command= None
        self.dsn= 'postgres://ufobot:yoyome9104@localhost:5432/ufobotdb' ###########
        super().__init__(command_prefix, help_command=help_command, description=description, **options)

    # Yesy! my bot is my util too.
    def timeconv(self, secs: float, y= False):
        secs= round(secs)
        if y:
            time_dict= {'year': 31557600, 'month': 2629800,'day': 86400,'hour': 3600, 'min': 60}
        else:
            time_dict= {'day': 86400,'hour': 3600, 'min': 60}
        time= ''
        for unit in time_dict.keys():
            if secs > time_dict[unit]:
                unittime= secs // time_dict[unit]
                secs %= time_dict[unit]
                time += str(unittime) + ' '
                if unittime == 1:
                    time += unit + ' '
                else:
                    time += unit + 's' + ' '
        time += str(secs) + ' secs'
        return time

    async def on_ready(self):
        print('Bot is ready.')
        self.start_time= time()
        self.loop.create_task(self.initialization())

    async def on_message(self, message):
        pass

    # Database connection and cache stuff
    async def initialization(self):
        try:
            self.db= await asyncpg.create_pool(self.dsn, max_inactive_connection_lifetime= 3)
            self.inited= True
            print("'DB connected.' :\t", self.db)
        except Exception as error:
            print('Ignoring exception in {}:'.format(__name__), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            await self.close()
            return
        gencog= self.get_cog('General')
        await gencog.loopstarter()
        await self.db.execute('UPDATE guildsettings SET mutedmems = NULL')
        print('Waiting for prefixes, discmds and blacklisted channels to cache.')
        data= await self.db.fetch("SELECT guild_id, prefix, discmds, blackch FROM guildsettings\
            WHERE ( prefix != '.' OR prefix != NULL ) OR ( discmds != '{}' OR discmds != NULL ) OR ( blackch != '{}' OR blackch != NULL )")
        for record in data:
            self.cache.update({record['guild_id']:{"prefix":record['prefix'] or '.', "discmds":record['discmds'] or [], "blackch":record['blackch'] or []}})
        self.load_extension('cogs.listners')

# Intents and bot initialization
async def get_prefix(client, message):
    return client.cache.get(message.guild.id, {"prefix":'.'}).get("prefix"), '<@!822448143508963338>', '<@822448143508963338>'
intents: discord.Intents= discord.Intents.default()
intents.members    = True
intents.typing     = False
intents.presences  = False
intents.dm_typing  = False
intents.invites    = False
MyUFO = Ufo_bot(
    command_prefix= get_prefix,
    case_insensitive= True,
    description= "My name is UFO bot, made with discord.py in python.",
    strip_after_prefix= True,
    intents= intents,
    owner_id= 577471505265590273,
    member_cache_flags= discord.MemberCacheFlags.none(),
    help_command= None,
    allowed_mentions= discord.AllowedMentions(everyone= False, users= False, roles= False, replied_user= True),
    activity= discord.Activity(name= "Aliens 🛸", type= discord.ActivityType.listening), status= discord.Status.idle)

# Spam prevention system.
@MyUFO.event
async def on_command(ctx: commands.Context):
    if not ctx.author.id in MyUFO.commandusers.keys():
        MyUFO.commandusers.update({ctx.author.id: [True, 1]})
        await sleep(20)
        try:
            MyUFO.commandusers.pop(ctx.author.id)
        except:
            pass
    else:
        user_command_state= MyUFO.commandusers[ctx.author.id]
        user_command_state[1]+= 1
        user_command_state[0]= 1
        MyUFO.commandusers.update({ctx.author.id: user_command_state})
        if user_command_state[1]>= 9:
            MyUFO.commandusers.pop(ctx.author.id)
            with open(f'{sys.path[0]}/data/backlists.json', 'r') as backlists:
                backlisted= load(backlists)
                ordinality= len(backlisted['users']) + 1
                backlisted['users'].append(ctx.author.id)
            with open(f'{sys.path[0]}/data/backlists.json', 'w') as backlists:
                dump(backlisted, backlists)
                del backlisted
            ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
            await ctx.author.send(f'Well\'ll\'ll. You were the **{ordinal(ordinality)}** to get bot banned.')

@MyUFO.event
async def on_command_completion(ctx: commands.Context):
    MyUFO.commandused+=1
    if ctx.author.id in MyUFO.commandusers.keys():
        MyUFO.commandusers.update({ctx.author.id: [False, MyUFO.commandusers[ctx.author.id][1]]})

if __name__ == '__main__':
    # Loading cogs
    for filename in listdir(f'{sys.path[0]}/cogs'):
        if filename.startswith('listners'):
            continue
        if filename.endswith('.py'):
            MyUFO.load_extension(f'cogs.{filename[:-3]}')
    hc= Help()
    async def help_check(ctx: commands.Context):
        if not ctx.guild:
            return False
        else:
            return True
    hc.add_check(help_check)
    MyUFO.help_command= hc
    TOKEN = 'ODIyNDQ4MTQzNTA4OTYzMzM4.YFSahQ._GTSECvd4bnM8JCN1EbjjP95Kws'
    MyUFO.run(TOKEN)