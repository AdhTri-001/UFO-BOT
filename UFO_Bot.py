from datetime import datetime
import json
import re
from time import time
import discord
import os, sys, traceback
from aiopyql import data
from discord.ext import commands

async def get_prefix(client, message):
    if message.guild:
        try:
            pref= await client.db.tables['guildsettings'].select('prefix', where= {'guild_id' : message.guild.id})
            pref= pref[0]['prefix'] or '.'
        except IndexError or KeyError or AttributeError:
            pref= "."
        return [pref, "<@!822448143508963338>"]
    else:
        return ['.', "<@!822448143508963338>"]
# Intents and bot initialization
intents = discord.Intents.default()
intents.members = True
intents.typing = False
intents.presences = False
client = commands.Bot(
    command_prefix= get_prefix,
    case_insensitive= True,
    description= "My name is UFO bot, a bot made with discord.py in python.",
    strip_after_prefix= True,
    intents= intents,
    owner_id= 577471505265590273,
    member_cache_flags= discord.MemberCacheFlags.none(),
    help_command= None)

# I m lazy to making new utils forlder and add these stuff there sorry
def timeconv(secs: float, y= False):
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

async def get_mlog_ch(guild):
    raw= await client.db.tables['guildsettings'].select('logch_id', where= {'modlog': True, 'guild_id': str(guild.id)})
    print('hi')
    try:
        return client.get_channel(int(raw[0]['logch_id']))
    except:
        return None

client.timeconv= timeconv
client.commandusers= []
client.inited= False
client.commandused= 0
client.errorcount= 0
client.mutemem= []
client.modlogch= get_mlog_ch

# Helps me to check is the bot ready?
@client.event
async def on_ready():
    print('Bot is ready.')
    await client.change_presence(activity= discord.Activity(name= "Aliens 🛸", type= discord.ActivityType.listening), status= discord.Status.idle)
    client.start_time= time()
    client.loop.create_task(initialization())

# Runs when a command is triggered
@client.event
async def on_command(ctx):
    client.commandusers.append(ctx.author.id)

# Runs after commands finishs
@client.event
async def on_command_completion(ctx):
    try:
        client.commandused+= 1
        client.commandusers.pop(client.commandusers.index(ctx.author.id))
    except:
        pass

@client.event
async def on_message(message):
    if message.author.id in client.commandusers:
        return
    with open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'))) as backlists:
        backlisted = json.load(backlists)
        if message.author.id in backlisted['users']:
            return
        if message.guild != None and message.guild.id in backlisted['guilds']:
            return
    if message.author.bot:
        return
    await client.process_commands(message)

# Database connection
async def initialization():
    try:
        client.db= await data.Database.create(database='postgres',
            user='postgres',
            password='yoyome9104',
            host='localhost',
            port=9977,
            db_type= 'postgres')
        client.inited= True
        print("'DB connected.'")
        await client.wait_until_ready()
        gencog= client.get_cog('General')
        await gencog.loopstarter()
        client.load_extension('cogs.listners')
    except Exception as error:
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print('Ignoring exception in {}:'.format(__name__), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await client.close()

TOKEN = 'ODIyNDQ4MTQzNTA4OTYzMzM4.YFSahQ._GTSECvd4bnM8JCN1EbjjP95Kws'

# Loading cogs
for filename in os.listdir(f'{sys.path[0]}/cogs'):
    if filename.startswith('listners'):
        continue
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

# help command, noice!
class Help(commands.MinimalHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.command_attrs= {'name': 'help', 'aliases': ['commands'], 'help': 'Provides help to the command or Category(First letter capital)'}

    def get_command_help(self, command):
        cmdhelp= command.help or "No help given for this command."
        cmddesc= command.description or ""
        signature= self.get_command_signature(command)
        if not ' ' in signature:
            return f"```{signature}```{cmdhelp}\n{cmddesc}"
        cmddata= signature.split(command.name, 1)
        cmddata[1]= re.sub(r'=.{2,}\]', ']', cmddata[1])
        signature= command.name.join(cmddata)
        return f"```{signature}```{cmdhelp}\n{cmddesc}"

    def group_command_signature(self, command):
        signature= self.get_command_signature(command)
        if command.aliases:
            signature= signature.replace(command.name, '|'.join(command.aliases)+f'|{command.name}')
        return signature

    # @UFO bot help
    async def send_bot_help(self, mapping):
        prefix= await get_prefix(client, self.context.message)
        embed= discord.Embed(title= "UFO bot help!",
            timestamp= datetime.utcnow(),
            color= self.context.me.color,
            description= f"Use {prefix[0]}help <command_name> to get help for that command.\nUse {prefix[0]}help <Category_name> to get help for that command.(Case Sensitive)")
        embed.set_author(name= str(self.context.author), icon_url= self.context.author.avatar_url)
        for cog, commands in mapping.items():
            commands= await self.filter_commands(commands, sort= True)
            comdsigns= [c.name for c in commands]
            try:
                comdsigns.pop(comdsigns.index('help'))
            except ValueError:
                pass
            if comdsigns:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value=f'```{", ".join(comdsigns)}```', inline=False)

        await self.context.send(embed=embed)

    # @UFO bot help <command>
    async def send_command_help(self, command):
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
            signature= self.group_command_signature(command)
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
        commands= await self.filter_commands(cog.get_commands(), sort= True)
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

client.help_command= Help()

client.run(TOKEN)