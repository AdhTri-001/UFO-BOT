import asyncio, os
import json
import discord
from discord.ext import commands
from typing import Union
from datetime import datetime

class Settings(commands.Cog):
    def __init__(self, client):
        self.client = client

    print("Settings.py has been loaded\n-----------------------------------")

    async def cog_check(self, ctx):
        if ctx.guild:
            return True
        else:
            return False

    def is_guild_owner():
        async def predicate(ctx):
            return ctx.author.id== ctx.guild.owner_id
        return commands.check(predicate)

    async def send_greet(self, member, channel= None):
        raw= await self.client.db.tables['guildsettings'].select('greetch', 'greetmsg', where= {'guild_id': member.guild.id})
        raw= raw[0]
        greetch= channel or self.client.get_channel(int(raw['greetch']))
        if greetch != 'NULL' or greetch:
            embed= discord.Embed(
                title= f'Welcome to {member.guild}!',
                description= raw['greetmsg'] or f'Welcome {member.mention}, hope you have a great stay here. Pls follow the server rules.',
                color= member.guild.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= str(member), icon_url= member.avatar_url)
            embed.set_thumbnail(url= member.guild.icon_url)
            await greetch.send("_This is a preview of greet embed_" if channel else None,embed= embed)

    async def send_leave(self, member, ban: bool, channel= None):
        raw= await self.client.db.tables['guildsettings'].select('leavech', 'leavemsg', where= {'guild_id': member.guild.id})
        raw= raw[0]
        leavech= channel or self.client.get_channel(int(raw['leavech']))
        if leavech != 'NULL' or leavech:
            embed= discord.Embed(
                title= f'Welcome to {member.guild}!',
                description= raw['leavemsg'] or f'Welcome {member.mention}, hope you have a great stay here. Pls follow the server rules.',
                color= member.guild.me.color,
                timestamp= datetime.utcnow()
            )
            embed.set_author(name= str(member), icon_url= member.avatar_url)
            embed.set_thumbnail(url= member.guild.icon_url)
            await leavech.send("_This is a preview of Farewell embed_" if channel else None, embed= embed)

    async def cog_check(self, ctx):
        if ctx.guild:
            return True
        else:
            False

    # Bot Settings Commands
    async def embeder(self, ctx, change:str, to:str):
        embed= discord.Embed(
            title= '⚙ Settings', description= f'{change} set to {to}',
            color= ctx.author.color, timestamp= datetime.utcnow())
        embed.set_author(name= ctx.author, icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
    
    # T_T Oh! why do we show offence to a single character ``.``
    @commands.command(aliases= ['pref'],
        help="come on this is easy, just pass the prefix of ur preference",
        description="Prefix can't be more then 5 letters. U need admin perms to use this command"
    )
    @commands.has_guild_permissions(administrator= True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def prefix(self, ctx, prefix = '.'):
        if len(str(prefix)) > 5:
            await ctx.send('Your prefix can\'t be longer then 5 letters!')
            return
        vals= {'guild_id': ctx.guild.id, 'prefix': prefix}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Prefix', f'`{prefix}`')

    # My dear master, aka bot master
    @commands.command(
        help="Mention the role, or give role id, or exect role name.",
        description="Set the mod role that can use commands marked under catagory Moderation."
    )
    @commands.has_guild_permissions(administrator= True)
    async def modrole(self, ctx, *, role : discord.Role = None):
        if not role:
            vals= {'guild_id': ctx.guild.id, 'modrole_id': None}
            await self.client.db.tables['guildsettings'].upsert(**vals)
            await self.embeder(ctx, 'Mod Role', 'None')
            return
        vals= {'guild_id': ctx.guild.id, 'modrole_id': role.id}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Mod Role', role.mention)
    
    # Yes! modlogs are for, for and only for no one T_T ppl just ignore them or mark as read.
    @commands.group(aliases= ['mlog'],
        help="See the modlogs of members or enable disable them after enabling u also need to set a channel with `modlog channel`.",
        description="This command needs `admin` perms too, members can check there warnings with `warnings`",
        invoke_without_command= True
    )
    @commands.has_guild_permissions(administrator= True)
    async def modlog(self, ctx, member: Union[discord.Member, None]):
        return
    @modlog.command(aliases= ['enable', 'true', '1'],
        help="enables the mod logs.",
        description=""
    )
    async def on(self, ctx):
        vals= {'guild_id': ctx.guild.id, 'modlog': True}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Modlogs', '`enable`')
    @modlog.command(aliases= ['disable', 'false', '0'],
        help="enables the mod logs.",
        description=""
    )
    async def off(self, ctx):
        vals= {'guild_id': ctx.guild.id, 'modlog': False}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Modlogs', '`disable`')
    @modlog.command(aliases= ['ch'],
        help="Mention/provide id/Name the channel.",
        description=""
    )
    async def channel(self, ctx, channel : discord.TextChannel = None):
        vals= {'guild_id': ctx.guild.id, 'logch_id': channel.id}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Mod Log Channel', channel.mention)
    
    # I don't like @everyone ping so i mention startrole. Think smart
    @commands.command(aliases= ['strole'],
        help="Mention the role, or give role id, or exect role name. Please!",
        description="Greet the new comers with a start role."
    )
    @commands.has_guild_permissions(administrator= True)
    async def startrole(self, ctx, *, role : discord.Role = None):
        if role == None:
            roleid= None
            rolemention= None
        else:
            roleid= role.id
            rolemention= role.mention
        vals= {'guild_id': ctx.guild.id, 'startrole_id': roleid}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Start role', rolemention)
    
    # The role to dismiss cancerous ppl.
    @commands.command(
        help="Mention the role, or give role id, or exect role name.",
        description="Sets the role to be given while muting someone."
    )
    @commands.has_guild_permissions(administrator= True)
    async def muterole(self, ctx, *, role: discord.Role= None):
        oldmuterole= await self.client.db.tables['guildsettings'].select('muterole_id', where= {'guild_id': ctx.guild.id})
        def check(m):
            return m.content.lower() in ['y', 'n'] and m.author == ctx.author
        if role == None and oldmuterole[0]['muterole_id'] == None:
            role= await ctx.guild.create_role(name= 'Muted', colour= discord.Color.light_grey(), reason= f'{ctx.author.name}#{ctx.author.discriminator}')
        elif role == None:
            embed= discord.Embed(description= 'This guild already have a mute role setup <@&'+oldmuterole[0]['muterole_id']+'>.\nYou want me to change it and make a new one? (y/n)')
            warning= await ctx.send(embed= embed)
            try:
                msg= await self.client.wait_for('message', timeout= 20, check= check)
            except asyncio.TimeoutError:
                await ctx.send('Alright its a no!')
                return
            try:
                await warning.delete()
                await msg.delete()
            except:
                pass
            if msg.content.lower() == 'n':
                return
            role= await ctx.guild.create_role(name= 'Muted', reason= f'{ctx.author.name}#{ctx.author.discriminator}')
        vals= {'guild_id': ctx.guild.id, 'muterole_id': role.id}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Mute role', role.mention)
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(role, send_messages=False, connect= False)
            except:
                pass
    
    # I will kick those who pass warning threshold
    @commands.command(
        help="Bot automatically kick someone when he pass kickat threshold.",
        description="Can't be less then 3, pass 0 to disable"
    )
    @commands.has_guild_permissions(administrator= True)
    async def kickat(self, ctx, *, kickat: int= 0):
        if kickat == 0:
            vals= {'guild_id': ctx.guild.id, 'kickat': kickat}
            await self.client.db.tables['guildsettings'].upsert(**vals)
            return await ctx.send("Kickat disabled!")
        if kickat < 3:
            return await ctx.send(":x: Kick at value can't be less then 3.")
        vals= {'guild_id': ctx.guild.id, 'kickat': kickat}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Kick At", kickat)

    # I will ban those who pass warning threshold
    @commands.command(
        help="Bot automatically ban someone when he pass kickat threshold.",
        description="Can't be less then 4, pass 0 to disable"
    )
    @commands.has_guild_permissions(administrator= True)
    async def banat(self, ctx, *, banat: int= 0):
        if banat == 0:
            vals= {'guild_id': ctx.guild.id, 'banat': banat}
            await self.client.db.tables['guildsettings'].upsert(**vals)
            return await ctx.send("Banat disabled!")
        if banat < 4:
            return await ctx.send(":x: Ban at value can't be less then 4.")
        vals= {'guild_id': ctx.guild.id, 'banat': banat}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Ban At", banat)

    # Greet command
    @commands.group(aliases= ['welcome'], invoke_without_command=True, help= 'Sends a sample of greet embed.')
    @commands.has_guild_permissions(administrator= True)
    async def greet(self, ctx):
        await self.send_greet(ctx.author, ctx.channel)
    @greet.command(aliases= ['channel'],
        help= 'Set a greet channel',
        description= 'This will use the default greet message, use `greetmsg` command to set a custom message.')
    @commands.has_guild_permissions(administrator= True)
    async def ch(self, ctx, channel: Union[discord.TextChannel, None]):
        if channel:
            vals= {'guild_id': ctx.guild.id, 'greetch': channel.id}
        else:
            vals= {'guild_id': ctx.guild.id, 'greetch': None}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Greet channel", f'{channel}')
    @greet.command(aliases= ['msg'],
        help= 'Set a message to be send to `leave channel`. If no arg was passed the bot will use default one')
    @commands.has_guild_permissions(administrator= True)
    async def message(self, ctx, *, message= None):
        if len(message) > 600:
            await ctx.send('To long text not excepted.')
            return
        vals= {'guild_id': ctx.guild.id, 'greetmsg': message}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Greet message", f'The given message' if message else 'The default one.')

    # Farewell command
    @commands.group(aliases= ['farewell'], invoke_without_command=True, help= 'Sends a sample of leave embed.')
    @commands.has_guild_permissions(administrator= True)
    async def leave(self, ctx):
        await self.send_leave(ctx.author, False, ctx.channel)
    @leave.command(name= 'ch', aliases= ['channel'],
        help= 'Set a leave channel',
        description= 'This will use the default leave message, use `leavemsg` command to set a custom message.')
    @commands.has_guild_permissions(administrator= True)
    async def _ch(self, ctx, channel: Union[discord.TextChannel, None]):
        if channel:
            vals= {'guild_id': ctx.guild.id, 'leavech': channel.id}
        else:
            vals= {'guild_id': ctx.guild.id, 'leavech': None}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Farewell channel", f'{channel}')
    @leave.command(name= 'message', aliases= ['msg'],
        help= 'Set a message to be send to `leave channel`. If no arg was passed the bot will use default one')
    @commands.has_guild_permissions(administrator= True)
    async def _message(self, ctx, *, message= None):
        if len(message) > 600:
            await ctx.send('To long text not excepted.')
            return
        vals= {'guild_id': ctx.guild.id, 'leavemsg': message}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, "Farewell message", f'The given message' if message else 'The default one.')

    # Chech out the current Guild settings.
    @commands.command(aliases= ['sets'],
        help="This will display the current server settings",
        description="This command is just for confirmation, tho recommanded to use it in private channels."
    )
    @commands.has_guild_permissions(manage_guild= True, manage_permissions= True, manage_roles= True, view_audit_log= True)
    async def settings(self, ctx):
        settings= await self.client.db.tables['guildsettings'].select('*', where= {'guild_id': ctx.guild.id})
        settings= settings[0]
        embed= discord.Embed(title= 'Current Guild Settings', Timestamp= datetime.utcnow(), color= discord.Color.random())
        embed.set_author(name= ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.add_field(name= 'Start role', value= '<@&{}>'.format(settings['startrole_id'])) if settings['startrole_id'] else None
        embed.add_field(name= 'Mute role', value= '<@&{}>'.format(settings['muterole_id'])) if settings['muterole_id'] else None
        embed.add_field(name= 'Mod role', value= '<@&{}>'.format(settings['modrole_id']), inline= False) if settings['modrole_id'] else None
        embed.add_field(name= 'Kick At', value= settings['kickat']) if settings['kickat'] else None
        embed.add_field(name= 'Ban At', value= settings['banat']) if settings['banat'] else None
        embed.add_field(name= 'Greet channel', value= f'<#{settings["greetch"]}>') if settings["greetch"] else None
        embed.add_field(name= 'Goodbye channel', value= f'<#{settings["leavech"]}>') if settings["leavech"] else None
        if not embed.fields:
            await ctx.send('"Nothing to see here"')
            return
        await ctx.send(embed= embed)

    # Disable command
    @commands.command(name= 'disable', help= 'Disable a command')
    @commands.has_guild_permissions(manage_guild= True)
    async def _disable(self, ctx, cmd):
        cmd= self.client.get_command(cmd)
        if cmd.cog.qualified_name == 'Settings' or cmd.cog == None:
            await ctx.send('This command can\'t be disabled.')
            return
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        discmds= discmds[0]['discmds']
        if cmd.name in discmds:
            await ctx.send('This command already disabled buddy.')
            return
        discmds.append(cmd.name)
        vals= {'guild_id': ctx.guild.id, 'discmds': discmds}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, f'Command {cmd.name}', 'disabled')

    # Enable command
    @commands.command(name= 'enable', help= 'Enable a disabled command')
    @commands.has_guild_permissions(manage_guild= True)
    async def _enable(self, ctx, cmd):
        cmd= self.client.get_command(cmd)
        if cmd.cog.qualified_name == 'Settings' or cmd.cog == None:
            await ctx.send('This command can\'t be disabled.')
            return
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        discmds= discmds[0]['discmds']
        if not cmd.name in discmds:
            await ctx.send('This command was never disabled buddy.')
            return
        discmds.remove(cmd.name)
        vals= {'guild_id': ctx.guild.id, 'discmds': discmds}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, f'Command {cmd.name}', 'enabled')

    # set Ranks
    @commands.group(aliases= ['joinroles'],
        help= 'With this command you can set the role that can be joined by members with `rank add` command.', invoke_without_command=True)
    @commands.bot_has_guild_permissions(manage_roles= True)
    async def ranks(self, ctx):
        ranks= await self.client.db.tables['guildsettings'].select('ranks', where= {'guild_id': ctx.guild.id})
        ranks= ranks[0]['ranks']
        if not ranks:
            return await ctx.send('There are no ranks setuped in the server, start adding them with `ranks add` command')
        pag= commands.Paginator(prefix='', suffix= '', linesep= ' • ')
        for rank in ranks:
            pag.add_line(f'<@&{rank}>')
        for page in pag.pages:
            embed= discord.Embed(title= f'{ctx.guild}\'s Ranks list',
                description= page,
                color= ctx.me.color)
            await ctx.send(embed= embed)
    @ranks.command(aliases= ['new', 'create'], help= 'Add a rank that members can join, these are just joinable role with `rank` command')
    @commands.has_guild_permissions(manage_guild= True, manage_roles= True)
    async def add(self, ctx, role: discord.Role):
        ranks= await self.client.db.tables['guildsettings'].select('ranks', where= {'guild_id': ctx.guild.id})
        ranks= ranks[0]['ranks']
        if role.position >= ctx.me.top_role.position:
            return await ctx.send('That role is above me, move the role below my top role so that I can add roles to members.')
        if not ranks:
            ranks= [str(role.id)]
        else:
            if str(role.id) in ranks:
                return await ctx.send('That role is already a rank, lets not do it.')
            ranks.append(str(role.id))
        vals= {'guild_id': ctx.guild.id, 'ranks': ranks}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Added rank', role.mention)
    @ranks.command(aliases= ['delete'], help= 'Remove a rank that members can join, these are just joinable role with `rank` command')
    @commands.has_guild_permissions(manage_guild= True, manage_roles= True)
    async def remove(self, ctx, role: discord.Role):
        ranks= await self.client.db.tables['guildsettings'].select('ranks', where= {'guild_id': ctx.guild.id})
        ranks= ranks[0]['ranks']
        try:
            ranks.remove(str(role.id))
        except:
            await ctx.send('That role was never a rank, what you doing?')
            return
        vals= {'guild_id': ctx.guild.id, 'ranks': ranks}
        await self.client.db.tables['guildsettings'].upsert(**vals)
        await self.embeder(ctx, 'Removed rank', role.mention)
    @ranks.command(aliases= ['give'], help= 'Join a rank!')
    async def join(self,ctx, role: discord.Role):
        ranks= await self.client.db.tables['guildsettings'].select('ranks', where= {'guild_id': ctx.guild.id})
        ranks= ranks[0]['ranks']
        if not str(role.id) in ranks:
            await ctx.send("That rank doesn't exist in this server. Use `ranks` command to see list of ranks")
            return
        if role in ctx.author.roles:
            await ctx.send('You already have that role!')
        embed= discord.Embed(
            title= 'Rank added',
            description= f'{role.mention} Was Added!',
            color= ctx.me.color
        )
        try:
            await ctx.author.add_roles(discord.Object(role.id), reason= f'Joined a rank {role.name}')
            await ctx.send(embed= embed)
        except: return await ctx.send('I m not able to add the role, push the rank below my top role.')
    @ranks.command(aliases= ['takeaway'], help= 'Drop a rank!')
    async def drop(self,ctx, role: discord.Role):
        ranks= await self.client.db.tables['guildsettings'].select('ranks', where= {'guild_id': ctx.guild.id})
        ranks= ranks[0]['ranks']
        if not str(role.id) in ranks:
            await ctx.send("That rank doesn't exist in this server. Use `ranks` command to see list of ranks")
            return
        if not role in ctx.author.roles:
            await ctx.send('You dont have that role already!')
        embed= discord.Embed(
            title= 'Rank removed',
            description= f'{role.mention} Was Taken!',
            color= ctx.me.color
        )
        try:
            await ctx.author.remove_roles(discord.Object(role.id), reason= f'Joined a rank {role.name}')
            await ctx.send(embed= embed)
        except: return await ctx.send('I was unable to remove the role, push the rank below my top role.')

    @commands.command(aliases= ['nolisten'], help= 'This will stop the bot to listen commands on the current or mentioned channels')
    @commands.has_guild_permissions(manage_channels= True)
    async def backlist(self, ctx, channel: discord.TextChannel= None):
        channel: discord.TextChannel= channel or ctx.channel
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if not channel.id in backlisted['channel']:
            backlisted['channel'].append(channel.id)
            await ctx.send(f'Backlisted {channel.mention}, I won\'t listen any command in that channel.')
        else:
            await ctx.send('That channel is already backlisted')
            return
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()
    
    @commands.command(aliases= ['plslisten'], help= 'This will stop the bot to listen commands on the current or mentioned channels')
    @commands.has_guild_permissions(manage_channels= True)
    async def whitelist(self, ctx, channel: discord.TextChannel= None):
        channel: discord.TextChannel= channel or ctx.channel
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if channel.id in backlisted['channel']:
            backlisted['channel'].remove(channel.id)
            await ctx.send(f'Whitelisted {channel.mention}, I will listen the commands in that channel.')
        else:
            await ctx.send('That channel is already whitelisted')
            return
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()

    # Command to reset all the bot data in the current guild
    @commands.command(aliases= ['removedata'], help= 'DELETE every guild setting that you set. You NEED TO BE guild owner to use this.')
    @is_guild_owner()
    async def factoryReset(self, ctx):
        await ctx.send('This will delete all the bot settings in this server. Tho this won\'t remove the backlisted channels.\nYou sure? (y/n)')
        def check(m):
            return ctx.author.id== m.auhtor.id and ctx.channel.id== m.channel.id and m.content.lower() in ['y','n']
        try:
            msg= self.client.wait_for('message', check= check, timeout= 30.0)
        except:
            await ctx.send('Phew')
        if msg.content.lower() == 'y':
            await self.client.db.tables['guildsettings'].delete(where= {'guild_id': f'{ctx.guild.id}'})
            await ctx.send('Damn all settings are now gone.')

    # Bot Owner Commands ----------------
    @commands.command(aliases= ['botban'])
    @commands.is_owner()
    async def bban(self, ctx, *, param: Union[discord.User, discord.Guild]):
        backlists=  open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if isinstance(param, discord.User):
            backlisted['users'].append(param.id)
        if isinstance(param, discord.Guild):
            backlisted['guilds'].append(param.id)
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()
        await ctx.send(f'Bot banned `{param.id}`')

    @commands.command(aliases= ['botunban'])
    @commands.is_owner()
    async def bunban(self, ctx, *, param: Union[discord.User, discord.Guild]):
        backlists=  open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')))
        backlisted= json.load(backlists)
        backlists.close()
        if isinstance(param, discord.User):
            backlisted['users'].remove(param.id)
        if isinstance(param, discord.Guild):
            backlisted['guilds'].remove(param.id)
        backlists= open('{}/data/backlists.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..')), 'w')
        json.dump(backlisted, backlists)
        backlists.close()
        await ctx.send(f'Bot unbanned `{param.id}`')

def setup(client):
    client.add_cog(Settings(client))