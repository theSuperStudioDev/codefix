import time
import os
import platform
import re
import asyncio
import inspect
import textwrap
from datetime import datetime, timedelta
from collections import Counter
import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pytz import timezone
import loadconfig

class TimeParser:
    def __init__(self, argument):
        compiled = re.compile(r"(?:(?P<hours>[0-9]{1,5})h)?(?:(?P<minutes>[0-9]{1,5})m)?(?:(?P<seconds>[0-9]{1,5})s)?$")
        self.original = argument
        try:
            self.seconds = int(argument)
        except ValueError as e:
            match = compiled.match(argument)
            if match is None or not match.group(0):
                raise commands.BadArgument('Invalid time given, valid examples are `4h`, `3m`, or `2s`') from e

            self.seconds = 0
            hours = match.group('hours')
            if hours is not None:
                self.seconds += int(hours) * 3600
            minutes = match.group('minutes')
            if minutes is not None:
                self.seconds += int(minutes) * 60
            seconds = match.group('seconds')
            if seconds is not None:
                self.seconds += int(seconds)

        if self.seconds <= 0:
            raise commands.BadArgument('Too little time given, valid examples are `4h`, `3m`, or `2s`')

        if self.seconds > 604800: # 7 days
            raise commands.BadArgument('7 days is a long time, don\'t you think?')

    @staticmethod
    def human_timedelta(dt):
        now = datetime.now(timezone(loadconfig.__timezone__))
        delta = now - dt
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        years, days = divmod(days, 365)

        if days:
            if hours:
                return '%s and %s' % (Plural(day=days), Plural(hour=hours))
            return Plural(day=days)

        if hours:
            if minutes:
                return '%s and %s' % (Plural(hour=hours), Plural(minute=minutes))
            return Plural(hour=hours)

        if minutes:
            if seconds:
                return '%s and %s' % (Plural(minute=minutes), Plural(second=seconds))
            return Plural(minute=minutes)
        return Plural(second=seconds)

class Plural:
    def __init__(self, **attr):
        iterator = attr.items()
        self.name, self.value = next(iter(iterator))

    def __str__(self):
        v = self.value
        if v > 1:
            return '%s %ss' % (v, self.name)
        return '%s %s' % (v, self.name)

class utility(commands.Cog):
    '''General/useful commands that don't fit anywhere else'''

    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        print('Error in {0.command.qualified_name}: {1}'.format(ctx, error))

    @staticmethod
    def _newImage(width, height, color):
        return Image.new("L", (width, height), color)

    @staticmethod
    def _getRoles(roles):
        string = ''
        for role in roles[::-1]:
            if not role.is_default():
                string += f'{role.mention}, '
        if string == '':
            return 'None'
        else:
            return string[:-2]

    @staticmethod
    def _getEmojis(emojis):
        string = ''
        for emoji in emojis:
            string += str(emoji)
        if string == '':
            return 'None'
        else:
            return string[:1000] # The maximum allowed character amount for embed fields

@commands.command(aliases=['uptime', 'up'])
async def status(self, ctx):
    '''Info about the bot'''
    timeUp = time.time() - self.bot.startTime
    hours = timeUp / 3600
    minutes = (timeUp / 60) % 60
    seconds = timeUp % 60

    admin = self.bot.AppInfo.owner
    users = 0
    channel = 0
    if len(self.bot.commands_used.items()):
        commandsChart = sorted(self.bot.commands_used.items(), key=lambda t: t[1], reverse=False)
        topCommand = commandsChart.pop()
        commandsInfo = '{} (Top Command: {} x {})'.format(sum(self.bot.commands_used.values()), topCommand[1], topCommand[0])
    else:
        commandsInfo = str(sum(self.bot.commands_used.values()))
    for guild in self.bot.guilds:
        users += len(guild.members)
        channel += len(guild.channels)

    embed = discord.Embed(color=ctx.me.top_role.colour)
    embed.set_footer(text='This bot is open-source on GitHub: https://github.com/Der-Eddy/discord_bot')
    embed.set_thumbnail(url=ctx.me.avatar.url)
    embed.add_field(name='Admin', value=admin, inline=False)
    embed.add_field(name='Uptime', value='{0:.0f} hours, {1:.0f} minutes, and {2:.0f} seconds\n'.format(hours, minutes, seconds), inline=False)
    embed.add_field(name='Observed Users', value=users, inline=True)
    embed.add_field(name='Observed Servers', value=len(self.bot.guilds), inline=True)
    embed.add_field(name='Observed Channels', value=channel, inline=True)
    embed.add_field(name='Executed Commands', value=commandsInfo, inline=True)
    embed.add_field(name='Bot Version', value=self.bot.botVersion, inline=True)
    embed.add_field(name='Discord.py Version', value=discord.__version__, inline=True)
    embed.add_field(name='Python Version', value=platform.python_version(), inline=True)
    embed.add_field(name='Docker', value=str(self.bot.docker), inline=True)
    # embed.add_field(name='Memory Usage', value=f'{round(memory_usage(-1)[0], 3)} MB', inline=True)
    embed.add_field(name='Operating System', value=f'{platform.system()} {platform.release()} {platform.version()}', inline=False)
    await ctx.send('**:information_source:** Information about this bot:', embed=embed)

