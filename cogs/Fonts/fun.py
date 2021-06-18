import asyncio, aiohttp, json, re
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import discord
from datetime import datetime
from akinator.async_aki import Akinator
import os, pathlib
from discord.ext.commands.cooldowns import BucketType
from twemoji_parser import TwemojiParser
from random import choice
from art import text2art
from py_expression_eval import Parser
import wikipedia
from urllib.request import urlretrieve

class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client

    
    animals= ['dog', 'cat', 'fox', 'bird']
    langs= {
        'ga': 'Irish', 'sq': 'Albanian', 'it': 'Italian', 'ar': 'Arabic', 'ja': 'Japanese',
        'az': 'Azerbaijani', 'kn': 'Kannada', 'eu': 'Basque', 'ko': 'Korean', 'bn': 'Bengali',
        'la': 'Latin', 'be': 'Belarusian', 'lv': 'Latvian', 'bg': 'Bulgarian', 'lt': 'Lithuanian',
        'ca': 'Catalan', 'mk': 'Macedonian', 'zh-CN': 'Chinese Simplified', 'ms': 'Malay',
        'zh-TW': 'Chinese Traditional', 'mt': 'Maltese', 'hr': 'Croatian', 'no': 'Norwegian',
        'cs': 'Czech', 'fa': 'Persian', 'da': 'Danish', 'pl': 'Polish', 'nl': 'Dutch',
        'pt': 'Portuguese', 'en': 'English', 'ro': 'Romanian', 'eo': 'Esperanto', 'ru': 'Russian',
        'et': 'Estonian', 'sr': 'Serbian', 'tl': 'Filipino', 'sk': 'Slovak', 'fi': 'Finnish',
        'sl': 'Slovenian', 'fr': 'French', 'es': 'Spanish', 'gl': 'Galician', 'sw': 'Swahili',
        'ka': 'Georgian', 'sv': 'Swedish', 'de': 'German', 'ta': 'Tamil', 'el': 'Greek', 'te': 'Telugu',
        'gu': 'Gujarati', 'th': 'Thai', 'ht': 'Haitian Creole', 'tr': 'Turkish', 'iw': 'Hebrew',
        'uk': 'Ukrainian', 'hi': 'Hindi', 'ur': 'Urdu', 'hu': 'Hungarian', 'vi': 'Vietnamese',
        'is': 'Icelandic', 'cy': 'Welsh', 'id': 'Indonesian', 'yi': 'Yiddish'}

    print("Fun.py has been loaded\n-----------------------------------")

    # Checking for disabled commands
    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        discmds= await self.client.db.tables['guildsettings'].select('discmds', where= {'guild_id': ctx.guild.id})
        try:
            return not ctx.command.name in discmds[0]['discmds']
        except: return True

    @commands.command(
        aliases= ["snap"],
        help= "Make a fake discord message snap to troll ur friends.",
        description= "U may use user id/mention if u don't want member not found error.",
        usage= '<user> <Text>')
    @commands.cooldown(2, 30, BucketType.user)
    @commands.guild_only()
    async def mimic(self, ctx, member : discord.Member, *, message):
        if len(message)>500:
            await ctx.send('This is not accepted, word limit is 500 characters.')
            return
        async with ctx.channel.typing():
            if member == None:
                member = ctx.author
            
            colour = {
                "time": (114, 118, 125),
                "content": (220, 221, 222)
            }

            font = str(pathlib.Path(__file__).parent.absolute()/"fonts"/"whitney"/"whitneymedium.otf")
            img = Image.new('RGB', (500, 115), color = (54,57,63))
            titlefnt = ImageFont.truetype(font, 20)
            timefnt = ImageFont.truetype(font, 13)
            parser = TwemojiParser(img, parse_discord_emoji=True)
            uname = member.display_name
            color = member.color.to_rgb()
            if color == (0, 0, 0):
                color = (255,255,255)
            await parser.draw_text((90, 20), uname, font=titlefnt, fill=color)
            h, w = await parser.getsize(uname, font=titlefnt)
            time = datetime.utcnow().strftime("Today at %H:%M")
            await parser.draw_text((90+h-15, 25), time, font=timefnt, fill=colour["time"])
            await parser.draw_text((90, 25+w), message, font=titlefnt, fill=colour["content"])
            img.save('img.png')
            if member.is_avatar_animated():
                await member.avatar_url_as().save("pfp.gif")
                f2 = Image.open("pfp.gif")
            else:
                await member.avatar_url_as().save("pfp.png")
                f2 = Image.open("pfp.png")
            f1 = Image.open("img.png")
            f2.thumbnail((50, 55))
            f2.save("pfp.png")

            f2 = Image.open("pfp.png").convert("RGB")

            mask = Image.new("L", f2.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, f2.size[0]-1, f2.size[1]-1), fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(0))

            result = f2.copy()
            result.putalpha(mask)

            result.save("pfp.png")

            f2 = Image.open("pfp.png")

            f3 = f1.copy()
            f3.paste(f2, (20, 20), f2)
            f3.save("img.png")

            file = discord.File("img.png")
            await ctx.send(file=file)

            try:
                os.remove("pfp.gif")
                os.remove("pfp.png")
                os.remove("img.png")
            except:
                pass

    @commands.command(
        aliases= ["weath","temperature","forecast"],
        help= "May be slightly inaccurate.",
        description= "Display weather of the provided place.",
        usage= '<Place Name>')
    @commands.cooldown(2, 60, BucketType.user)
    @commands.guild_only()
    async def weather(self, ctx, place):
        async with aiohttp.ClientSession() as cs:
            url = "https://api.openweathermap.org/data/2.5/weather?q="+place+"&appid=ebe2fbc4698f167aed9a6871d3792426"
            async with cs.get(url) as response:
                response = await response.json()
                if response["cod"] == "404":
                    await ctx.send(f"Either api not responding or I can't fetch weather report of __{place.capitalize()}__. Make sure u type exect name, case doesn't matter, no spaces", delete_after= 15.0)
                    return
                weather = response['main']
                embed = discord.Embed(title= f"Weather report of {place.capitalize()}", description= f"{response['weather'][0]['main']} > {response['weather'][0]['description']}", color= ctx.me.color)
                embed.add_field(name= "Temperature", value= f"Feels like: **{round(weather['temp'] - 273.16),1}°C** ({round(weather['temp_min'] - 273.16, 2)} / {round(weather['temp_max'] - 273.16, 2)})", inline=False)
                embed.add_field(name= "Pressure", value= str(weather['pressure']), inline=True)
                embed.add_field(name= "Humidity", value= str(weather['humidity']), inline=True)
                embed.add_field(name= "Winds", value= f"{response['wind']['speed']}M/h along {response['wind']['deg']}°", inline=True)
                embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{response['weather'][0]['icon']}.png")
                await ctx.send(embed= embed)
    
    @commands.command(
        aliases= ["word"],
        help="Word must belong to ENGLISH dictionary!",
        description="Defines a words with proper examples.")
    @commands.cooldown(5, 60, BucketType.user)
    @commands.guild_only()
    async def define(self, ctx, word : str):
        async with ctx.channel.typing():
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as response:
                    response = await response.json()
                    try:
                        if response['title'] == "No Definitions Found":
                            await ctx.send("No such word found in english dictionary.", delete_after= 10.0)
                            return
                    except:
                        pass
                    desc = ""
                    response = response[0]
                    try:
                        desc = f"Origin : __(say: _{response['phonetics'][0]['text']}_)__ {response['origin']}"
                    except:
                        desc = "Origin : `No Origin Found.`"
                    embed = discord.Embed(
                        title= word.capitalize(),
                        description= desc,
                        color= ctx.me.color)
                    i= 4
                    synonyms = []
                    for meaning in response['meanings']:
                        if i == 0:
                            break
                        i -= 1
                        value= ""
                        for definition in meaning['definitions']:
                            value += "'"+definition['definition']+"'" + "\n"
                            try:
                                value += "`eg.` " + f"_{definition['example']}_\n"
                            except:
                                pass
                            try:
                                synonyms += definition['synonyms']
                            except:
                                pass
                        embed.add_field(name= meaning['partOfSpeech'].capitalize(), value= value)
                    synonyms = list(set(synonyms))
                    syntext = "`No synonyms for this word``"
                    i = 0
                    for syn in synonyms:
                        if i == 0:
                            syntext = ""
                        if i == 15:
                            break
                        i += 1
                        syntext += f"`{syn}` "
                    embed.add_field(name= "Synonyms", value= syntext[:-1])
                    await ctx.send(embed=embed)
    
    @commands.command(
        aliases= ['pinpoint', 'whereis'],
        help="Pinpoint ur CITY in the map",
        description="Make sure this map only and only works with cities and other small areas, also this command is kinda beta so inaccuracy will be there far u go from equator.")
    @commands.cooldown(2, 60, BucketType.user)
    @commands.guild_only()
    async def locate(self, ctx, *, place):
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://geocode.xyz/{place}?json=1') as response:
                img = Image.open("worldmap.png")
                parser = TwemojiParser(img)
                response = await response.json()
                try:
                    await ctx.send(response['error']['description'][2:])
                    return
                except:
                    pass
                long = round(float(response['longt']),2)
                lat = round(float(response['latt']),2)
                try:
                    country = response['standard']['countryname']
                except:
                    country = "`No country found.`"
                lo = long
                la = lat
                if long > 0:
                    lo -= long/8
                else:
                    lo += long/7
                if lat > 0:
                    la += lat/5
                else:
                    la -= lat/5
                x =int(360.00 + (2*lo))
                y =int(180.00 - (2*la))
                font = str(pathlib.Path(__file__).parent.absolute()/"fonts"/"whitney"/"whitneymedium.otf")
                pinfont = ImageFont.truetype(font, 15)
                await parser.draw_text((x, y-4), '📍', pinfont)
                img.save('img.png')
                file = discord.File('img.png')
                await ctx.send(f"Longitude: {long}\nLatitude: {lat}\nCountry: {country}", file= file)

    @commands.command(
        aliases= ["haha", "lmao"],
        help="Summon a ahh a joke!",
        description="Jokes can be one part or two part, if two part u need to react in order to see the next part of joke. Alright?")
    @commands.cooldown(5, 60, BucketType.user)
    @commands.guild_only()
    async def joke(self, ctx):
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist') as response:
                response= await response.json()
                if response['error']:
                    await ctx.send(f"API raised an error: `{response['message']}`")
                if response['type'] == 'single':
                    embed= discord.Embed(title= response['category'], description= response['joke'], color= ctx.me.color)
                    await ctx.reply(embed= embed)
                else:
                    embed= discord.Embed(title= response['category'], description= response['setup'], color= ctx.me.color)
                    msg : discord.Message= await ctx.reply(embed= embed)
                    await msg.add_reaction(emoji= '👀')
                    def check(r, u):
                        return r.message == msg and str(r.emoji) == '👀' and u == ctx.author
                    try:
                        await self.client.wait_for('reaction_add', 
                            timeout= 30.0,
                            check= check)
                    except:
                        pass
                    embed.set_footer(text= response['delivery'])
                    await msg.edit(embed=embed)

    @commands.command(
        aliases= ['memes', 'lol'],
        help="Presents u a meme.",
        description="A random freshy meme from some top subreddits.")
    @commands.cooldown(5, 60, BucketType.user)
    @commands.guild_only()
    async def meme(self, ctx):
        reddit = choice(['MemeEconomy', 'ComedyCemetery', 'memes', 'dankmemes', 'PrequelMemes', 'terriblefacebookmemes', 'funny', 'teenagers', 'watchpeopledieinside'])
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://meme-api.herokuapp.com/gimme/{reddit}") as response:
                response = await response.json()
                meme= discord.Embed(
                    title= f"r/{response['subreddit']}",
                    url= response['postLink'],
                    description= response['title'], color= discord.Color.orange())
                meme.set_author(
                    name= f"Posted by u/{response['author']}",
                    icon_url= "https://styles.redditmedia.com/t5_3kper/styles/profileIcon_snoo3e112319-987c-49e7-9dde-8858d422c529-headshot.png?width=256&height=256&crop=256:256,smart&s=e2f86a3a77245b62cf3b3f90f6de786ab0451bee",
                    url= f"https://www.reddit.com/user/{response['author']}")
                meme.set_footer(
                    icon_url="https://i.redd.it/b9zcqp6w31w51.jpg",
                    text= response['ups'])
                meme.set_image(url= response['preview'][-1])
                await ctx.reply(embed= meme)
    
    @commands.command(
        aliases= ['subreddit', 'rddt'],
        help="Just a tip, subreddits dont have spaces",
        description="Summons a randome top fresh post from the given reddit(not case sensitive:3)")
    @commands.cooldown(5, 60, BucketType.user)
    @commands.guild_only()
    async def reddit(self, ctx, reddit):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://meme-api.herokuapp.com/gimme/{reddit}") as response:
                response = await response.json()
                try:
                    await ctx.send(f"**({response['code']})** {response['message']}")
                except KeyError:
                    pass
                meme= discord.Embed(
                    title= f"r/{response['subreddit']}",
                    url= response['postLink'],
                    description= response['title'], color= discord.Color.orange())
                meme.set_author(
                    name= f"Posted by u/{response['author']}",
                    icon_url= "https://bit.ly/3yyTE02",
                    url= f"https://www.reddit.com/user/{response['author']}")
                meme.set_footer(
                    icon_url="https://i.redd.it/b9zcqp6w31w51.jpg",
                    text= response['ups'])
                meme.set_image(url= response['preview'][-1])
                await ctx.reply(embed= meme)
    
    @commands.group(
        aliases= ['ani'], invoke_without_command=True,
        help="Cute animals.",
        description="Use this command with `list` argument to see list of animals u rquest for.")
    @commands.cooldown(8, 60, BucketType.user)
    @commands.guild_only()
    async def animal(self, ctx, animal: str= None):
        animal= animal or choice(self.animals)
        if not animal.lower() in self.animals:
            await ctx.send('Animal not listed.')
            return
        with open('{}/data/animals.json'.format(os.path.normpath(os.path.abspath(__file__)+'/'+'..'+'/'+'..'))) as animals:
            anim_dict= json.load(animals)
            anim_dict= choice(anim_dict[animal])# Same variable to save memory
            embed= discord.Embed(
                title= animal.capitalize(),
                color= discord.Color.blurple(),
            )
            embed.set_image(url= anim_dict)
            await ctx.send(embed=embed)
    @animal.command()
    async def list(self, ctx):
        desc= " **|** ".join(self.animals)
        emb= discord.Embed(title= "List of animals u can request image for.", description= desc, color= ctx.me.color)
        await ctx.send(embed= emb)
    
    @commands.group(
        aliases= ['tra'],
        help="Use 2 letter language code to translate the text to ur language.",
        description="Do .translate list to see the list of available languages with there code.")
    @commands.cooldown(10, 60, BucketType.user)
    @commands.guild_only()
    async def translate(self, ctx, lang = 'en', *, text = None):
        if not lang in self.langs.keys():
            text = lang + ' ' + text
            lang = 'en'
        async with aiohttp.ClientSession() as cs:
            async with cs.post(
                url= f'https://translate.googleapis.com/translate_a/single?client=gtx&ie=UTF-8&oe=UTF-8&sl=auto&tl={lang}&dt=t&q={text}') as response:
                response= await response.json()
                trans= response[0][0][0]
                await ctx.send(f'Language: {self.langs[lang]}\nDetect Language: {self.langs[response[2]]}\nTranslation: {trans}\n\n(Use `@UFO bot translate list` to see all supported languages.)')
    @translate.command(name= 'list')
    async def _list(self, ctx):
        desc = ""
        j= 0
        for i in self.langs.keys():
            desc += f'• `{i}`' + ' - ' + self.langs[i] + '|\t'
        embed = discord.Embed(title= "Supported Languages for translate command!", description= desc, color= ctx.me.color)
        await ctx.send(embed= embed)
        return

    @commands.command(
        aliases= ['txtart', 'ascii'],
        help="Converts the given text to a teact art.",
        description="I smell some copypastas.")
    @commands.guild_only()
    async def textart(self, ctx, *, text:str):
        if len(text) > 15:
            await ctx.send("You can't convert more then 15 letters to an ASCII art. Sorry abt that but its for preventing wall of message.")
            return
        text = text.replace(' ', '\n')
        art= text2art(text, font= 'rnd-medium', chr_ignore= True)
        await ctx.send(f'```fix\n{art}\n```')

    @commands.command(
        aliases= ['ttt', 'tic'],
        help="Mention the user or Give there user id or there nick name or user#discrim to challenge ur friend.",
        description="Starts a tictaktoe came against ur friend.")
    @commands.guild_only()
    async def tictaktoe(self, ctx, *, member2: discord.Member):
        if member2.bot:
            await ctx.send("U can't challenge a bot huh.")
            return
        member1= ctx.author
        msg : discord.Message= await ctx.send(f'{member2.mention}, tictaktoe challenge for u from {member1.mention}.')
        await msg.add_reaction('✔')
        await msg.add_reaction('❌')
        def check(r, u):
            return u.id==member2.id and r.emoji in ['✔','❌'] and r.message == msg

        try:
            r, m= await self.client.wait_for('reaction_add', timeout= 60, check= check)
            if r.emoji== '❌':
                await ctx.send(f"{ctx.author.mention} They denied ur request oof :/")
                await m.delete()
                return
        except asyncio.TimeoutError:
            await ctx.send(":x: Game Canceled.")
            return

        players= (member1, member2)
        theBoard = {'1': ' ' , '2': ' ' , '3': ' ' ,
                    '4': ' ' , '5': ' ' , '6': ' ' ,
                    '7': ' ' , '8': ' ' , '9': ' ' }
        board_keys = []
        for key in theBoard:
            board_keys.append(key)

        def printBoard(board : dict):
            for i in board.keys():
                if board[i] == ' ':
                    board.update({i : i})
            realb = board['1'] + ' | ' + board['2'] + ' | ' + board['3'] + '\n--+---+-- \n' + board['4'] + ' | ' + board['5'] + ' | ' + board['6'] + '\n--+---+-- \n' + board['7'] + ' | ' + board['8'] + ' | ' + board['9']
            return discord.Embed(description= f'```ml\n{realb}```')
        
        boardmsg = await ctx.send(embed = printBoard(theBoard))
        turnmsg = await ctx.send("Starting...")


        async def game():

            turn = 'X'
            count = 0


            while count < 10:
                player = players[count%2]
                await boardmsg.edit(embed= printBoard(theBoard))
                await turnmsg.edit(content= f"It is {player.mention}'s turn.")

                move = '0'

                for i in range(1, 10):
                    try:
                        movemsg = await self.client.wait_for(
                            'message', timeout= 30, check= lambda m: m.author.id == player.id and m.channel.id == ctx.channel.id)
                    except asyncio.TimeoutError:
                        await turnmsg.edit("Alrigth! I have other things to do too. :wave:")
                        return
                    move = movemsg.content
                    try:
                        await movemsg.delete()
                    except:
                        pass
                    if not move in theBoard.keys() or theBoard[move] in ['X', 'O']:
                        await ctx.send("Invalid input try again, enter the number of the box u wanna place ur turn.", delete_after= 5)
                        move = '0'
                        continue
                    break
                if move == '0':
                    print("Game Over. 3 invalid inputs!")
                    return
                theBoard[move] = turn
                count += 1

                if count >= 5:
                    if theBoard['7'] == theBoard['8'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['4'] == theBoard['5'] == theBoard['6'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['2'] == theBoard['3'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['4'] == theBoard['7'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['2'] == theBoard['5'] == theBoard['8'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['3'] == theBoard['6'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['7'] == theBoard['5'] == theBoard['3'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return
                    elif theBoard['1'] == theBoard['5'] == theBoard['9'] != ' ':
                        await ctx.send(f"Game Over!! {player.mention} takeaway the victory")
                        return

                if count == 9:
                    await ctx.send("\nGame Over!!\nIt's a Tie oof.")
                    return

                if turn == 'X':
                    turn = 'O'
                else:
                    turn = 'X'

        await game()

    @commands.command(
        aliases= ['echo'],
        help="Just a plane text.",
        description="Just copy paste what u pass.")
    @commands.guild_only()
    async def say(self, ctx, *, statement):
        if len(statement)> 120:
            await ctx.send('I m lazy to type that much, sorry.')
            return
        try:
            await ctx.message.delete()
        except:
            try:
                await ctx.message.add_reaction('✅')
            except:
                await ctx.reply(statement, mention_author= False)
                return
        statement= await commands.clean_content().convert(ctx, statement)
        await ctx.send(statement)

    @commands.command(
        aliases= ['aki'],
        help='Thonk of a character, I will try to guess it by questioning u. The answer must be one of these:\n\t- "yes" OR "y" OR "0" for YES\n\t- "no" OR "n" OR "1" for NO\n\t- "i" OR "idk" OR "i dont know" OR "i don\'t know" OR "2" for I DON\'T KNOW\n\t- "probably" OR "p" OR "3" for PROBABLY\n\t- "probably not" OR "pn" OR "4" for PROBABLY NOT\n\t- "b" OR "back" OR "5" to go back.\n\t- "c" OR "cancel" OR "6" to cancel.',
        description="Starts an Akinator game.")
    @commands.cooldown(1, 60, BucketType.user)
    @commands.guild_only()
    async def akinator(self, ctx):
        aki= Akinator()
        msg= await ctx.send('Thonk of a character, I will try to guess it by questioning u. The answer must be one of these:\n\t- "yes" OR "y" OR "0" for YES\n\t- "no" OR "n" OR "1" for NO\n\t- "i" OR "idk" OR "i dont know" OR "i don\'t know" OR "2" for I DON\'T KNOW\n\t- "probably" OR "p" OR "3" for PROBABLY\n\t- "probably not" OR "pn" OR "4" for PROBABLY NOT\n\t- "b" OR "back" OR "5" to go back.\n\t- "c" OR "cancel" OR "6" to cancel.')
        await msg.add_reaction('👌')
        def check(r, u):
            return str(r.emoji) == '👌' and u.id== ctx.author.id and r.message == msg
        def anscheck(m):
            return str(m.content.lower()) in ["yes", "y", "0", "no", "n", "1", "i", "idk", "i dont know", "i don't know", "2", "probably", "p", "3", "probably not", "pn", "4", "back", "b", "5", "cancel", "c", "6"]
        try:
            await self.client.wait_for('reaction_add', timeout= 5, check= check)
        except asyncio.TimeoutError:
            pass
        quesno= 1
        ques= await aki.start_game()
        lastmsg= ctx.message

        while aki.progression <= 80:
            embed= discord.Embed(description= f'`{quesno}.` {ques}', color= ctx.me.color)
            embed.set_footer(text= '"c" OR "cancel" OR "6" to cancel.')
            embed.set_author(icon_url= "https://static.wikia.nocookie.net/video-game-character-database/images/9/9f/Akinator.png/revision/latest/top-crop/width/360/height/450?cb=20200817020737", name= 'Akinator!')
            await lastmsg.reply(embed= embed)
            try:
                lastmsg= await self.client.wait_for('message', timeout= 45, check= anscheck)
            except asyncio.TimeoutError:
                await ctx.send(':x: Canceled akinator game.')
                return
            if lastmsg.content in ["cancel", "c", "6"]:
                await ctx.send(":x: Cancelled Akinator game. Thanks for playing.")
                return
            elif lastmsg.content in ["back", "b", "5"]:
                try:
                    q = await aki.back()
                    continue
                except:
                    await ctx.send("Can't go back at this point, sorry!")
                    continue
            ques= await aki.answer(lastmsg.content)
            if quesno > 39:
                await ctx.send("Akinator: Limit of 40 questions reached. Here is my guess so far.")
                break
            quesno+= 1
        await aki.win()

        endembed= discord.Embed(title= aki.first_guess['name'], description= aki.first_guess['description'], color= ctx.author.color)
        endembed.set_thumbnail(url= aki.first_guess['absolute_picture_path'])
        endembed.set_footer(text= f"I'm {round(float(aki.first_guess['proba'])*100, 1)}% sure.")
        endembed.set_author(icon_url= ctx.author.avatar_url, name= ctx.author)
        await ctx.send(embed= endembed)

    @commands.command(
        aliases=['eval', 'math'],
        help="Evaluate a mathematical expression.",
        description="Basic functions: + - / * % ^\nAdvanced: sin() cos() tan() log(a,b) asin() acos() atan() floor() round() abs() exp()")
    @commands.guild_only()
    async def solve(self, ctx, *, expression):
        parser = Parser()
        await ctx.send(f"{parser.parse(expression)} = **{parser.parse(expression).evaluate({})}**")

    @commands.command(
        aliases=['hug', 'ship'],
        help="User parameter must be mention/user#discrim/usernick/userid",
        description="Sends a image, ur pfp overlayed over the member's pfp.")
    @commands.cooldown(2, 60, BucketType.user)
    @commands.guild_only()
    async def cuddle(self, ctx, *, member: discord.Member):
        await ctx.channel.trigger_typing()
        await member.avatar_url_as(format= 'png').save("pfp1.png")
        await ctx.author.avatar_url_as(format= 'png').save("pfp2.png")
        pfp1= Image.open("pfp1.png").convert('RGB')
        pfp2= Image.open("pfp2.png").convert('RGB')
        pfp1= pfp1.resize((512, 512))
        pfp2= pfp2.resize((512, 512))
        result= ImageChops.overlay(pfp1, pfp2)

        result.save("hug.png")
        ship= f'{ctx.author.display_name[:-int(len(ctx.author.display_name)/2)]}{member.display_name[int(len(member.display_name)/2):]}'
        await ctx.send(f"**{ctx.author}** gave a sweet hug to **{member}**. As a restult **{ship}** was formed!!!",file= discord.File("hug.png"))

    @commands.command(aliases= ['wiki'],
        help= 'Pass the argument u want to search in wikipedia',
        description= 'You may get unexpected results, pls keep your query short and sweet.')
    @commands.cooldown(2, 30, BucketType.user)
    @commands.guild_only()
    async def wikipedia(self, ctx, *, query: str):
        await ctx.channel.trigger_typing()
        if len(query)> 20:
            await ctx.send('Query too long.. Pls only pass query below 20 letters.')
            return
        try:
            result= wikipedia.summary(query, chars= 1000)
        except wikipedia.DisambiguationError as error:
            try:
                opts= error.options[0:10] if len(error.options) > 10 else error.options
                dym= '\n'.join(opts)
                embed= discord.Embed(title= 'Page not found!',
                    description= f'*Do you mean?*\n{dym}')
                embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/d/de/Wikipedia_Logo_1.0.png')
                await ctx.send(embed= embed)
                return
            except:
                await ctx.send('Error occured! failed to find any wiki page related to that.')
                return
        except:
            await ctx.send('If you are seeing this, this error should hardly occur, pls report this in the support server so i can fix it.')
            return
        embed= discord.Embed(
            title= query.capitalize(),
            description= f'{result}[Continue reading.](https://en.wikipedia.org/wiki/Special:Search?search={query}&go=Go&ns0=1)',
            color= discord.Color.random()
        )
        embed.set_thumbnail(url= 'https://upload.wikimedia.org/wikipedia/commons/d/de/Wikipedia_Logo_1.0.png')
        embed.set_author(name= str(ctx.author), icon_url= ctx.author.avatar_url)
        await ctx.send(embed= embed)

    @commands.command(aliases= ['websnap', 'urlsnap', 'webss'],
        help= 'Sends a snapshot of a website as an embed, pass a crop value between 0-100 to make adjust the snap ratio.')
    @commands.cooldown(3, 30, BucketType.user)
    @commands.guild_only()
    async def webshot(self, ctx, url: str, crop: int= 50):
        await ctx.channel.trigger_typing()
        if not crop in range(0,101):
            await ctx.send('Crop can only be an integer in range 0-100')
            return
        crop= 12*crop
        reg= r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        if not re.match(reg, url):
            await ctx.send('Not a url, pls pass the full url.')
            return
        embed= discord.Embed(
            title= "Website snapshot",
            url= url,
            color= ctx.me.color
        )
        url= f'http://image.thum.io/get/png/noanimate/width/720/crop/{crop}/&{url}'
        urlretrieve(url, 'WebSnap.png')
        img= discord.File('WebSnap.png', 'WebSnap.png')
        embed.set_image(url= 'attachment://WebSnap.png')
        await ctx.send(embed= embed, file= img)

def setup(client):
    client.add_cog(Fun(client))