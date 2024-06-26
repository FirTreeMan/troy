import discord
import pygame
import requests
from dotenv import load_dotenv
from discord.ext import commands
from pygame import Surface, display, image, Rect, font, FONT_LEFT, FONT_RIGHT, FONT_CENTER
import gamble as g
import datetime
import io
import os
import random
import pickle


font.init()
display.init()
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FONT = "Futura Condensed Extra Bold.otf"
KFONT = "gg sans Medium.woff"
with open('stop.txt', 'r') as file:
    STOPQUOTES = tuple(file.readlines())
with open('kill.txt', 'r') as file:
    KILLQUOTES = tuple(file.readlines())
with open('cat.txt', 'r') as file:
    CATQUOTES = tuple(file.readlines())
DISCORDBG = (49, 51, 56)
STRANGLERANGE = (5, 600)
STRANGLEMULT = 3
STRANGLEMAX = 10
CATINTERVAL = 2
CATMAX = len(CATQUOTES) * CATINTERVAL
CATREGSPACE = 1
CATLOSERSPACE = 2
CATNAMES = tuple(os.listdir("cat"))
# delete cat.pkl when updating cat folder
if not os.path.isfile("cat.pkl"):
    CATSEARCHTERMS = {frozenset(tag for tag in value.replace(", ", ".").split(".")): index
                      for index, value in enumerate(CATNAMES)}
    with open("cat.pkl", 'wb') as file:
        pickle.dump(CATSEARCHTERMS, file, 5)
else:
    with open("cat.pkl", 'rb') as file:
        CATSEARCHTERMS = pickle.load(file)

STARTPTS = 50
ITEMCOSTS = {
    'killblock': 50,
    'strangleblock': 50,
    'strangle reset': 500,
    'cat reset': 500,
}
ITEMDESCS = {
    'killblock': 'cant be killed for a day',
    'strangleblock': 'cant be strangled for a day',
    'strangle reset': 'resets strangle buildup',
    'cat reset': 'resets curse buildup',
}


class Group:
    def __init__(self, server, name, members):
        self.server: int = server
        self.name: str = name
        self.members = members
        self.owner: int = self.members[0]

    @staticmethod
    def load(pklfile: str):
        groupdata: dict[int, dict[str, list[int]]]
        if os.path.isfile(pklfile):
            with open(pklfile, 'rb') as f:
                groupdata = pickle.load(f)
        else:
            return {}

        output: dict[int, list[Group]] = {}
        for server, servergroups in groupdata.items():
            for groupname, members in servergroups.items():
                output[server] = output.get(server, [])
                output[server].append(Group(server, groupname, members))
        return output

    @staticmethod
    def dump(pklfile: str, groupdict: dict[int, list]):
        groupdata: dict[int, dict[str, list[int]]] = {}

        for server, grouplist in groupdict.items():
            groupdata[server] = {}
            for group_ in grouplist:
                groupdata[server][group_.name] = group_.members
        with open(pklfile, 'wb') as _file:
            pickle.dump(groupdata, _file, 5)


def tryload(pklfile: str, default):
    if os.path.isfile(pklfile):
        with open(pklfile, 'rb') as f:
            return pickle.load(f)
    return default


def loadtext(textfile: str, integer=False):
    open(textfile, 'a+').close()
    with open(textfile, 'r') as f:
        return [int(s.rstrip('\n')) if integer else s.rstrip('\n') for s in f.readlines()]


stranglespam = {}
currmonth = -1
catspam = {}
points = tryload("points.pkl", {})
lobbies: list[g.Lobby] = []
usrlobbies = {}
items = tryload("items.pkl", {})
groups: dict[int, list[Group]] = Group.load("groups.pkl")
groupmessages: dict[int, str] = tryload("groupmessages.pkl", {})
losers = loadtext("losers.txt")
catexceptions = loadtext("catexceptions.txt", True)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="troy please ", intents=intents)


