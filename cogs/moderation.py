import datetime, discord, re
import json
from discord.ext import commands, tasks
from typing import Union
from discord.ext.commands.cooldowns import BucketType
from time import time
from asyncio import sleep

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client= client
    
    print("Moderation.py has been loaded\n-----------------------------------")

    @commands.Cog.listener()
    async def on_ready(self):
        await sleep(10)
        self.mutetask= self.mutehandler.start()
        print('Started Mute Task in Moderation.py')
        await sleep(10)
        self.tempbanstask= self.tempban_handler.start()
        print('Started tempBan Task in Moderation.py')

    # Checking for disabled commands
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        try:
            return not ctx.command.name in discmds[0]['discmds']
        except: return True

    # Custom Check if user can moderate with the power of modrole
    async def has_modrole(ctx):
        modrole= await ctx.bot.db.tables['guildsettings'].select('modrole_id', where= {'guild_id': ctx.guild.id})
        if modrole[0]['modrole_id']== None or modrole[0]['modrole_id'] == 'NULL':
            return False
        try:
            return await commands.has_role(int(modrole[0]['modrole_id'])).predicate(ctx)
        except:
            return False

    async def brokencl(self, ctx, count, check):
        tod= datetime.datetime.now()
        d= datetime.timedelta(days= 13)
        dt= tod - d
        deleted= 0
        if count<=0:
            raise commands.BadArgument(message= 'Count should be a positive number.')
        if count<= 100:
            deleted+= len(await ctx.channel.purge(limit= count, after= dt, check= check))
        else:
            for i in range(1, 11):
                deleted+= len(await ctx.channel.purge(limit= 100, after= dt, check= check))
                count-= 100
                if count< 100:
                    deleted+= len(await ctx.channel.purge(limit= count, after= dt, check= check))
                    break
        return deleted

    async def brokencltill(self, ctx, check, msg):
        dt= msg.created_at
        deleted= 0
        for i in range(1, 11):
            deld= deleted
            deleted+= len(await ctx.channel.purge(limit= 100, after= dt, check= check))
            if deld== deleted:
                #if msg.created_at.timestamp() > discord.Object(ctx.channel.last_message_id).created_at.timestamp():
                break
        return deleted

    # Convert time.
    def convert(self, time):
        time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
        time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}
        time = time.lower()
        matches = re.findall(time_regex, time)
        time = 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
                raise commands.BadArgument(f"{value} is an invalid time key! h|m|s|d are valid arguments")
            except ValueError:
                raise commands.BadArgument(f"{key} is not a number!")
        return round(time)

    # Mute handler.
    @tasks.loop(seconds= 30)
    async def mutehandler(self):
        for muteEntry in self.client.mutemem:
            if muteEntry[1] > datetime.datetime.utcnow().timestamp():
                try:
                    muterole= await self.client.db.tables['guildsettings'].select('muterole_id',where= {'guild_id': muteEntry[0].guild.id})
                    muterole= muterole[0]['muterole_id']
                    await muteEntry[0].remove_roles(discord.Object(int(muterole)), reason= f'{muteEntry[0]} Unmuted after timeout.')
                except:
                    pass

    # Temp bans handler.
    @tasks.loop(seconds= 30)
    async def tempban_handler(self):
        tempbans= await self.client.db.tables['tempbans'].select('*', where= [['timestamp', '<', time()]])
        if not tempbans:
            return
        for tempban in tempbans:
            user= discord.Object(int(tempban['user_id']))
            guild= self.client.get_guild(int(tempban['guild_id']))
            await guild.unban(user, reason= 'This user was banned using tempban command. There time has come to taste unban.')

    # clear command
    @commands.group(aliases= ['purge', 'delete'], invoke_without_command=True)
    @commands.cooldown(2, 7, BucketType.guild)
    @commands.bot_has_permissions(manage_messages= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_messages= True, manage_guild= True))
    @commands.guild_only()
    async def clear(self, ctx, count : int, *, user: discord.Member= None):
        if not user:
            def check(m):
                return True
        else:
            def check(m):
                return m.author.id == user.id
        await ctx.channel.trigger_typing()
        start= time()
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, check)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command()
    async def bots(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_a_bot(m):
            return m.author.bot
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, is_a_bot)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['humans', 'nonbots', 'user'])
    async def users(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_a_user(m):
            return not m.author.bot
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, is_a_user)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['embed'])
    async def embeds(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_embeds(m):
            return len(m.embeds) != 0
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, has_embeds)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['u','self'])
    async def you(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_me(m):
            return self.client.user == m.author
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, is_me)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['links','url'])
    async def link(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_link(m):
            regex= r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
            if re.search(regex, m.content):
                return True
            else: return False
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, has_link)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['invites'])
    async def invte(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_invite(m):
            regex= r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
            if re.search(regex, m.content):
                return True
            else: return False
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, has_invite)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['attachments'])
    async def files(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_attachments(m):
            regex= r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
            if m.attachments:
                return True
            else: return False
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, has_attachments)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['pin'])
    async def pins(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def is_pinned(m):
            return m.pinned
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, is_pinned)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['contains'])
    async def contain(self, ctx, count: int, *, text:str):
        await ctx.channel.trigger_typing()
        start= time()
        def is_contained(m):
            return text.lower() in m.content
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, is_contained)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @clear.command(aliases= ['mentions'])
    async def mention(self, ctx, count: int):
        await ctx.channel.trigger_typing()
        start= time()
        def has_mentions(m):
            return len(m.mentions) != 0
        await ctx.message.delete()
        deleted= await self.brokencl(ctx, count, has_mentions)
        end= time()
        embed= discord.Embed(
            title= f'Purged {deleted} messages',
            description= f'✅ Took me total of {round(end- start, 1)} seconds.',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after = 5.0)

    # clear till command, one of the unique feature.
    @commands.group(aliases= ['purgetill', 'deletetill'], invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_messages= True, manage_guild= True))
    @commands.guild_only()
    @commands.cooldown(2, 7, BucketType.guild)
    async def cleartill(self, ctx, userID: int= None):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            if userID:
                def check(m):
                    return userID == m.author.id
            else:
                def check(m):
                    return True
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, check, msg= msg)
        embed= discord.Embed(
            title= f'✅ Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @cleartill.command(aliases= ['bots'])
    async def bot(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            def is_a_bot(m):
                return m.author.bot
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, is_a_bot, msg= msg)
        embed= discord.Embed(
            title= f'✅ Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)
    @cleartill.command(aliases= ['users', 'humans', 'notbots'])
    async def user(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.message.reference:
            msg= ctx.message.reference.resolved
            def is_a_human(m):
                return not m.author.bot
        else:
            await ctx.send('You need to reply to the message while using command to purge messages after that message.')
            return
        await ctx.message.delete()
        deleted= await self.brokencltill(ctx, is_a_human, msg= msg)
        embed= discord.Embed(
            title= f'✅ Purged {deleted} messages',
            color= discord.Color.green()
        )
        await ctx.send(embed= embed, delete_after= 5.0)

    # ban command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.bot_has_permissions(ban_members= True)
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    async def ban(self, ctx, member: Union[discord.Member, discord.User], daysToDelete: Union[int, str]= '', *, reason= 'No reason given.'):
        if isinstance(daysToDelete, str):
            reason= daysToDelete+ ' ' + reason
            daysToDelete= 0
        if isinstance(daysToDelete, int):
            if daysToDelete> 7:
                daysToDelete= 7
        if isinstance(member, discord.Member):
            if (member == ctx.author):
                await ctx.send('You can\'t ban urself.')
                return
            if member.id == ctx.me.id:
                await ctx.send('You wanna ban me? Use other bot or do it urself u lazy human! :(')
                return
            if member.guild_permissions.administrator == True:
                await ctx.send('You can\'t ban an admin.')
                return
            if member.top_role.position >= ctx.author.top_role.position:
                await ctx.send('You doin\'t have permission to ban them.')
                return
            if member.top_role.position >= ctx.me.top_role.position:
                await ctx.send('I can\'t ban the mentioned user.')
                return
        embed= discord.Embed(
            title= 'U have been banned!',
            description= f'You have been banned from {ctx.guild.name}.',
            color= discord.Color.red(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Reason', value= reason)
        embed.set_footer(text= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_author(name= ctx.guild.name, icon_url= ctx.guild.icon_url)
        try:
            await member.send(embed= embed)
        except:
            pass
        await ctx.guild.ban(user= member, reason= reason, delete_message_days= daysToDelete)
        embed= discord.Embed(
            title= 'User Banned!',
            description= f'✅ Banned **{member.display_name}** and deleted all of their messages before {daysToDelete} days.',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)

    # Mass ban command
    @commands.command(aliases= ['multiban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.guild_only()
    @commands.cooldown(2, 20, BucketType.user)
    async def massban(self, ctx, userids: commands.Greedy[int], *, reason= None):
        await ctx.channel.trigger_typing()
        reason = reason or str(ctx.author)
        if not len(userids):
            await ctx.send('You need to provide me the ids of members whome u want to ban.')
            return
        elif len(userids) > 12:
            await ctx.send('Maximum of 12 memberIDs can be given in mass ban.')
        bans= await ctx.guild.bans()
        for id in userids:
            member= discord.Object(id)
            try:
                await ctx.guild.ban(user= member, reason= reason, delete_message_days= 0)
            except: pass
        afterbans= set(await ctx.guild.bans()) - set(bans)
        afterbans= list(afterbans)
        membannedids= []
        successtext= ''
        for i in range(0, len(afterbans)):
            successtext+= f'{afterbans[i][1].name} - ({afterbans[i][1].id})\n'
            membannedids.append(afterbans[i][1].id)
        failed= list(set(userids)- set(membannedids))
        embed= discord.Embed(
            title= f'Mass banned {len(afterbans)} people!',
            description= f'With reason {reason}',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Succesfull!', value= successtext if len(successtext)>0 else 'No success lmao', inline= False)
        embed.add_field(name= 'Failed!', value= '\n'.join(map(str, failed))) if failed else None
        await ctx.send(embed= embed)

    # Mass Unban
    @commands.command(aliases= ['multiunban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.guild_only()
    @commands.cooldown(2, 20, BucketType.user)
    async def massunban(self, ctx, userids: commands.Greedy[int], *, reason= None):
        await ctx.channel.trigger_typing()
        reason = reason or str(ctx.author)
        if not len(userids):
            await ctx.send('You need to provide me the ids of members whome u want to ban.')
            return
        elif len(userids) > 12:
            await ctx.send('Maximum of 12 memberIDs can be given in mass ban.')
        bans= await ctx.guild.bans()
        for id in userids:
            member= discord.Object(id)
            try:
                await ctx.guild.unban(user= member, reason= reason)
            except: pass
        afterbans= set(bans)- set(await ctx.guild.bans())
        afterbans= list(afterbans)
        membannedids= []
        successtext= ''
        for i in range(0, len(afterbans)):
            successtext+= f'{afterbans[i][1].name} - ({afterbans[i][1].id})\n'
            membannedids.append(afterbans[i][1].id)
        failed= list(set(userids)- set(membannedids))
        embed= discord.Embed(
            title= f'Mass unbanned {len(afterbans)} people!',
            description= f'With reason {reason}',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Succesfull!', value= successtext if len(successtext)>0 else 'No success lmao', inline= False)
        embed.add_field(name= 'Failed!', value= '\n'.join(map(str, failed))) if failed else None
        await ctx.send(embed= embed)

    # Temp ban command
    @commands.command(aliases= ['tban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.guild_only()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.cooldown(2,15, BucketType.user)
    async def tempban(self, ctx, member: discord.Member, time: str, *, reason: str= None):
        reason= reason or str(ctx.author)
        time= self.convert(time)
        if time< 300:
            await ctx.send('Tempbans below 5 mins are considered to be troll tempbans, pls retry with proper duration.')
            return
        id= member.id
        await self.ban(ctx, member, reason+f'with temp ban that will expire after {self.client.timeconv(time)}')
        vals= {
            'user_id': id,
            'guild_id': ctx.guild.id,
            'timestamp': int(datetime.datetime.utcnow().timestamp()+time)
        }
        await self.client.db.table['tempbans'].upsert(**vals)

    # Soft ban
    @commands.command(aliases= ['sban'])
    @commands.bot_has_permissions(ban_members= True)
    @commands.guild_only()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.cooldown(2,15, BucketType.user)
    async def softban(self, ctx, member: discord.Member, *, reason: str= None):
        reason= reason or str(ctx.author)
        id= member.id
        await self.ban(ctx, member, 7, reason+' with soft ban.')
        try:
            await ctx.guild.unban(discord.Object(id), reason= f'It was a soft ban by {ctx.author}')
        except:
            pass

    # Mute command
    @commands.command(aliases= ['shut'])
    @commands.bot_has_permissions(manage_roles= True)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_roles= True))
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    async def mute(self, ctx, member: discord.Member, time: str= None, *, reason= None):
        reason= reason or str(ctx.author)
        if member == ctx.author:
            await ctx.send('You can\'t mute urself.')
            return
        if member.id == ctx.me.id:
            await ctx.send('You wanna mute me? Use other bot or do it urself u lazy human! :(')
            return
        if member.guild_permissions.administrator == True:
            await ctx.send('You can\'t mute an admin.')
            return
        if member.top_role.position >= ctx.author.top_role.position:
            await ctx.send('You doin\'t have permission to mute them.')
            return
        if member.top_role.position >= ctx.me.top_role.position:
            await ctx.send('I can\'t mute the mentioned user.')
            return
        muterole= await self.client.db.tables['guildsettings'].select('muterole_id',where= {'guild_id': ctx.guild.id})
        muterole= muterole[0]['muterole_id']
        if muterole == None or muterole == 'NULL':
            await ctx.send('Muterole isn\'t setuped in this guild, use `muterole` command to setup a mute role.')
            return
        try:
            muterole= discord.Object(int(muterole))
            await member.add_roles(muterole, reason= reason)
        except:
            await ctx.send('I was unable to add role, maybe because the mute role is above my role or mute role was deleted.')
        time= self.convert(time) if time else None
        if time != None:
            if time > 1209600:
                await ctx.send("Mute duration cant be more then 14 days.")
            if time < 10:
                await ctx.send('Time can\'t be less than 10 seconds.')
        embed= discord.Embed(
            title= 'Muted!',
            description= f'Muted **{member.display_name}** with reason *{reason}*',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Duration of mute', value= self.client.timeconv(time)) if time else None
        await ctx.send(embed= embed)
        if time != None:
            self.client.mutemem.append((member, datetime.datetime.utcnow().timestamp()+time))

    # Unmute command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_roles= True))
    @commands.bot_has_permissions(manage_roles= True)
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    async def unmute(self, ctx, member: discord.Member):
        muterole= await self.client.db.tables['guildsettings'].select('muterole_id',where= {'guild_id': ctx.guild.id})
        muterole= muterole[0]['muterole_id']
        try:
            await member.remove_roles(discord.Object(int(muterole)), reason= f'{ctx.author} Unmuted.')
        except:
            await ctx.send('I\'m unable to remove the mute role.')
        embed= discord.Embed(
            title= 'Unmuted!',
            description= f'Unmuted **{member.display_name}**',
            color= discord.Color.green(),
            timestamp= datetime.datetime.utcnow()
        )
        await ctx.send(embed= embed)

    # kick command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(kick_members= True))
    @commands.bot_has_permissions(kick_members= True)
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    async def kick(self, ctx, member: discord.Member, *, reason= 'No reason given.'):
        if member == ctx.author:
            await ctx.send('You can\'t kick urself.')
            return
        if member.id == ctx.me.id:
            await ctx.send('Goodbye? You forgot what I did for u? :(')
            return
        if member.guild_permissions.administrator == True:
            await ctx.send('You can\'t kick an admin.')
            return
        if member.top_role.position >= ctx.author.top_role.position:
            await ctx.send('You dont have permission to ban them.')
            return
        if member.top_role.position >= ctx.me.top_role.position:
            await ctx.send('I don\'t have permission to ban them.')
        await ctx.guild.kick(user= member, reason= reason)
        embed= discord.Embed(
            title= 'U have been kicked!',
            description= f'You have been kicked from {ctx.guild.name}.',
            color= discord.Color.red(),
            timestamp= datetime.datetime.utcnow()
        )
        embed.add_field(name= 'Reason', value= reason)
        embed.set_footer(text= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.set_author(name= ctx.guild.name, icon_url= ctx.guild.icon_url)
        try:
            await member.send(embed= embed)
        except:
            pass
        embed= discord.Embed(
            title= 'User kicked!',
            description= f'✅ kicked **{member.display_name}**',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)

    # unban command
    @commands.command()
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(ban_members= True))
    @commands.bot_has_permissions(ban_members= True)
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    async def unban(self, ctx, userID: int, *, reason= "No reason given."):
        bans= await ctx.guild.bans()
        user= discord.Object(id= userID)
        await ctx.guild.unban(user= user, reason= reason)
        afterbans= await ctx.guild.bans()
        user= set(bans)- set(afterbans)
        user= list(user)
        user= user[0]
        embed= discord.Embed(
            title= 'User Unbanned!',
            description= f'✅ Unbanned **{user[1].name}**',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)

    # warn command
    @commands.command(aliases= ['redcard'],
        help= "Warns the user. You can optionaly pass time like `1d12h30m30s` which is max at 14 days, u can alse pass count to amount of warnings to add",
        description= "If user crosses the `kickat` or `banat` amount of warnings, they will be treeted",
        usage= "<member> [reason]\nOR\n<member> [count < 10] [reason]")
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    @commands.check_any(commands.check(has_modrole), commands.has_permissions(manage_guild= True))
    async def warn(self, ctx, member: discord.Member, count: Union[int, str]= 1, reason: str= None):
        if isinstance(count, str):
            reason= count + (reason if reason else None)
            count= 1
        if not reason:
            reason= "No reason was given"
        if count>= 10: return await ctx.send('U can warn a member upto 10 times per command usage.')
        raw= await self.client.db.tables['guildsettings'].select('warns', 'banat', 'kickat', where= {'guild_id': ctx.guild.id})
        warnings= raw[0]['warns']
        banat= raw[0]['banat']
        kickat= raw[0]['kickat']
        if member.id in warnings.keys():
            warns= warnings[member.id]
        else:
            warns= 0
        warns+= count
        warnings.update({member.id: warns})
        if warns >= banat and banat != 0:
            try:
                await ctx.guild.ban(member, reason= f'{ctx.author} warned, and they crossed banat limit.', days_to_delete= 0)
                embed= discord.Embed(
                    title= 'Banned',
                    description= 'They have been banned for crossing `banat` limit.',
                    color= discord.Color.green()
                )
                embed.add_field(name= 'Reason', value= reason)
                await ctx.send(embed= embed)
                return
            except:
                await ctx.send('They crossed the banat, but I m unable to ban them..')
                return
        elif warns >= kickat and kickat != 0:
            try:
                await ctx.guild.kick(member, reason= f'{ctx.author} warned, and they crossed kickat limit.')
                embed= discord.Embed(
                    title= 'Kicked',
                    description= 'They have been kicked for crossing `kickat` limit.',
                    color= discord.Color.green()
                )
                embed.add_field(name= 'Reason', value= reason)
                await ctx.send(embed= embed)
                return
            except:
                await ctx.send('They crossed the kickat, but I m unable to kick them..')
                return
        vals= {'warns': warnings}
        await self.client.db.tables['guildsettings'].update(**vals, where= {'guild_id': ctx.guild.id})
        embed= discord.Embed(
            title= 'Warned',
            description= f'**{member}** has been warned. They have `{warns}` warns now.',
            color= discord.Color.green()
        )
        embed.add_field(name= 'Reason', value= reason)
        await ctx.send(embed= embed)
        channel= await self.client.modlogch(ctx.guild)
        if not channel: return
        embed= discord.Embed(
            title= 'Member Warned!',
            description= f'{member} was warned by moderator **{ctx.author}**',
            color= discord.Color.red()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        embed.add_field(name= 'Reason', value= reason)
        await channel.send(embed= embed)

    # A command to give or remove role from members.
    @commands.group(aliases= ['yum'], invoke_without_command= True)
    @commands.guild_only()
    @commands.cooldown(2, 10, BucketType.guild)
    @commands.bot_has_guild_permissions(manage_roles= True)
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_roles= True))
    async def role(self, ctx):
        await ctx.send_help(ctx.command)
    @role.command(name= 'add', aliases= ['give', 'plus', '+'])
    async def _add(self, ctx, member: discord.Member, role: discord.Role):
        try:
            member.add_roles(role, reason= f'My master {ctx.author} told me.')
        except:
            if role.position > ctx.me.top_role.position:
                await ctx.send('`Failed` to give the role, `Role above me`')
            elif role.is_bot_managed():
                await ctx.send('`Failed` to give the role, `Role is managed by a bot`')
            elif role.is_default():
                await ctx.send('`Failed` to give the role, `Role is default role, they already have it`')
            elif role.is_premium_subscriber():
                await ctx.send('`Failed` to give the role, `Role is a nitro booster role`')
            elif role.is_integration():
                await ctx.send('`Failed` to give the role, `Role is managed by some integration`')
            else:
                await ctx.send('Can\'t add the role')
            return
        embed= discord.Embed(
            title= 'Role was added!',
            description= f'{role.mention} was given to {member.mention}',
            color= role.color if role.color != discord.Color.default() else discord.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)
    @role.command(name= 'remove', aliases= ['rem', 'minus', '-', 'take'])
    async def _remove(self, ctx, member: discord.Member, role: discord.Role):
        try:
            member.remove_roles(role, reason= f'My master {ctx.author} told me.')
        except:
            if role.position > ctx.me.top_role.position:
                await ctx.send('`Failed` to remove the role, `Role above me`')
            elif role.is_bot_managed():
                await ctx.send('`Failed` to remove the role, `Role is managed by a bot`')
            elif role.is_default():
                await ctx.send('`Failed` to remove the role, `Role is default role, they already have it`')
            elif role.is_premium_subscriber():
                await ctx.send('`Failed` to remove the role, `Role is a nitro booster role`')
            elif role.is_integration():
                await ctx.send('`Failed` to remove the role, `Role is managed by some integration`')
            else:
                await ctx.send('Can\'t remove the role')
            return
        embed= discord.Embed(
            title= 'Role was removed!',
            description= f'{role.mention} was removed {member.mention}',
            color= role.color if role.color != discord.Color.default() else discord.green()
        )
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)

def setup(client):
    client.add_cog(Moderation(client))