@commands.command()
async def ping(self, ctx):
    '''Measures the response time'''
    ping = ctx.message
    pong = await ctx.send('**:ping_pong:** Pong!')
    delta = pong.created_at - ping.created_at
    delta = int(delta.total_seconds() * 1000)
    await pong.edit(content=f':ping_pong: Pong! ({delta} ms)\n*Discord WebSocket Latency: {round(self.bot.latency, 5)} ms*')

# @commands.command()
# @commands.cooldown(1, 2, commands.cooldowns.BucketType.guild)
# async def github(self, ctx):
#     '''In progress'''
#     url = 'https://api.github.com/repos/Der-Eddy/discord_bot/stats/commit_activity'
#     async with aiohttp.get(url) as r:
#         if r.status == 200:
#             content = await r.json()
#             commitCount = 0
#             for week in content:
#                 commitCount += week['total']
#
#             embed = discord.Embed(title='GitHub Repo Stats', type='rich', color=0xf1c40f) #Golden
#             embed.set_thumbnail(url='https://assets-cdn.github.com/images/modules/logos_page/GitHub-Mark.png')
#             embed.add_field(name='Commits', value=commitCount, inline=True)
#             embed.add_field(name='Link', value='https://github.com/Der-Eddy/discord_bot')
#             await ctx.send(embed=embed)
#         else:
#             await ctx.send(':x: Could not access the GitHub API\nhttps://github.com/Der-Eddy/discord_bot')

@commands.command(aliases=['info'])
async def about(self, ctx):
    '''Info about me'''
    msg = 'Shinobu Oshino is perhaps one of the most mysterious characters in Bakemonogatari. Until the spring before last, she was a highly regarded, noble, ruthless vampire over 500 years old. She mercilessly attacked and massacred humans at will. Koyomi Araragi was also attacked and severely injured by her. Only through the intervention of the exorcist Meme Oshino could Kiss-shot Acerola-orion Heart-under-blade, as she was known then, be defeated. However, she lost all her memories and was transformed from an attractive, adult woman into an innocent girl.\n\n'
    msg += 'Since then, she has lived with Meme in an abandoned building and was taken in by him. He also gave her the name Shinobu. The vampire blood in her still craves victims, and since Koyomi feels somewhat responsible, he regularly offers himself as a source of food for Shinobu.\n\n'
    msg += 'Source: http://www.anisearch.de/character/6598,shinobu-oshino/\n\n'

    embed = discord.Embed(color=ctx.me.top_role.colour)
    embed.set_footer(text='This bot is also free, open-source, written in Python, and made with discord.py! https://github.com/Der-Eddy/discord_bot\n')
    embed.set_thumbnail(url=ctx.me.avatar.url)
    embed.add_field(name='**:information_source: Shinobu Oshino (500 years old)**', value=msg, inline=False)
    await ctx.send(embed=embed)

@commands.command(aliases=['archive'])
@commands.cooldown(1, 60, commands.cooldowns.BucketType.channel)
async def log(self, ctx, *limit: int):
    '''Archives the log of the current channel and uploads it as an attachment

    Example:
    -----------

    :log 100
    '''
    if not limit:
        limit = 10
    else:
        limit = limit[0]
    logFile = f'{ctx.channel}.log'
    counter = 0
    with open(logFile, 'w', encoding='UTF-8') as f:
        f.write(f'Archived messages from channel: {ctx.channel} on {ctx.message.created_at.strftime("%d.%m.%Y %H:%M:%S")}\n')
        async for message in ctx.channel.history(limit=limit, before=ctx.message):
            try:
                attachment = '[Attached file: {}]'.format(message.attachments[0].url)
            except IndexError:
                attachment = ''
            f.write('{} {!s:20s}: {} {}\r\n'.format(message.created_at.strftime('%d.%m.%Y %H:%M:%S'), message.author, message.clean_content, attachment))
            counter += 1
    msg = f':ok: {counter} messages have been archived!'
    f = discord.File(logFile)
    await ctx.send(file=f, content=msg)
    os.remove(logFile)

