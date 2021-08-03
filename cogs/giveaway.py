import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta
import re

class Giveaways(commands.Cog):
    def __init__(self, client):
        self.client= client
        self.client.loop.create_task(self.loopstarter())

    print("Giveaway.py has been loaded\n-----------------------------------")

    async def loopstarter(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(5)
        self.giveaway_handler.start()
        print('Started Giveaway loop in Giveaways.py')

    # Checking for disabled commands and Blacklisted channels
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= self.client.cache.get(ctx.guild.id, {"discmds":[], "blackch":[]})
        blackch, discmds= discmds['blackch'],discmds['discmds']
        if not discmds and not blackch:
            return True
        else:
            return not ctx.command.name in discmds and not ctx.channel.id in blackch

    def convert(self, time):
        time_regex= re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
        time_dict= {"h": 3600, "s": 1, "m": 60, "d": 86400}
        time= time.lower()
        matches= re.findall(time_regex, time)
        time= 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
                raise commands.BadArgument(f"{value} is an invalid time key! h|m|s|d are valid arguments")
            except ValueError:
                raise commands.BadArgument(f"{key} is not a number!")
        return round(time)

    # Custom Check if user can moderate with the power of modrole
    async def has_modrole(ctx):
        modrole= await ctx.bot.db.fetchval('SELECT modrole_id FROM guildsettings WHERE guild_id= $1', ctx.guild.id)
        if not modrole:
            return False
        try:
            return await commands.has_role(int(modrole)).predicate(ctx)
        except:
            return False

    @tasks.loop(seconds= 20)
    async def giveaway_handler(self):
        giveaways= await self.client.db.fetch(f'DELETE FROM giveaways WHERE timestamp < {int(datetime.utcnow().timestamp())} RETURNING *')
        for giveaway in giveaways:
            channel= self.client.get_channel(giveaway['channel_id'])
            if not channel:
                continue
            try:
                msg= await channel.fetch_message(giveaway['message_id'])
                if not msg: continue
            except:
                continue
            users= await msg.reactions[0].users().flatten()
            users.pop(users.index(self.client.user))
            if len(users) == 0:
                em= discord.Embed(title= 'Giveaway Failed', color= discord.Color.default())
                em.add_field(name= "Reason", value= "No one reacted in time!")
                await msg.channel.send(embed= em)
                continue
            winners= ""
            wincount= giveaway['winner_count']
            prize= giveaway['prize']
            for i in range(0, wincount):
                if len(users) == 0:
                    break
                winner= random.choice(users)
                users.remove(winner)
                winners += f"{winner.mention}, "

            # edit embed to show winner
            newembed= discord.Embed(title= "Giveaway Ended!", description= f"{prize}", timestamp= datetime.utcnow())
            newembed.add_field(name= "Winner", value= f"{winners[:-2]}")
            newembed.set_footer(text= f"Ended ", icon_url="https://qotoqot.com/sad-animations/img/400/shy/shy.gif")
            try:
                await msg.edit(embed= newembed)
                await msg.reply(f"Congratulations! {winners[:-2]} won **{prize}**!",
                    allowed_mentions= discord.AllowedMentions(everyone= False, roles= False, users= True, replied_user= False))
            except: continue

    # Lmao this is the Biggest command, Yet efficient.
    @commands.command(aliases= ['giveaway', 'ga'],
        help= 'Start a giveaway in a channel where I have permission to embed links.',
        description= 'You would require ')
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_channels= True, manage_guild= True))
    @commands.guild_only()
    async def gstart(self, ctx):
        guild_gways= await self.client.db.fetchval('SELECT COUNT(guild_id) FROM giveaways WHERE guild_id= $1', ctx.guild.id)
        if guild_gways>= 8:
            return await ctx.send('There are already 8 giveaways running in the current guild. Tarry there.')

        questions= ["Which channel should it be hosted in?",
                    "What should be the duration of the giveaway? (s|m|h|d)\nMin: `31s`",
                    "What is the prize of the giveaway?",
                    "Tell me how many winners u want to have?",
                    "What role to mention? You can mention the role/give the roleid.\n`skip` to send without mentions"]

        answers= []
        Questions : discord.Message= await ctx.send("Starting...")

        for i in questions:
            embed= discord.Embed(title= "Starting a giveaway!", description= i, color= discord.Color.blurple() if ctx.me.color == discord.Color.default() else ctx.me.color)
            embed.set_footer(text= "Alternatively type `Stop` to cancel command")
            await Questions.edit(content= "Let's start with this giveaway! Answer these questions within 60 seconds!",embed= embed)

            try:
                msg= await self.client.wait_for('message', 
                    timeout= 60.0, 
                    check= lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id)
                if msg.content.lower() == "stop":
                    await ctx.send(":x: Giveaways Cancelled")
                    await Questions.edit(content= "Stopped!")
                    return
            except asyncio.TimeoutError:
                await ctx.send(':x: Giveaways Cancelled')
                return
            else:
                answers.append(msg.content)
        
        try:
            channel= await commands.TextChannelConverter().convert(ctx, answers[0])
            if channel.guild.id != ctx.guild.id:
                raise Exception
        except:
            return await ctx.send('No channel was found.')
        time= self.convert(answers[1])
        if time <= 30 or time >= 1209600:
            await ctx.send(f"Time can't be `{time}`, it should be a value greater then 30s and less than 14d.")
            return
        prize= answers[2]
        try:
            wincount= int(answers[3])
            if wincount <1:
                raise Exception
        except:
            return await ctx.send('Invalid winner count.')
        a= answers[4]
        if a != 'skip':
            mentionrole= ""
            for i in a:
                try:
                    if int(i) in range(0,10):
                        mentionrole += i
                except:
                    pass
            if len(mentionrole) == 18:
                mentionrole= f"<@&{mentionrole}>"
            else:
                mentionrole= u"\u200B"
        else:
            mentionrole= u"\u200B"
        
        # send a message for the user to know the giveaway started!
        confembed= discord.Embed(
            title= "Giveaway started!",
            description= f"Giveaway started at {channel.mention} and will last `{self.client.timeconv(time)}` seconds!",
            color= discord.Color.blurple())
        await Questions.edit(content= "", embed= confembed)
        # now send the embed in the channel!
        embed= discord.Embed(title= "Giveaway!", description= prize, color= ctx.guild.me.color, timestamp= datetime.utcnow())
        embed.add_field(name= "Hosted by:", value= ctx.author.mention)
        end_time= datetime.utcnow() + timedelta(seconds= time)
        embed.add_field(name= "Ends at:", value= f'<t:{int(end_time.timestamp())}:F>\n<t:{int(end_time.timestamp())}:R>')
        embed.set_footer(text= f"Started at ", icon_url='https://images-ext-1.discordapp.net/external/ZaAMSwxiAFN_-cRIFkr6uHHNITfAPsE9SFRm_RRVCfQ/https/cdn.discordapp.com/emojis/724135911331463279.gif')
        try:
            my_msg= await channel.send(mentionrole, embed= embed,
                allowed_mentions= discord.AllowedMentions(everyone= True, roles= True, users= False, replied_user= False))
            await my_msg.add_reaction('🎉')
        except:
            return await ctx.send(f"I don't have enough permissions in {channel.mention}, pls give me `embed links`, `add reactions`, `send_messages`, `read messages`.")
        await self.client.db.execute('INSERT INTO giveaways (\
                winner_count,\
                message_id,\
                timestamp,\
                prize,\
                guild_id,\
                channel_id\
            )\
            VALUES ($1, $2, $3, $4, $5, $6);', wincount, my_msg.id, int(end_time.timestamp()), prize, ctx.guild.id, channel.id)

    @commands.command(aliases= ['gr'])
    @commands.check_any(commands.check(has_modrole), commands.has_guild_permissions(manage_channels= True, manage_guild= True))
    @commands.guild_only()
    async def reroll(self,ctx, messageid : int, channel: discord.TextChannel= None):
        channel= channel or ctx.channel
        try:
            msg= await channel.fetch_message(messageid)
        except:
            raise commands.MessageNotFound(f'`{messageid}` in {channel.mention}')

        users= await msg.reactions[0].users().flatten()
        users.pop(users.index(self.client.user))

        winner= random.choice(users)
        await channel.send(f"Congratulations! The new winner is {winner.mention}!")

    @commands.command(aliases= ['glist', 'gs'])
    @commands.guild_only()
    async def giveaways(self, ctx):
        guild_gways= await self.client.db.fetch('SELECT * FROM giveaways WHERE guild_id= $1', ctx.guild.id)
        if len(guild_gways) == 0:
            await ctx.send('There are no giveaways running in this server. Use `gstart` command to start a giveaway.')
            return
        embed= discord.Embed(
            title= 'Giveaways.',
            description= f'There are {len(guild_gways)} giveaway running in the server' if len(guild_gways)>1 else 'There is one gievaway running in the server.',
            color= ctx.me.color
        )
        msgurl_format= 'https://discord.com/channels/'
        for gway in guild_gways:
            embed.add_field(name= f"Expires IN: `{self.client.timeconv(gway['timestamp']-datetime.utcnow().timestamp())}`",
                value= f"Winner Count= **{gway['winner_count']}**\nPrize= {gway['prize']}\n[\`\`Jump``]({msgurl_format}/{gway['guild_id']}/{gway['channel_id']}/{gway['message_id']})",
            )
        await ctx.send(embed= embed)

def setup(client):
    client.add_cog(Giveaways(client))