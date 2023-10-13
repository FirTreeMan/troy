import discord
import pygame
import requests
from dotenv import load_dotenv
from discord.ext import commands
from pygame import Surface, display, image, Rect, font, FONT_LEFT, FONT_RIGHT, FONT_CENTER
from datetime import timedelta
import io
import os
import random

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
DISCORDBG = (49, 51, 56)
STRANGLERANGE = [5, 300]
STRANGLEMULT = 3
open('losers.txt', 'a+').close()
with open('losers.txt', 'r') as file:
    losers = [s.rstrip('\n') for s in file.readlines()]

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


@bot.event
async def on_ready():
    print(f'{bot.user.name} on')
    print(f"{'name': <30}{'server': <30}{'message'}")
    print("-" * 120)


@bot.before_invoke
async def common(ctx):
    message = ctx.message
    print(f"{message.guild.get_member(message.author.id).display_name: <30}{message.guild.name: <30}{message.content}")


@bot.command(name='live', help='checks for vitals')
async def live(ctx):
    await ctx.channel.send("iphone venezuela bottom texxt 100 billion dead")


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

    await ctx.channel.send(file=discord.File('make.png'))


@bot.command(name='stop', help='asks it to stop')
async def stop(ctx):
    await ctx.channel.send(random.choice(STOPQUOTES))


@bot.command(name='kill', help='something devious')
async def kill(ctx, user: discord.User = None):
    if user and user.id in (698596771059728455, 1127648163747086407):
        await ctx.channel.send("no thanks sweaty")
        return

    member = ctx.message.guild.get_member(user.id) if user else ctx.message.guild.get_member(int(ctx.message.author.id))

    text = random.choice(KILLQUOTES).replace("\\n", "\n")
    textbox = font.Font(KFONT, 48).render(text + "\n", antialias=True, color=(255, 255, 255), bgcolor=DISCORDBG,
                                          wraplength=2490)
    pfpbase = pygame.transform.scale(pygame.image.load(io.BytesIO(requests.get(member.avatar.with_size(512)).content),
                                                       namehint=""), (120, 120))
    pfp = pygame.Surface(pfpbase.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(pfp, (255, 255, 255, 255), (0, 0, *pfpbase.get_size()))
    pfp.blit(pfpbase, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    name = member.display_name
    rolecolor = member.color.to_rgb()
    namebox = font.Font(KFONT, 48).render(name, antialias=True, color=rolecolor, bgcolor=DISCORDBG,
                                          wraplength=2490)
    time = (f"{random.randint(1, 12):02}/{random.randint(1, 30):02}/{random.randint(2020, 2023):04} "
            f"{random.randint(1, 12)}:{random.randint(1, 59):02} {random.choice(['AM', 'PM'])}")
    if str(ctx.message.guild.id) in losers:
        time = "11/14/1987 4:12 PM"
    timebox = font.Font(KFONT, 32).render(time, antialias=True, color=(148, 155, 164), bgcolor=DISCORDBG,
                                          wraplength=2490)

    surf = pygame.Surface((6 + pfp.get_width() + 33 + textbox.get_width(),
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

    await ctx.channel.send(file=discord.File('kill.png'))


@bot.command(name='censor', help='for admins to make him less egregious')
async def censor(ctx):
    global losers

    if ctx.message.author.guild_permissions.manage_messages:
        if (guildid := str(ctx.message.guild.id)) in losers:
            losers.remove(guildid)
            await ctx.channel.send("this server is no longer in the stinky pile")
        else:
            losers.append(guildid)
            await ctx.channel.send("activated dumb loser mode")
        with open('losers.txt', 'w') as f:
            f.writelines([s + "\n" for s in losers])
    else:
        await ctx.channel.send("you aren't a moderator silly")


@bot.command(name='strangle', help='choke someone (and yourself)')
async def strangle(ctx):
    # await ctx.channel.send(len([s for s in ctx.message.guild.members
    #                             if ctx.message.guild.me.top_role > s.top_role]))
    if str(ctx.message.guild.id) in losers:
        await ctx.channel.send("mods wont let me (1984 anyone?)")
        return
    me = ctx.message.guild.me
    instigator = ctx.message.author
    victimchoices = [s for s in ctx.message.guild.members if ctx.message.guild.me.top_role > s.top_role]
    if me.top_role <= instigator.top_role:
        await ctx.channel.send("you are too powerful... admin abuse...")
        return
    if not victimchoices:
        await ctx.channel.send("there is nobody here to exert my power over...")
        return
    victim = random.choice(victimchoices)
    duration = timedelta(seconds=random.randrange(*STRANGLERANGE))
    await victim.timeout(duration, reason=f'strangled on behalf of {instigator.mention}')
    await instigator.timeout(duration * STRANGLEMULT, reason=f'wanted to strangle')
    await ctx.channel.send(f"strangled you and {victim.mention}")


bot.run(TOKEN)