@log.error
async def log_error(self, error, ctx):
    if isinstance(error, commands.errors.CommandOnCooldown):
        seconds = str(error)[34:]
        await ctx.send(f':alarm_clock: Cooldown! Try again in {seconds}')

@commands.command()
async def invite(self, ctx):
    '''Creates an invite link for the current channel'''
    invite = await ctx.channel.create_invite(unique=False)
    msg = f'Invite link for **#{ctx.channel.name}** on server **{ctx.guild.name}**:\n`{invite}`'
    await ctx.send(msg)

@commands.command()
async def whois(self, ctx, member: discord.Member=None):
    '''Provides information about a user

    Example:
    -----------

    :whois @Der-Eddy#6508
    '''
    if member is None:
        member = ctx.author

    if member.top_role.is_default():
        topRole = 'everyone' # to prevent @everyone spam
        topRoleColour = '#000000'
    else:
        topRole = member.top_role
        topRoleColour = member.top_role.colour

    if member is not None:
        embed = discord.Embed(color=member.top_role.colour)
        embed.set_footer(text=f'UserID: {member.id}')
        embed.set_thumbnail(url=member.avatar.url)
        if member.name != member.display_name:
            fullName = f'{member} ({member.display_name})'
        else:
            fullName = member
        embed.add_field(name=member.name, value=fullName, inline=False)
        embed.add_field(name='Joined Discord on', value='{}\n(Days since: {})'.format(member.created_at.strftime('%d.%m.%Y'), (datetime.now(timezone(loadconfig.__timezone__)) - member.created_at).days), inline=True)
        embed.add_field(name='Joined server on', value='{}\n(Days since: {})'.format(member.joined_at.strftime('%d.%m.%Y'), (datetime.now(timezone(loadconfig.__timezone__)) - member.joined_at).days), inline=True)
        embed.add_field(name='Avatar Link', value=member.avatar.url, inline=False)
        embed.add_field(name='Roles', value=self._getRoles(member.roles), inline=True)
        embed.add_field(name='Role color', value='{} ({})'.format(topRoleColour, topRole), inline=True)
        embed.add_field(name='Status', value=member.status, inline=True)
        await ctx.send(embed=embed)
    else:
        msg = ':no_entry: You did not specify a user!'
        await ctx.send(msg)

@commands.command(aliases=['e'])
async def emoji(self, ctx, emojiname: str):
    '''Returns an enlarged version of a specified emoji

    Example:
    -----------

    :emoji Emilia
    '''
    emoji = discord.utils.find(lambda e: e.name.lower() == emojiname.lower(), self.bot.emojis)
    if emoji:
        tempEmojiFile = 'tempEmoji.png'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(str(emoji.url)) as img:
                with open(tempEmojiFile, 'wb') as f:
                    f.write(await img.read())
            f = discord.File(tempEmojiFile)
            await ctx.send(file=f)
            os.remove(tempEmojiFile)
    else:
        await ctx.send(':x: Could not find the specified emoji :(')

@commands.command(aliases=['emotes'])
async def emojis(self, ctx):
    '''Lists all emojis the bot has access to'''
    msg = ''
    for emoji in self.bot.emojis:
        if len(msg) + len(str(emoji)) > 1000:
            await ctx.send(msg)
            msg = ''
        msg += str(emoji)
    await ctx.send(msg)