def drawtext(surface: Surface, text, rect: Rect, color=(0, 0, 0), fontname=FONT, fontsize=80, aa=True,
             bkg=(255, 255, 255), align=FONT_LEFT):
    usedfont = font.Font(fontname, fontsize)
    usedfont.align = align

    while True:
        fontrect = usedfont.render(text, antialias=aa, color=color, bgcolor=bkg, wraplength=rect.width)
        if fontrect.get_height() <= rect.height:
            break
        fontsize -= 1
        usedfont = font.Font(fontname, fontsize)
        usedfont.align = align

    surface.blit(fontrect, rect.topleft)

    return fontrect


def surfsequal(surf1: Surface, surf2: Surface):
    if surf1.get_size() != surf2.get_size():
        return False
    for x in range(surf1.get_width()):
        for y in range(surf1.get_height()):
            if surf1.get_at((x, y)) != surf2.get_at((x, y)):
                return False
    return True


async def searchweights(tags: set[str] | frozenset[str], terms: tuple[str], negterms: tuple[str]):
    tags = {tuple(s.split()) if isinstance(s, str) else s for s in tags}
    termset = set(terms)
    negtermset = set(negterms) if negterms else set()
    weight = 0
    checkedtitle = False
    for tag in tags:
        if not checkedtitle and tag[-1] == "!":
            if tag[:-1] == terms:
                return 999
            if tag[:-1] == negterms:
                return -999
            checkedtitle = True
            continue
        tagset = set(tag)
        intersections = tagset & termset
        negintersections = tagset & negtermset
        weight += len(intersections) - len(negintersections)
        if len(intersections) == len(tagset) > 1 and tag == terms:
            weight += len(tagset) * 0.1
        elif intersections:
            weight -= len(tagset) * 0.1
        if len(negintersections) == len(tagset) > 1 and tag == negterms:
            weight -= len(tagset) * 0.1
        elif negintersections:
            weight += len(tagset) * 0.1
    return weight


async def findlobby(ctx, user, game, solo=False, prebet=None):
    if lobby := usrlobbies.get(user.id, None):
        await lobby.removeplayer(user.id)
        usrlobbies.pop(user.id)
    if not solo:
        for ident, lobby in enumerate(lobbies):
            if lobby.gametype == game and len(lobby.players) <= g.Lobby.MAXPLAYERS and not lobby.ingame:
                await lobby.addplayer(user.id)
                usrlobbies[user.id] = lobby
                await send(ctx, f"joined lobby {ident}",
                           log=lobby)
                if prebet is not None:
                    await lobby.addmove(user.id, str(prebet))
                    await send(ctx, f"placed bet")
                return ident
    lobbies.append(g.Lobby(ctx, game, len(lobbies), {user.id}))
    usrlobbies[user.id] = lobbies[-1]
    if solo:
        await send(ctx, f"joined solo lobby {len(lobbies) - 1}",
                   log=f"{len(lobbies) - 1} solo")
        await send(ctx, await lobbies[-1].readyplayer(user.id),
                   nolog=True)

    return len(lobbies) - 1


async def pointdump():
    with open("points.pkl", 'wb') as _file:
        pickle.dump(points, _file, 5)


async def itemdump():
    with open("items.pkl", 'wb') as _file:
        pickle.dump(items, _file, 5)


async def groupdump(groupmessagedump=False):
    Group.dump("groups.pkl", groups)
    if not groupmessagedump:
        return
    with open("groupmessages.pkl", 'wb') as _file:
        pickle.dump(groupmessages, _file, 5)


async def send(ctx, *args, **kwargs):
    if kwargs.pop('forcecat', False) or \
            (not kwargs.pop('nocat', False) and catspam.get(ctx.message.author.id, 0) >= CATMAX):
        item = discord.File("cat/" + random.choice(CATNAMES))
        additions = [item]
        if kwargs.get('file', None):
            additions.insert(0, kwargs.pop('file'))
        kwargs['files'] = kwargs.get('files', []) + additions
    logdata = [logs] if not isinstance(logs := kwargs.pop('log', ''), list) else logs
    nolog = kwargs.pop('nolog', False)

    if not nolog:
        await log(ctx, *logdata)
    return await ctx.channel.send(*args, **kwargs)


