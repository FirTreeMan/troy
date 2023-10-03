import os
import discord
import pygame
from dotenv import load_dotenv
from discord.ext import commands
from pygame import Surface, display, image, Rect, font, FONT_LEFT, FONT_RIGHT, FONT_CENTER

font.init()
display.init()
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FONT = "Futura Condensed Extra Bold.otf"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="troy please ", intents=intents)


def drawtext(surface: Surface, text, rect: Rect,
             color=(0, 0, 0), fontname=FONT, fontsize=80, aa=True, bkg=(255, 255, 255), align=FONT_LEFT):
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
    await ctx.channel.send("kys loser XD")


bot.run(TOKEN)