@commands.command(pass_context=True, aliases=['serverinfo', 'guild', 'membercount'])
async def server(self, ctx):
    '''Provides information about the current Discord guild'''
    emojis = self._getEmojis(ctx.guild.emojis)
    roles = self._getRoles(ctx.guild.roles)
    embed = discord.Embed(color=discord.Color.random())
    embed.set_thumbnail(url=ctx.guild.icon)
    embed.set_footer(text='Some emojis might be missing')
    embed.add_field(name='Name', value=ctx.guild.name, inline=True)
    embed.add_field(name='ID', value=ctx.guild.id, inline=True)
    embed.add_field(name='Owner', value=ctx.guild.owner, inline=True)
    embed.add_field(name='Members', value=ctx.guild.member_count, inline=True)
    embed.add_field(name='Premium Members', value=ctx.guild.premium_subscription_count, inline=True)
    embed.add_field(name='Created on', value=ctx.guild.created_at.strftime('%d.%m.%Y'), inline=True)
    if ctx.guild.system_channel:
        embed.add_field(name='Default Channel', value=f'#{ctx.guild.system_channel}', inline=True)
    embed.add_field(name='AFK Voice Timeout', value=f'{int(ctx.guild.afk_timeout / 60)} min', inline=True)
    embed.add_field(name='Guild Shard', value=ctx.guild.shard_id, inline=True)
    embed.add_field(name='NSFW Level', value=str(ctx.guild.nsfw_level).removeprefix('NSFWLevel.'), inline=True)
    embed.add_field(name='MFA Level', value=str(ctx.guild.mfa_level).removeprefix('MFALevel.'), inline=True)
    if ctx.guild.splash:
        embed.add_field(name='Splash', value=ctx.guild.splash, inline=True)
    if ctx.guild.discovery_splash:
        embed.add_field(name='Discovery Splash', value=ctx.guild.discovery_splash, inline=True)
    if ctx.guild.banner:
        embed.add_field(name='Banner', value=ctx.guild.banner, inline=True)
    embed.add_field(name='Roles', value=roles, inline=True)
    embed.add_field(name='Custom Emojis', value=emojis, inline=True)
    await ctx.send(embed=embed)

# Shamelessly copied from https://github.com/Rapptz/RoboDanny/blob/b513a32dfbd4fdbd910f7f56d88d1d012ab44826/cogs/meta.py
@commands.command(aliases=['reminder'])
@commands.cooldown(1, 30, commands.cooldowns.BucketType.user)
async def timer(self, ctx, time: TimeParser, *, message=''):
    '''Sets a timer and notifies you when it expires

    Example:
    -----------

    :timer 13m Pizza

    :timer 2h Stream starts
    '''
    reminder = None
    completed = None
    message = message.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')

    if not message:
        reminder = ':timer: Ok {0.mention}, I have set a timer for {1}.'
        completed = ':alarm_clock: Ding Ding Ding {0.mention}! Your timer has expired.'
    else:
        reminder = ':timer: Ok {0.mention}, I have set a timer for `{2}` for {1}.'
        completed = ':alarm_clock: Ding Ding Ding {0.mention}! Your timer for `{1}` has expired.'

    human_time = datetime.now(timezone(loadconfig.__timezone__)) - timedelta(seconds=time.seconds)
    human_time = TimeParser.human_timedelta(human_time)
    await ctx.send(reminder.format(ctx.author, human_time, message))
    await asyncio.sleep(time.seconds)
    await ctx.send(completed.format(ctx.author, message, human_time))