async def log(ctx, *extra):
    message = ctx.message
    nl = "\n"
    print(f"{str(datetime.datetime.now()): <40}{message.author.display_name: <30}"
          f"{(message.guild.name if message.guild is not None else 'DM'): <30}{message.content.replace(nl, ' '): <80}",
          end='')
    print(*extra)


def catcooldown(rate, per, specrate, specper, cooltype=commands.BucketType.default):
    cd = commands.Cooldown(rate, per)
    cdspec = commands.Cooldown(specrate, specper)

    def determine(ctx):
        return cdspec \
            if catspam.get(ctx.message.author.id, 0) >= CATMAX and ctx.message.author.id not in catexceptions \
            else cd

    return commands.dynamic_cooldown(determine, cooltype)


cooldown = catcooldown(1, 1, 1, 10, commands.BucketType.user)


@bot.event
async def on_ready():
    print(f'{bot.user.name} on')
    print()
    print(f"{'date': <40}{'name': <30}{'server': <30}{'message': <80}{'extra': <80}")
    print("-" * 260)


@bot.event
async def on_message(message):
    global points

    if message.author.id != bot.application_id:
        if message.attachments:
            baseimg = image.load('cleantroy.png')
            for url in [s.url for s in message.attachments if s.content_type.startswith("image")]:
                img = image.load(io.BytesIO(requests.get(url).content), namehint='')
                if (size := img.get_size()) == baseimg.get_size() and \
                        surfsequal(img.subsurface(0, 200, size[0], size[1] - 200),
                                   baseimg.subsurface(0, 200, size[0], size[1] - 200)):
                    await message.channel.send("hey thats me")
                    await bot.process_commands(message)
                    return
        if (cheat := isinstance(message.channel, discord.DMChannel)) or \
                ((usrlobby := usrlobbies.get(message.author.id, None)) and
                 message.channel is usrlobby.ctx.message.channel):
            if (lobby := usrlobbies.get(message.author.id, None)) and lobby.game:
                if not lobby.ingame and await lobby.validmove(message.author.id, message.content):
                    betamt = int(message.content)
                    if betamt <= (userpoints := points.get(message.author.id, STARTPTS)):
                        points[message.author.id] = userpoints - betamt
                        await pointdump()
                        await send(await bot.get_context(message), "placed bet",
                                   log='|'.join([str(betamt), str(userpoints)]))
                    else:
                        await send(await bot.get_context(message), "yorue too poor !",
                                   log='|'.join([str(betamt), str(userpoints)]))
                if await lobby.addmove(message.author.id, message.content, cheat):
                    await send(lobby.ctx, await lobby.run(),
                               log=lobby)
                    points[message.author.id] += lobby.result.get('playerwinnings', {}).get(message.author.id, 0)
                    await pointdump()
                for user in lobby.private.keys():
                    await (await bot.fetch_user(user)).send(lobby.private[user])
                lobby.private.clear()

    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    emoji = reaction.emoji

    if user.bot:
        return

    if emoji == '👽':
        for messageid, groupname in groupmessages.items():
            if messageid == reaction.message.id:
                for group_ in groups[reaction.message.guild.id]:
                    if group_.name == groupname:
                        if user.id not in group_.members:
                            group_.members.append(user.id)
                            await groupdump()
                            await reaction.message.channel.send(f"{user.mention} joined group <{groupname}>")
                        return


# noinspection PyUnusedLocal
@bot.before_invoke
async def start(ctx):
    global currmonth

    if currmonth != (newmonth := datetime.datetime.now().month):
        currmonth = newmonth
        stranglespam.clear()
        catspam.clear()


@cooldown
@bot.command(name='live', help='checks for vitals')
async def live(ctx):
    await send(ctx, "iphone venezuela bottom texxt 100 billion dead")


