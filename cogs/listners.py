from typing import Union
import discord
from discord.ext import commands
from datetime import datetime
from time import time
from colorama import Style, Fore
from random import choice

class Listners(commands.Cog):
    def __init__(self, client):
        self.client= client

    print('Listners.py has been loaded\n-----------------------------------')

    async def file_case(self, guild, action, member, reason= "No reason provided pls use `case` command to file the reason."):
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.strip() == '<@!822448143508963338>':
            prefix = self.client.command_prefix(message, self.client)
            await message.channel.send(f"My prefix at this guild is `{prefix.pop(0)}`. Alternatively u can mention me at the start of ur message if u dont remember the prefix.")
            return
        # AUTOMODERATION COMING SOON...

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

    # Sends a message to a channel when a member joins and also give the startrole
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        startrole= await self.client.db.tables['guildsettings'].select('startrole_id', where= {'guild_id':member.guild.id})
        startrole= startrole[0]['startrole_id']
        mutemems= [mutemem[0] for mutemem in self.client.mutemem]
        if startrole:
            try:
                await member.add_roles(discord.Object(int(startrole)))
            except:
                mlogch= self.client.modlogch(member.guild)
                if mlogch:
                    await mlogch.send(f'New member **{member.display_name}** joined, I was sunable to add start role({startrole})')
        if member in mutemems:
            muterole= await self.client.db.tables['guildsettings'].select('muterole_id',where= {'guild_id': member.guild.id})
            muterole= muterole[0]['muterole_id']
            if muterole == None or muterole == 'NULL':
                return
            try:
                muterole= discord.Object(int(muterole))
                await member.add_roles(muterole, reason= 'Tryied to leave and rejoin to remove mute role.')
            except:
                pass
        try:
            await self.send_greet(member)
        except:
            pass

    # Sends a message to a channel when a member leaves
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        banEnts= await member.guild.bans()
        banUserIds= []
        for Entery in banEnts:
            banUserIds.append(Entery[1].id)
        if member.id in banUserIds:
            banned= True
        else: banned= False
        try:
            await self.send_leave(member, banned)
        except:
            pass

    # Snipe the message and tranfer to db.
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        try:
            if message.author.bot or message.embeds or len(message.content)> 500:
                return
            await self.client.db.tables['snipes'].upsert(channel_id= message.channel.id, author_pfp= message.author.avatar_url,
                message_content= message.content, timestamp= time(), author_name= str(message.author))
        except:
            pass

    # Handles all the errors bot faces.
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        try:
            self.client.commandusers.pop(self.client.commandusers.index(ctx.author.id))
        except ValueError:
            pass
        if isinstance(error, commands.MissingRole):
            return
        if isinstance(error, commands.MissingPermissions):
            return
        if isinstance(error, commands.MissingAnyRole):
            return
        if isinstance(error, commands.CommandOnCooldown):
            embed= discord.Embed(
                title= choice(['Cooldown', 'Chill', 'Relax']),
                description= f'**{ctx.command}** is in cooldown, retry after {round(error.retry_after, 2)} secs.'
            )
        elif isinstance(error, commands.BadUnionArgument):
            embed= discord.Embed(
                title= 'Bad argument',
                description= f'The argument u passed failed to parse'
            )
        elif isinstance(error, commands.CheckFailure):
            return
        elif isinstance(error, commands.NoPrivateMessage):
            embed= discord.Embed(
                title= 'Guild Only',
                description= f'**{ctx.command}** is a guild only command, doesn\'t work on DMs.'
            )
        elif isinstance(error, commands.BadArgument):
            embed= discord.Embed(
                title= 'Bad Argument',
                description= str(error)
            )
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed= discord.Embed(
                title= 'Missing Argument',
                description= f'{error.param} is the required argument that is missing.'
            )
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.MemberNotFound):
            embed= discord.Embed(
                title= 'Member Not found',
                description= f'"{error.argument}" Is not a member.'
            )
        elif isinstance(error, commands.UserNotFound):
            embed= discord.Embed(
                title= 'User Not found',
                description= f'"{error.argument}" Is not a User.'
            )
        elif isinstance(error, commands.ChannelNotFound):
            embed= discord.Embed(
                title= 'Channel not found',
                description= f'Channel not found, or if it exists it\'s not visible to me.'
            )
        elif isinstance(error, commands.MessageNotFound):
            embed= discord.Embed(
                title= 'Message not found',
                description= f'Can\'t find any such message.'
            )
        elif isinstance(error, commands.RoleNotFound):
            embed= discord.Embed(
                title= 'Role not found',
                description= f'"{error.argument}" can\'t find any such role.'
            )
        elif isinstance(error, commands.BotMissingPermissions):
            embed= discord.Embed(
                title= 'Not enough perms',
                description= f'"{error.missing_perms}" is the required permission for this command to run.'
            )
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.UserNotFound):
            embed= discord.Embed(
                title= 'User Not found',
                description= f'"{error.argument}" Is not a user.'
            )
        else:
            embed= discord.Embed(
                title= 'A wild error occured.',
                description= repr(error),
                timestamp= datetime.utcnow()
            )
            await ctx.send(embed= embed)
            error_ch: discord.TextChannel= self.client.get_channel(id=848123775161335828)
            embed.add_field(name= 'Guild id', value= ctx.guild.id)
            embed.add_field(name= 'Channel id', value= ctx.channel.id)
            await error_ch.send(embed= embed)
            print(f'{Fore.RED}-==================================================================-{Style.RESET_ALL}')
            raise error
        embed.set_author(name= f'{ctx.author}', icon_url= ctx.author.avatar_url)
        self.client.errorcount+= 1
        embed.set_footer(icon_url= 'https://data.whicdn.com/images/287267204/original.gif',
            text= f'Errors this session: {self.client.errorcount}')
        embed.color= discord.Color.dark_theme()
        await ctx.send(embed= embed, delete_after= 10)

    # Sends a modlogs on ban
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        channel= await self.client.modlogch(guild)
        if not channel: return
        try:
            bans= await guild.bans()
            for banent in bans:
                if banent[1].id == user.id:
                    banreason= banent[0] or 'No reason provided.'
                    break
            await self.modlogger.log_moderation(guild, user, 'Banned', banreason, fields= [{'name': 'Total bans now!', 'value': len(bans)}])
        except:
            await channel.send('`I have not permissions to see bans. give me auditlogs and ban members.`')

    # Sends a modlog on unban
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        channel= await self.client.modlogch(guild)
        if not channel: return
        try:
            bans= await guild.bans()
            await self.modlogger.log_moderation(guild, user, 'Banned', None, fields= [{'name': 'Total bans now!', 'value': len(bans)}])
        except:
            await channel.send('`I have not permissions to see bans. Give me audit logs and ban members`')

    # Sends a modlog on role add
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        channel= await self.client.modlogch(after.guild)
        if not channel: return
        roleupdated= set(after.roles).symmetric_difference(set(before.roles))
        if not list(roleupdated):
            return
        roleupdated= roleupdated[0]
        embed= discord.Embed(
            title= 'Roles Updated',
            description= f'{roleupdated.mention} was {"given to" if before.roles< after.roles else "removed from"} {after.mention}',
            color= discord.Color.blurple()
        )
        await channel.send(embed=embed)

    # Send a modlog on guild update
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        channel= await self.client.modlogch(after)
        if not channel: return
        if before.name != after.name:
            delta= ('Name Changed', before.name, after.name)
        elif before.afk_channel != after.afk_channel:
            delta= ('AFK Channel Changed!', before.afk_channel, after.afk_channel)
        else:
            return
        embed= discord.Embed(
            title= 'GUILD UPDATED!',
            description= delta[0],
            color= discord.Color.blurple()
        )
        embed.add_field(name= 'Before', value= f'{delta[1]}', inline= False)
        embed.add_field(name= 'After', value= f'{delta[2]}', inline= False)
        await channel.send(embed= embed)

    # Send a modlog on bulk delete
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        channel= await self.client.modlogch(messages[0].guild)
        if not channel: return
        if not messages[0].guild:
            return
        embed= discord.Embed(title= 'Bulk Delete!',
            description= f'A total of {len(messages)} were deleted in {messages[0].channel.mention}',
            color= discord.Color.blurple())
        await channel.send(embed= embed)

def setup(client):
    client.add_cog(Listners(client))