@timer.error
async def timer_error(self, ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send(str(error))
    elif isinstance(error, commands.errors.CommandOnCooldown):
        seconds = str(error)[34:]
        await ctx.send(f':alarm_clock: Cooldown! Try again in {seconds}')

@commands.command()
async def source(self, ctx, *, command: str = None):
    '''Displays the source code for a command on GitHub

    Example:
    -----------

    :source kawaii
    '''
    source_url = 'https://github.com/Der-Eddy/discord_bot'
    if command is None:
        await ctx.send(source_url)
        return

    obj = self.bot.get_command(command.replace('.', ' '))
    if obj is None:
        return await ctx.send(':x: Could not find the command')

    src = obj.callback.__code__
    lines, firstlineno = inspect.getsourcelines(src)
    sourcecode = inspect.getsource(src).replace('```', '')
    if not obj.callback.__module__.startswith('discord'):
        location = os.path.relpath(src.co_filename).replace('\\', '/')
    else:
        location = obj.callback.__module__.replace('.', '/') + '.py'
        source_url = 'https://github.com/Rapptz/discord.py'

    if len(sourcecode) > 1900:
        final_url = '{}/blob/master/{}#L{}-L{}'.format(source_url, location, firstlineno, firstlineno + len(lines) - 1)
    else:
        final_url = '<{}/blob/master/{}#L{}-L{}>\n```Python\n{}```'.format(source_url, location, firstlineno, firstlineno + len(lines) - 1, sourcecode)

    await ctx.send(final_url)

@commands.command(hidden=True)
async def roleUsers(self, ctx, *roleName: str):
    '''Lists all users with a specific role'''
    roleName = ' '.join(roleName)
    role = discord.utils.get(ctx.guild.roles, name=roleName)
    msg = ''
    for member in ctx.guild.members:
        if role in member.roles:
            msg += f'{member.id} | {member}\n'

    if msg == '':
        await ctx.send(':x: Could not find any users with that role!')
    else:
        await ctx.send(msg)

@commands.command(aliases=['activities'])
async def games(self, ctx, *scope):
    '''Displays what games are currently being played on the server'''
    games = Counter()
    for member in ctx.guild.members:
        for activity in member.activities:
            if isinstance(activity, discord.Game):
                games[str(activity)] += 1
            elif isinstance(activity, discord.Activity):
                games[activity.name] += 1
    msg = ':chart: Games currently being played on this server\n'
    msg += '```js\n'
    msg += '{!s:40s}: {!s:>3s}\n'.format('Name', 'Count')
    chart = sorted(games.items(), key=lambda t: t[1], reverse=True)
    for index, (name, amount) in enumerate(chart):
        if len(msg) < 1950:
            msg += '{!s:40s}: {!s:>3s}\n'.format(name, amount)
        else:
            amount = len(chart) - index
            msg += f'+ {amount} others'
            break
    msg += '```'
    await ctx.send(msg)

@commands.command()
async def spoiler(self, ctx, *, text: str):
    '''Creates a GIF image that displays a spoiler text when hovered over'''
    content = '**' + ctx.author.display_name + '** has spoiled some text:'
    try:
        await ctx.message.delete()
    except discord.errors.Forbidden:
        content += '\n*(Please delete your own message)*'

    lineLength = 60
    margin = (5, 5)
    fontFile = "font/Ubuntu-R.ttf"
    fontSize = 18
    fontColor = 150
    bgColor = 20
    font = ImageFont.truetype(fontFile, fontSize)

    textLines = []
    for line in text.splitlines():
        textLines.extend(textwrap.wrap(line, lineLength, replace_whitespace=False))

    title = 'SPOILER! Hover to read'
    width = font.getsize(title)[0] + 50
    height = 0

    for line in textLines:
        size = font.getsize(line)
        width = max(width, size[0])
        height += size[1] + 2

    width += margin[0]*2
    height += margin[1]*2

    textFull = '\n'.join(textLines)

    spoilIMG = [self._newImage(width, height, bgColor) for _ in range(2)]
    spoilText = [title, textFull]

    for img, txt in zip(spoilIMG, spoilText):
        canvas = ImageDraw.Draw(img)
        canvas.multiline_text(margin, txt, font=font, fill=fontColor, spacing=4)

    path = f'tmp\\{ctx.message.id}.gif'

    spoilIMG[0].save(path, format='GIF', save_all=True, append_images=[spoilIMG[1]], duration=[0, 0xFFFF], loop=0)
    f = discord.File(path)
    await ctx.send(file=f, content=content)

    os.remove(path)

@commands.command(aliases=['vote', 'addvotes', 'votes'])
async def addvote(self, ctx, votecount='bool'):
    '''Adds emotes as reactions for voting/polling'''
    if votecount.lower() == 'bool':
        emote_list = ['✅', '❌']
    elif votecount in ['2', '3', '4', '5', '6', '7', '8', '9', '10']:
        emotes = ['1\u20e3', '2\u20e3', '3\u20e3', '4\u20e3', '5\u20e3', '6\u20e3', '7\u20e3', '8\u20e3', '9\u20e3', '\U0001f51f']
        emote_list = []
        for i in range(0, int(votecount)):
            emote_list.append(emotes[i])
    else:
        await ctx.send(':x: Please specify a number between 2 and 10')
        return

    message = await ctx.channel.history(limit=1, before=ctx.message).flatten()
    try:
        await ctx.message.delete()
    except:
        pass

    for emote in emote_list:
        await message[0].add_reaction(emote)

# This command needs to be at the end due to its name
@commands.command()
async def commands(self, ctx):
    '''Displays how many times each command has been used since the last startup'''
    msg = ':chart: List of executed commands (since last startup)\n'
    msg += 'Total: {}\n'.format(sum(self.bot.commands_used.values()))
    msg += '```js\n'
    msg += '{!s:15s}: {!s:>4s}\n'.format('Name', 'Count')
    chart = sorted(self.bot.commands_used.items(), key=lambda t: t[1], reverse=True)
    for name, amount in chart:
        msg += '{!s:15s}: {!s:>4s}\n'.format(name, amount)
    msg += '```'
    await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(utility(bot))