@cooldown
@bot.command(name='make', help='prints a fresh troy')
async def make(ctx, verb: str = "spit yo shit", obj: str = "Troy", subj: str = "Troy"):
    imgsurf = image.load('cleantroy.png')
    surf = Surface(imgsurf.get_size(), pygame.SRCALPHA)
    surf.blit(imgsurf, (0, 0))
    verbrect = Rect(-2, -10, 363, 93)
    objrect = Rect(375, -10, 160, 93)
    subjrect = Rect(52, 85, 340, 93)

    drawtext(surf, verb, verbrect, align=FONT_CENTER)
    drawtext(surf, obj, objrect, align=FONT_LEFT)
    drawtext(surf, subj, subjrect, align=FONT_RIGHT)
    # pygame.draw.rect(surf, (255, 0, 0), verbrect, 2)
    # pygame.draw.rect(surf, (255, 0, 0), objrect, 2)
    # pygame.draw.rect(surf, (255, 0, 0), subjrect, 2)
    image.save(surf, 'make.png')

    await send(ctx, file=discord.File('make.png'),
               log='|'.join([verb, obj, subj]))


@cooldown
@bot.command(name='stop', help='asks it to stop')
async def stop(ctx):
    await send(ctx, quote := random.choice(STOPQUOTES),
               log=quote)


@cooldown
@bot.command(name='kill', help='something devious')
async def kill(ctx, user: discord.User = None):
    if user and user.id in (698596771059728455, 1127648163747086407):
        await send(ctx, "no thanks sweaty",
                   log="innocent victim")
        return
    if user and (item := items.get(user.id, {}).get('killblock', None)):
        if item and item.date() >= datetime.datetime.now().date():
            await send(ctx, "he bought safety",
                       log="safe victim")
            return

    member = ctx.message.guild.get_member(user.id) if user else ctx.message.guild.get_member(int(ctx.message.author.id))

    quote = random.choice(KILLQUOTES)
    text = quote.replace("\\n", "\n")
    textbox = font.Font(KFONT, 48).render(text + "\n", antialias=True, color=(255, 255, 255), bgcolor=DISCORDBG,
                                          wraplength=2490)
    pfpbase = pygame.transform.scale(image.load(io.BytesIO(requests.get(member.display_avatar.with_size(512)).content),
                                                namehint=''), (120, 120))
    pfp = Surface(pfpbase.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(pfp, (255, 255, 255, 255), (0, 0, *pfpbase.get_size()))
    pfp.blit(pfpbase, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    name = member.display_name
    rolecolor = member.color.to_rgb() if member.color != discord.Color.default() else (255, 255, 255)
    namebox = font.Font(KFONT, 48).render(name, antialias=True, color=rolecolor, bgcolor=DISCORDBG,
                                          wraplength=2490)
    time = (f"{random.randint(1, 12):02}/{random.randint(1, 30):02}/{random.randint(2020, 2023):04} "
            f"{random.randint(1, 12)}:{random.randint(1, 59):02} {random.choice(['AM', 'PM'])}")
    if str(ctx.message.guild.id) in losers:
        time = "11/14/1987 4:12 PM"
    timebox = font.Font(KFONT, 32).render(time, antialias=True, color=(148, 155, 164), bgcolor=DISCORDBG,
                                          wraplength=2490)

    surf = Surface((6 + pfp.get_width() + 33 + textbox.get_width(),
                    6 + namebox.get_height() + textbox.get_height()))
    surf.fill(DISCORDBG)
    surf.blit(pfp, (6, 6))
    surf.blit(namebox, (6 + pfp.get_width() + 33, 6))
    surf.blit(timebox, (6 + pfp.get_width() + 33 + namebox.get_width() + 18, 6 + 16))
    surf.blit(textbox, (surf.get_width() - textbox.get_width(), surf.get_height() - textbox.get_height()))
    # pygame.draw.rect(surf, (255, 0, 0), pfp.get_rect(), 2)
    # pygame.draw.rect(surf, (255, 0, 0), namebox.get_rect(), 2)
    # pygame.draw.rect(surf, (255, 0, 0), textbox.get_rect(), 2)

    image.save(surf, 'kill.png')

    await send(ctx, file=discord.File('kill.png'),
               log=quote[:30] + "...")


@cooldown
@bot.command(name='censor', help='for admins to reduce mischief')
async def censor(ctx):
    global losers

    if not ctx.message.author.guild_permissions.manage_messages:
        await send(ctx, "you aren't a moderator silly",
                   log="not a moderator")
        return

    if (guildid := str(ctx.message.guild.id)) in losers:
        losers.remove(guildid)
        await send(ctx, "this server is no longer in the stinky pile",
                   log="server uncensored")
    else:
        losers.append(guildid)
        await send(ctx, "activated dumb loser mode",
                   log="server censored")
    with open('losers.txt', 'w') as f:
        f.writelines([s + "\n" for s in losers])


@cooldown
@bot.command(name='strangle', help='choke someone (and yourself)')
async def strangle(ctx):
    # await send(ctx, len([s for s in ctx.message.guild.members
    #                             if ctx.message.guild.me.top_role > s.top_role]))
    if str(ctx.message.guild.id) in losers:
        await send(ctx, "mods won't let me (1984 anyone?)",
                   log="command censored")
        return
    me = ctx.message.guild.me
    instigator = ctx.message.author
    victimchoices = [s for s in ctx.message.guild.members if ctx.message.guild.me.top_role > s.top_role and
                     items.get(s.id, {}).get('strangleblock', datetime.date.min) < datetime.datetime.now().date()]
    if me.top_role <= instigator.top_role:
        await send(ctx, "you are too powerful... admin abuse...",
                   log="instigator has higher role")
        return
    if not victimchoices:
        await send(ctx, "there is nobody feeble enough here...",
                   log="no valid victims")
        return
    victim = random.choice(victimchoices)
    duration = datetime.timedelta(seconds=random.randrange(*STRANGLERANGE))
    instigatorduration = (duration * STRANGLEMULT * (stranglespam.get(instigator.id, 0)) *
                          (int(stranglespam.get(instigator.id, 0) > STRANGLEMAX) + 1))
    stranglespam[instigator.id] = stranglespam.get(instigator.id, 0) + 1
    await victim.timeout(duration, reason=f'strangled on behalf of {instigator.mention}')
    await instigator.timeout(instigatorduration, reason=f'wanted to strangle')
    await send(ctx, f"strangled you and {victim.mention}",
               log='|'.join([victim.display_name, str(duration), str(instigatorduration)]))


@cooldown
@bot.command(name='cat', hidden=True)
async def cat(ctx, *, search=''):
    async def get_weight_dict(_searchterms, _negterms):
        out = {}
        for term in CATSEARCHTERMS.keys():
            out[term] = await searchweights(term, _searchterms, _negterms)
        return out

    instigator = ctx.message.author
    space = CATREGSPACE if str(ctx.message.guild.id) not in losers else CATLOSERSPACE
    spamcnt = catspam.get(instigator.id, 0) + space
    catspam[instigator.id] = spamcnt
    quotient = spamcnt // CATINTERVAL
    if spamcnt > CATMAX and instigator.id not in catexceptions:
        await send(ctx, "im all out of cat juice...", nocat=True,
                   log="limit reached")
        return
    if search.startswith("curse"):
        catspam[instigator.id] = CATMAX
        await send(ctx, "you have been imbued with cat juice...", nocat=True,
                   log="limit forced")
        return
    args = []
    if spamcnt % CATINTERVAL == 0:
        if instigator.id not in catexceptions:
            args.append(CATQUOTES[quotient - 1])
        else:
            args.append(CATQUOTES[random.randrange(0, len(CATQUOTES))])
    attachment = None
    if search:
        searchterms, negterms = None, None
        if '/' in search:
            searchterms, negterms = [tuple(s.split()) for s in search.split('/')][:2]
        else:
            searchterms = tuple(search.split())

        weightdict = await get_weight_dict(searchterms, negterms)
        results = sorted(CATSEARCHTERMS.keys(), key=lambda x: weightdict[x], reverse=True)
        heaviest = weightdict[results[0]]

        for i, result in enumerate(results):
            if weightdict[result] < heaviest:
                results = results[:i]
                break

        item = random.choice(results)
        attachment = CATNAMES[CATSEARCHTERMS[item]]
    if attachment is None:
        attachment = random.choice(CATNAMES)
    await send(ctx, *args, file=discord.File("cat/" + attachment), nocat=True,
               log='|'.join([str(spamcnt), search, attachment]))


@cooldown
@bot.command(name='gamble', help='dont run out of points')
async def gamble(ctx, *, stuff=''):
    user = ctx.message.author

    stuff = stuff.split()
    if not stuff:
        await send(ctx, f"you have {points.get(ctx.message.author.id, STARTPTS)} gamblepoints",
                   log="checked points")
        return

    if stuff[-1] == 'help':
        text = '''
        use one of these terms at the end to join a lobby with the respective game:
        - blackjack (or 'b')
        append 'solo' when joining a lobby to only play against the computer
        append 'start' when in a lobby to start the game with all players
        append 'leave' when in a lobby to leave the lobby
        append 'callout' with the user you want to target
        append 'gift' with the receiving user and the amount to send
        after starting a game, dm the amount of gamblepoints you will bet for the game
        every round, send the command you want to use in the appropriate channel
        if you want to cheat, dm the cheat you want to use (with corresponding inputs)
        '''
        await send(ctx, text,
                   log='help')
        return
    if stuff[-1] == 'start':
        if lobby := usrlobbies.get(user.id, None):
            await send(ctx, await lobby.readyplayer(user.id),
                       log=lobby)
            return
    if stuff[-1] == 'leave':
        if lobby := usrlobbies.pop(user.id, None):
            await lobby.removeplayer(user.id)
            await send(ctx, "left lobby",
                       log=lobby)
            return
    if len(stuff) >= 2 and stuff[0] == 'callout' and (victim := stuff[1][2:-1]):
        if (lobby := usrlobbies.get(victim, None)) and lobby is usrlobbies.get(user.id, None):
            if amt := lobby.playercheats.get(victim, 0):
                points[victim] = points.get(user.id, STARTPTS) + await lobby.catchcheater(user.id, victim, True)
                await pointdump()
                await send(ctx, f"{ctx.message.author} called out {stuff[1]} for cheating x{amt}",
                           log="callout success")
            else:
                points[user.id] = points.get(user.id, STARTPTS) + await lobby.catchcheater(user.id, victim, False)
                await pointdump()
                await send(ctx, f"{ctx.message.author} thought he knew (actual loser)",
                           log="callout failed")
            return
    if len(stuff) == 3 and stuff[0] == 'gift' and len(victim := stuff[1][2:-1]) == 18:
        try:
            if int(stuff[2]) > points.get(victim, STARTPTS):
                return
        except ValueError:
            return
        amt = int(stuff[2])
        points[victim] = points.get(victim, STARTPTS) + amt
        points[user.id] = points.get(user.id, STARTPTS) - amt
        await pointdump()
        await send(ctx, f"gifted {amt} to <@{victim}>",
                   log='|'.join([user.id, victim, amt]))
        return

    solo = stuff[-1] == 'solo'
    prebet = None
    try:
        solo = solo or (stuff[-2] == 'solo' and int(stuff[-1]))
        prebet = int(stuff[-1])
    except ValueError:
        pass

    if stuff[0] in ('blackjack', 'b'):
        await findlobby(ctx, user, 'b', solo, prebet)
    elif stuff[0] in ('roulette', 'r'):
        await findlobby(ctx, user, 'r', solo, prebet)
    # elif stuff[0] in ('poker', 'p'):
    #     await findlobby(ctx, user, 'p', solo)
    else:
        await send(ctx, "type a real game duma",
                   log="invalid game")
        return


@cooldown
@bot.command(name='buy', help='get good')
async def buy(ctx, *, item=''):
    if not item:
        text = '\n'.join([f"{k}: {ITEMDESCS[k]} ({v} gamblepoints)" for k, v in ITEMCOSTS])
        await send(ctx, text)
        await ctx.invoke(bot.get_command('gamble'))
        return

    if item in ITEMCOSTS.keys():
        userpoints = points.get((user := ctx.message.author).id, STARTPTS)
        if userpoints >= ITEMCOSTS[item]:
            bought = None
            if item == 'killblock':
                time = datetime.datetime.now() + datetime.timedelta(days=1)
                bought = time
            elif item == 'strangleblock':
                time = datetime.datetime.now() + datetime.timedelta(days=1)
                bought = time
            elif item == 'strangle reset':
                stranglespam[user.id] = 0
            elif item == 'cat reset':
                catspam[user.id] = 0
            points[user.id] = points.get(user.id, STARTPTS) - ITEMCOSTS[item]
            await pointdump()
            if bought is not None:
                items[user.id][item] = bought
                await itemdump()
            await send(ctx, "you got it",
                       log=f"{item}|{ITEMCOSTS[item]}/{userpoints}")
        else:
            await send(ctx, "too broke loser",
                       log=f"{item}|{ITEMCOSTS[item]}/{userpoints}")


@cooldown
@bot.command(name='group', help='make and join groups (commands are create, join, leave, ping)')
async def group(ctx, *, args=''):
    server = ctx.message.guild.id
    author = ctx.message.author.id
    groups[server] = groups.get(server, [])
    grouplist = groups[server]
    command = args[:args.index(' ')]
    groupname = args[args.index(' ') + 1:]

    if len(groupname) > 40:
        await send(ctx, "too much text... attention span too short to read... need... tldr...",
                   log=f"groupname too long")
        return

    if command == 'create':
        for group_ in grouplist:
            if group_.name == groupname:
                await send(ctx, f"that group already exists... it's over for you...",
                           log=f"group <{groupname}> exists")
                return
        grouplist.append(Group(server, groupname, [author]))
        message = await send(ctx, f"created group <{groupname}>, react with 👽 to join",
                             log=f"created group <{groupname}>")
        groupmessages[message.id] = groupname
        await groupdump(True)
        await message.add_reaction('👽')
    elif command == 'join':
        for group_ in grouplist:
            if group_.name == groupname and author not in group_.members:
                group_.members.append(author)
                await groupdump()
                await send(ctx, f"joined group <{groupname}>",
                           log=f"joined group <{groupname}>")
                return
        await send(ctx, f"that group doesn't exist... it's over for you...",
                   log=f"can't join group <{groupname}>")
    elif command == 'leave':
        for index, group_ in enumerate(grouplist):
            if group_.name == groupname:
                if author in group_.members:
                    group_.members.remove(author)
                    await send(ctx, f"left group <{groupname}>",
                               log=f"left group <{groupname}>")
                    if len(group_.members) == 0:
                        grouplist.pop(index)
                        await send(ctx, f"nobody left in group <{groupname}>, deleted (lol)",
                                   log=f"deleted group <{groupname}>")
                    await groupdump()
                else:
                    await send(ctx, f"how can you leave when you weren't even invited lol",
                               log=f"group <{groupname}> not joined")
                    pass
                return
        await send(ctx, f"that group doesn't exist... it's over for you...",
                   log=f"can't join group <{groupname}>")
    elif command == 'ping':
        for group_ in grouplist:
            if group_.name == groupname:
                if author in group_.members:
                    output = ""
                    for uid in group_.members:
                        output += f"{(await bot.fetch_user(uid)).mention}\n"
                    output += "wake up"
                    await send(ctx, output,
                               log=f"pinged group <{groupname}>")
                else:
                    await send(ctx, f"i'm afraid i can't let you do that because you are a loser",
                               log=f"not member of group <{groupname}>")
                return
        await send(ctx, f"that group doesn't exist... it's over for you...",
                   log=f"can't join group <{groupname}>")
    else:
        await send(ctx, f"uhh... idk what that means",
                   nolog=True)


bot.run(TOKEN)
