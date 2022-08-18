import decimal
from enum import unique
from hashlib import new
from operator import truediv
from typing import AsyncContextManager
from bson.objectid import ObjectId
import discord
from discord import message
from discord import user
from discord.ext import commands, tasks
from discord.ext.commands import bot
from discord.ext.commands.core import Command, command, has_permissions
from discord.ext.commands.errors import CommandNotFound
from discord.utils import get
import random
import asyncio
import time
import pymongo
from pymongo import MongoClient
from asyncio import sleep
from collections import Counter
import decimal
import datetime
from datetime import date
import os
from pymongo.common import COMMAND_NOT_FOUND_CODES

from pymongo.results import InsertOneResult

from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption

import math
import re
import topgg

botOnline = False

cluster = MongoClient(os.getenv('MONGOTOKEN'))

charDB = cluster["acrafflebot"]["characters"]
userDB = cluster["acrafflebot"]["users"]
botstatsDB = cluster["acrafflebot"]["botstats"]
showDB = cluster["acrafflebot"]["shows"]
loadingScreenDB = cluster["acrafflebot"]["loadingscreens"]
shopDB = cluster["acrafflebot"]["usershops"]
voteDB = cluster["acrafflebot"]["uservotes"]
blockDB = cluster["acrafflebot"]["blocks"]
presDB = cluster["acrafflebot"]["userprestige"]
achDB = cluster["acrafflebot"]["achievements"]
sznDB = cluster["acrafflebot"]["seasons"]
sznWinDB = cluster["acrafflebot"]["sznwinners"]

intents = discord.Intents.default()
intents.members = True


cmdPrefix = "!" #get_prefix


client = discord.Client(intents = intents)
client = commands.Bot(command_prefix = cmdPrefix, intents=intents)

version = botstatsDB.find_one({"id":573})

versionNumber = version["version"]

botName = "acraffle"
client.remove_command("help") #removes the premade help command so we can use our own

@client.event
async def on_ready():
    DiscordComponents(client)
    print (f"Bot Online\nVersion {versionNumber}") #when the bot runs properly it will print this message to the console
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"!achelp"))
    global botOnline
    botOnline = True

#Internal Commands
def printlist(type,list):
    listname = []
    for character in list:
        try:
            int(character)
            listname.append(f"{character}")
        except:
            listname.append(f"{character.capitalize()}")
    if type == "list":
        return('\n'.join(listname))
    if type == "embed":
        return
        
@client.event
async def on_command_error(ctx, error):
    if isinstance(error,commands.CommandInvokeError) and isinstance(error.original, ValueError):
            ctx.command.reset_cooldown(ctx)

    elif isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title = f"Cooldown - {ctx.author.name.capitalize()}",description = 'This command is on cooldown for you.\nTry again in:',color = discord.Color.teal())
        if error.retry_after >= 3600:
            em.add_field(name = "Hours                  ", value = '**{:.2f}** hours'.format(error.retry_after / 3600))
            em.add_field(name = "Minutes", value = '**{:.2f}** min'.format(error.retry_after / 60))
        elif error.retry_after < 3600 and error.retry_after >= 60:
            em.add_field(name = "Minutes", value = '**{:.2f}** min'.format(error.retry_after / 60))
        else:
            em.add_field(name = "Seconds", value = '**{:.2f}** sec'.format(error.retry_after))
        em.set_thumbnail(url = ctx.author.avatar_url)
        await ctx.send(embed = em)
        await send_logs_cooldown(ctx.author,ctx.message.guild)
        return

    elif isinstance(error, commands.MissingPermissions):
        em = discord.Embed(title = f"Missing Permissions - {ctx.author.name.capitalize()}",description = 'You need **administrator** permissions to use this command.',color = discord.Color.teal())
        await ctx.send(embed = em)
        return

    elif isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, commands.MemberNotFound):
        return

    elif isinstance(error, commands.ExpectedClosingQuoteError):
        return

    elif isinstance(error, commands.MessageNotFound):
        return

    elif isinstance(error, commands.BadColourArgument):
        return

    elif isinstance(error, commands.BotMissingPermissions):
        em = discord.Embed(title = f"ACraffle is Missing Permissions!",description = "Please kick the bot from the server and re-invite it with the neccessary permisions.\nThank You",color = discord.Color.red())
        await ctx.send(embed = em)
        return

    elif isinstance(error, commands.EmojiNotFound):
        em = discord.Embed(title = f"Emoji Not Found!",description = "Sometimes server specific emojis won't work in the BIO so keep that in mind!",color = discord.Color.red())
        await ctx.send(embed = em)
        return

    else:
        raise error

async def createuser(member,guild):
    data = userDB.find_one({"id":member.id})
    if data is None:
        # guildid = guild.id
        # guildname = guild.name
        newuser = {"id": member.id,"name":member.name,"currentchar":None}
        userDB.insert_one(newuser)
        userDB.update_one({"id":member.id}, {"$set":{"favorites": [] }})
       
        await send_logs_newuser(member,guild)
        await addUniqueUser()
        return
    else:
        if data["name"] == member.name:
            return
        else:
            userDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return
    
async def createvoter(member):
    data = voteDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name,"credits":0}
        voteDB.insert_one(newuser)
        return
    else:
        if data["name"] == member.name:
            return
        else:
            voteDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createpres(member):
    data = presDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name}
        presDB.insert_one(newuser)
        presDB.update_one({"id":member.id}, {"$set":{"shows":[]}})
        presDB.update_one({"id":member.id}, {"$set":{"dates":[]}})
        presDB.update_one({"id":member.id}, {"$set":{"totPres":0}})
        return
    else:
        if data["name"] == member.name:
            return
        else:
            presDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createblock(member):
    data = blockDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name}
        blockDB.insert_one(newuser)
        blockDB.update_one({"id":member.id}, {"$set":{"blocklist": [] }})
        return
    else:
        if data["name"] == member.name:
            return
        else:
            blockDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createshopuser(member,guild):
    data = shopDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name,'money':0}
        shopDB.insert_one(newuser)
        shopDB.update_one({"id":member.id}, {"$set":{"characterShop": [] }})
        try:
            oldProf = userDB.find_one({'id':member.id})
            try:
                shopDB.update_one({"id":member.id}, {"$set":{"money": oldProf['money']}})
                userDB.update_one({"id":member.id}, {"$unset":{"money":""}})
            except:
                pass
            try:
                userDB.update_one({"id":member.id}, {"$unset":{"characterShop":""}})
            except:
                pass
            try:
                userDB.update_one({"id":member.id}, {"$unset":{"boughtuncommon":""}})
                userDB.update_one({"id":member.id}, {"$unset":{"boughtrare":""}})
                userDB.update_one({"id":member.id}, {"$unset":{"boughtepic":""}})
                userDB.update_one({"id":member.id}, {"$unset":{"boughtlegendary":""}})
                userDB.update_one({"id":member.id}, {"$unset":{"boughtloading":""}})
            except:
                pass
            try:
                userDB.update_one({"id":member.id}, {"$unset":{"month":""}})
                userDB.update_one({"id":member.id}, {"$unset":{"tomorrow":""}})
            except:
                pass
                
        except:
            pass

        return
    else:
        if data["name"] == member.name:
            return
        else:
            shopDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createsznuser(member):
    data = sznDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name,"xp":0}
        sznDB.insert_one(newuser)
        return
    else:
        if data["name"] == member.name:
            return
        else:
            sznDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createsznWinuser(member):
    data = sznWinDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name}
        sznWinDB.insert_one(newuser)
        sznWinDB.update_one({"id":member.id}, {"$set":{"prevSeasons":[]}})
        return
    else:
        if data["name"] == member.name:
            return
        else:
            sznWinDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

async def createachuser(member):
    data = achDB.find_one({"id":member.id})
    if data is None:
        newuser = {"id": member.id,"name":member.name,"votes":0, "trades":0}
        achDB.insert_one(newuser)
        return
    else:
        if data["name"] == member.name:
            return
        else:
            achDB.update_one({"id":member.id}, {"$set":{"name":member.name}})
            return

winGifs = [
        "https://cdn.discordapp.com/attachments/895180216564084737/948092265069432862/money_happy.gif",
        "https://i.pinimg.com/originals/16/1d/34/161d342a29cbb9c85f6bb7db905fb9b9.gif",
        "https://c.tenor.com/nBWlYPbKxzwAAAAC/anime-happy.gif",
        "https://c.tenor.com/dNcXa6SrTrQAAAAC/himouto-umaru-chan-anime-smile.gif",
        "https://c.tenor.com/krtQxxqLkLAAAAAC/team-rocket-money.gif",
        "https://c.tenor.com/YeS1tAsLUuQAAAAC/anime-boy.gif",
        "https://c.tenor.com/QD1c8lZdCAQAAAAC/tsunade-naruto.gif",
        "https://c.tenor.com/cs2kpxUZGTIAAAAC/offer-money.gif"
    ]

loseGifs = [
    "https://c.tenor.com/YM3fW1y6f8MAAAAC/crying-cute.gif",
    "https://c.tenor.com/ouRN_UCS-cIAAAAC/argh-anime-haikyuu-yu-nishinoya.gif",
    "https://c.tenor.com/i3uWiBCMgh8AAAAC/sad-aesthetic.gif",
    "https://c.tenor.com/lBlcEFqoDnEAAAAC/annoyed-anime.gif",
    "https://c.tenor.com/2YmFNn9rx1EAAAAC/bakugo-angry-cake.gif",
    "https://c.tenor.com/lh02oyf-wmYAAAAC/anime-concerned.gif",
    "https://c.tenor.com/DpgTBEePAp0AAAAC/ugh-a-certain-scientific-railgun.gif"
]

async def addRollStat():
    data = botstatsDB.find_one()
    amountRaf = data["amountRaf"] + 1
    objectid = ObjectId("60904caebabb801e274deb5c")
    botstatsDB.update_one({"_id":objectid}, {"$set":{"amountRaf":amountRaf}})

async def addUniqueUser():
    data = botstatsDB.find_one()
    uniqueUser = data["uniqueUser"] + 1
    objectid = ObjectId("60904caebabb801e274deb5c")
    botstatsDB.update_one({"_id":objectid}, {"$set":{"uniqueUser":uniqueUser}})
   

@client.command()
async def lsapp(ctx, member:discord.Member = None):
    if ctx.message.author.id == 401939531970117643:
        if member == None:
            member = ctx.author

        achDB.update_one({"id":member.id}, {"$set":{"lsadded":True}})
        await ctx.send(f"{member} ls was approved")
    else:
        em = discord.Embed(title = f"Lard Check - {member.name}\nOnly Lard can use this command!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

@client.command()
async def evanapp(ctx, member:discord.Member = None):
    if ctx.message.author.id == 401939531970117643:
        if member == None:
            member = ctx.author

        achDB.update_one({"id":member.id}, {"$set":{"lardapp":True}})
        await ctx.send(f"{member} was approved for profile like")
    else:
        em = discord.Embed(title = f"Lard Check - {member.name}\nOnly Lard can use this command!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

@client.command()
async def rankapp(ctx, member:discord.Member = None):
    if ctx.message.author.id == 401939531970117643:
        if member == None:
            member = ctx.author

        achDB.update_one({"id":member.id}, {"$set":{"rank1":True}})
        await ctx.send(f"{member} was approved for rank 1")
    else:
        em = discord.Embed(title = f"Lard Check - {member.name}\nOnly Lard can use this command!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

@client.command()
async def revapp(ctx, member:discord.Member = None):
    if ctx.message.author.id == 401939531970117643:
        if member == None:
            member = ctx.author

        achDB.update_one({"id":member.id}, {"$set":{"reviewL":True}})
        await ctx.send(f"{member} was approved")
    else:
        em = discord.Embed(title = f"Lard Check - {member.name}\nOnly Lard can use this command!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return


def getPresCol(level):
    if level == 0:
        color = discord.Color.teal()
    else:
        color = discord.Color(random.randint(0,16777215))
    return color


async def addRarityRanking(character,show,rarity):
    if rarity == "common":
        num = 1  
    elif rarity == "uncommon":
        num = 2
    elif rarity == "rare":
        num = 3
    elif rarity == "epic":
        num = 4
    elif rarity == "legendary":
        num = 5
    elif rarity == "hyperlegendary":
        num = 6
    
    charDB.update_one({"name":character, "show":show}, {"$set":{"rarityrank":num}})
    


@client.command()
@commands.has_role("addchars")
async def addCharAC(ctx, name=None, show=None, rarity=None, gif=None):
    if name==None or show==None or gif==None or rarity==None:
        em = discord.Embed(title = f"{cmdPrefix}addChar <name> <show(oneword)> <rarity> <gif>",color = discord.Color.red())
        await ctx.send(embed=em)
        return
    name = name.lower()
    show=show.lower()
    rarity=rarity.lower()
    botstat = botstatsDB.find_one()
    commonNum = charDB.count_documents({"rarity":"common"})
    uncommonNum = charDB.count_documents({"rarity":"uncommon"})
    rareNum = charDB.count_documents({"rarity":"rare"})
    epicNum = charDB.count_documents({"rarity":"epic"})
    legendaryNum = charDB.count_documents({"rarity":"legendary"})
    hyperlegendaryNum = charDB.count_documents({"rarity":"hyperlegendary"})
    charlist = charDB.find().sort("name")
    charlistS = charDB.find().sort("show")
    charname = charDB.find_one({"name":name})
    charshow = charDB.find_one({"show":show})
    if charname in charlist and charshow in charlistS:
        em = discord.Embed(title = f"{name} already in database",color = discord.Color.red())
        await ctx.send(embed=em)
    else:
        showFound = showDB.find_one({'name':show})
        abv = showFound['abv']
        newchar = {"name":name,"show":show,"rarity":rarity,'abv':abv,"gif":gif}
        charDB.insert_one(newchar)
        if rarity == "common":
            plusOne = commonNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numcommon":plusOne}})
        if rarity == "uncommon":
            plusOne = uncommonNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numuncommon":plusOne}})
        if rarity == "rare":
            plusOne = rareNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numrare":plusOne}})
        if rarity == "epic":
            plusOne = epicNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numepic":plusOne}})
        if rarity == "legendary":
            plusOne = legendaryNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numlegendary":plusOne}})
        if rarity == "hyperlegendary":
            plusOne = hyperlegendaryNum+1
            charDB.update_one({"name":name, "show":show}, {"$set":{"raritynumber":plusOne}})
            botstatsDB.update_one({"id":573}, {"$set":{"numhyperlegendary":plusOne}})
        await addRarityRanking(name,show,rarity)
        em = discord.Embed(title = "Success" ,description= f"**Name:** {name}\n**Show:** {show}\n**Rarity:** {rarity}\n**GIF Link:** {gif}",color = getColor(rarity))
        em.set_image(url=gif)
        await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def assignCharAC(ctx,name=None,show=None,member:discord.Member=None):
    if member is None:
        member = ctx.author
    show = show.lower()
    name=name.lower()
    char = charDB.find_one({"name":name,"show":show})
    charname=char["name"]
    charshow=char["show"]
    gif = char["gif"]
    rarity=char["rarity"]
    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":name,"show":show,"rarity":rarity}}})
    
    if rarity == "legendary":
        user = userDB.find_one({"id":member.id})
        try:
            legendaries = user["legendsunlocked"]
            newLeg = legendaries+1
            userDB.update_one({"id":member.id}, {"$set":{"legendsunlocked":newLeg}})
        except:
            userDB.update_one({"id":member.id}, {"$set":{"legendsunlocked":1}})
        

    if rarity == "epic":
        user = userDB.find_one({"id":member.id})
        try:
            epics = user["legunlocked"]
            newepic = epics+1
            userDB.update_one({"id":member.id}, {"$set":{"legunlocked":newepic}})
        except:
            userDB.update_one({"id":member.id}, {"$set":{"legunlocked":1}})
    
    em = discord.Embed(title = f"ACassignChar - {member.name}" ,description= f"**Name:** {charname.capitalize()}\n**Show:** {charshow.capitalize()}\n**Rarity:** {rarity.capitalize()}",color = getColor(rarity))
    em.set_image(url=gif)
    await ctx.send(embed=em)
    return



@client.command()
@commands.has_role("addchars")
async def getCharAC(ctx, name=None, show=None):
    if name is None:
        em = discord.Embed(title = f"{cmdPrefix}getChar <name> <show(oneword)>",color = discord.Color.red())
        await ctx.send(embed=em)
        return
    name=name.lower()
    if show is None:
        char = charDB.find_one({"name":name})
    else:
        show=show.lower()
        char = charDB.find_one({"name":name, "show":show})
    

    charname = char["name"]
    show = char["show"]
    rarity = char["rarity"]
    gif = char["gif"]
    em = discord.Embed(title = f"{name.capitalize()}" ,description= f"**Name:** {name}\n**Show:** {show}\n**Rarity:** {rarity}\n**GIF Link:** {gif}",color = getColor(rarity))
    em.set_image(url=gif)
    await ctx.send(embed=em)


@client.command()
@commands.has_role("changegifs")
async def updateGIFAC(ctx,name=None, show=None, gif=None):
    if name is None or show is None or gif is None:
        em = discord.Embed(title = f"{cmdPrefix}updateGIF <name> <show(oneword)> <gif>",color = discord.Color.red())
        await ctx.send(embed=em)
        return

    
    charFound = charDB.find_one({"name":name,"show":show})
    
    if charFound == None:
        em = discord.Embed(title = f"{name} not found!",color = discord.Color.red())
        await ctx.send(embed=em)
        return

    
    charDB.update_one({"name":name, "show":show}, {"$set":{"gif":gif}})
    em = discord.Embed(title = f"Updated gif for **{name}.**",color = discord.Color.gold())
    em.set_image(url=gif)
    await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def updateRarityAC(ctx,name=None, show=None, rarity=None):
    if name is None or show is None or rarity is None:
        em = discord.Embed(title = f"{cmdPrefix}updateGIF <name> <show(oneword)> <newrarity>",color = discord.Color.red())
        await ctx.send(embed=em)
        return

    charFound = charDB.find_one({"name":name,"show":show})
    oldcharrarity = charFound["rarity"]
    oldraritynum = charFound["raritynumber"]

    charDB.update_one({"name":name, "show":show}, {"$set":{"rarity":rarity}})
    await addRarityRanking(name,show,rarity)

    numRarity = charDB.count_documents({"rarity":rarity})
    botstatsDB.update_one({"id":573}, {"$set":{"numcommon":numRarity+1}})


    charlist = charDB.find({"rarity":oldcharrarity,"raritynumber":{"$gt": oldraritynum}})
    for x in charlist:
        newrarnum = x["raritynumber"] - 1
        locname=x["name"]
        locshow=x["show"]
        charDB.update_one({"name":locname, "show":locshow}, {"$set":{"raritynumber":newrarnum}})



    amountcommons = charDB.count_documents({"rarity":"common"})
    botstatsDB.update_one({"id":573},{"$set":{"numcommon":amountcommons}})
    amountuncommons = charDB.count_documents({"rarity":"uncommon"})
    botstatsDB.update_one({"id":573},{"$set":{"numuncommon":amountuncommons}})
    amountrares = charDB.count_documents({"rarity":"rare"})
    botstatsDB.update_one({"id":573},{"$set":{"numrare":amountrares}})
    amountepics = charDB.count_documents({"rarity":"epic"})
    botstatsDB.update_one({"id":573},{"$set":{"numepic":amountepics}})
    amountlegendaries = charDB.count_documents({"rarity":"legendary"})
    botstatsDB.update_one({"id":573},{"$set":{"numlegendary":amountlegendaries}})
    amounthypers = charDB.count_documents({"rarity":"hyperlegendary"})
    botstatsDB.update_one({"id":573},{"$set":{"numhyperlegendary":amounthypers}})
    
    em = discord.Embed(title = f"Updated rarity for **{name} from {oldcharrarity} to {rarity}.**",color = discord.Color.gold())
    await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def updatelegendariesAC(ctx): 
    userlist = userDB.find({"characters.rarity": "legendary"})
    for x in userlist:
        numLeg = 0
        numChars = len(x["characters"])
        for i in x["characters"]:
            if i["rarity"] == "legendary":
                print(f'{x["name"]},  {i["name"]}')
                numLeg += 1
        userDB.update_one({"id":x["id"]}, {"$set":{"legendsunlocked":numLeg}})
        print(numLeg)

@client.command()
@commands.has_role("addchars")
async def updateepicsAC(ctx): 
    userlist = userDB.find({"characters.rarity": "epic"})
    for x in userlist:
        numLeg = 0
        numChars = len(x["characters"])
        for i in x["characters"]:
            if i["rarity"] == "epic":
                print(f'{x["name"]},  {i["name"]}')
                numLeg += 1
        userDB.update_one({"id":x["id"]}, {"$set":{"legunlocked":numLeg}})
        print(numLeg)

@client.command()
@commands.has_role("addchars")
async def updateNameAC(ctx,oldname=None, show=None, newname=None):
    if oldname is None or show is None or newname is None:
        em = discord.Embed(title = f"{cmdPrefix}updateRarity <name> <show(oneword)> <newname>",color = discord.Color.red())
        await ctx.send(embed=em)
        return
    
    charDB.update_one({"name":oldname, "show":show}, {"$set":{"name":newname}})
    usersWithChar = userDB.find({"characters":{"$elemMatch": {"name":oldname}}})

    charnewName = charDB.find_one({"name":newname})
    for x in usersWithChar:
        userDB.update_one({"id":x["id"]}, {"$pull":{"characters":{"name":oldname}}})
        userDB.update_one({"id":x["id"]}, {"$addToSet":{"characters":{"name":newname,"show":charnewName["show"],"rarity":charnewName["rarity"]}}})

    em = discord.Embed(title = f"Updated name to {newname} for **{oldname}.**",color = discord.Color.gold())
    await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def updateShowAC(ctx,name=None, show=None, newshow=None):
    if name is None or show is None or newshow is None:
        em = discord.Embed(title = f"{cmdPrefix}updateRarity <name> <show(oneword)> <newshow>",color = discord.Color.red())
        await ctx.send(embed=em)
        return
    
    charDB.update_one({"name":name, "show":show}, {"$set":{"show":newshow}})
    em = discord.Embed(title = f"Updated show to {newshow} for **{name}.**",color = discord.Color.gold())
    await ctx.send(embed=em)

def randnum(max):
    randnum1 = random.randint(1,2)
    if randnum1 == 1:
        randseed = random.randint(1,5000)
    if randnum1 == 2:
        randseed = random.randint(5001,10000)
    random.seed(randseed)
    randomnum = random.randint(1,max)
    return randomnum    

@client.command()
@commands.has_role("addchars")
async def addShowAC(ctx, name= None,abv = None,title = None, thumbnail=None):
    name=name.lower()
    abv = abv.lower()
    newshow = {"name":name,"abv":abv,"title":title,"thumbnail":thumbnail}
    showDB.insert_one(newshow)

    em = discord.Embed(title = f"{title.title()} added",color = discord.Color.gold())
    em.set_thumbnail(url=thumbnail)
    await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def addLSAC(ctx,link=None,desc=None):
    num = loadingScreenDB.count_documents({})+1
    newLS = {"number":num,"gif":link,"description":desc}
    loadingScreenDB.insert_one(newLS)
    em = discord.Embed(title = "Success" ,description= f"**Number:** {num}\n**GIF Link:** {link}\n**Desc:** {desc}",color = getColor('legendary'))
    em.set_image(url=link)
    await ctx.send(embed=em)

@client.command()
@commands.has_role("addchars")
async def setmoneyAC(ctx,amount=None,member:discord.Member=None):
    if amount == None:
        em = discord.Embed(title = f"{cmdPrefix}setmoneyAC money member",color = discord.Color.red())
        await ctx.send(embed=em)
        return
    if member == None:
        member = ctx.author
    
    amount = int(amount)
    user = userDB.find_one({"id":member.id})
    oldbal = user["money"]
    userDB.update_one({"id":member.id}, {"$set":{"money":user["money"]+amount}})

    user = userDB.find_one({"id":member.id})
    em = discord.Embed(title = f"{member.name}'s' balance:\nOld: ${oldbal}\nNew: ${user['money']}",color = discord.Color.gold())
    await ctx.send(embed=em)

#User Commands
###################################################################


rarities = ["common", "uncommon", "rare","epic","legendary"]
chance = [52,32,10,5,1]

#chance =[100,0,0,0,0] #for testing
#chance=[0,0,0,0,100] #for testing

def addfunds(member,amount):
    user = shopDB.find_one({"id":member.id})
    shopDB.update_one({"id":member.id}, {"$inc":{"money":amount}})

    if user["money"] >= 100000:
        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
        return

def addfundsdupe(member,rarity):
    user = shopDB.find_one({"id":member.id})
    if rarity == "common":
        amount = 150
    if rarity == "uncommon":
        amount = 250
    if rarity == "rare":
        amount = 500
    if rarity == "epic":
        amount = 1500
    if rarity == "legendary":
        amount = 5000

    shopDB.update_one({"id":member.id}, {"$inc":{"money":amount}})
    if user["money"] >= 100000:
        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
        return

def getpricedupe(rarity):
    if rarity == "common":
        amount = 50
    if rarity == "uncommon":
        amount = 100
    if rarity == "rare":
        amount = 200
    if rarity == "epic":
        amount = 750
    if rarity == "legendary":
        amount = 3000
    return amount


def addfundspres(member,level):
    botStats = botstatsDB.find_one({"id":573})
    sznDB.update_one({"id":member.id}, {"$inc":{"xp":3 * level}})
    shopDB.update_one({"id":member.id}, {"$inc":{"money":level*botStats['presBonus']}})


def updateLegendaryandEpic(member):
        user = userDB.find_one({"id":member.id})
        Leg=0
        Ep=0
        for x in user["characters"]:
            if x["rarity"] == "legendary":
                Leg+=1
            if x["rarity"] == "epic":
                Ep+=1
                
        userDB.update_one({"id":member.id}, {"$set":{"legendsunlocked":Leg}})
        userDB.update_one({"id":member.id}, {"$set":{"legunlocked":Ep}})

def updateCharsAmount(member):
        user = userDB.find_one({"id":member.id})
        userchars = len(user["characters"])
        userDB.update_one({"id":user["id"]}, {"$set":{"charsunlocked":userchars}})

def checkDupes(member,name):
        duplicate = "New"
        user = userDB.find_one({"id":member.id})
        try:
            userchars = user["characters"]
        except:
            return duplicate
        for x in userchars:
            if x["name"] == name:
                duplicate = "Duplicate"
                break
        return duplicate

@client.command(aliases = ["acr","ACraffle","ACR","Acr","Acraffle"])
@commands.cooldown(1, 10, commands.BucketType.user)
async def acraffle(ctx):
    member = ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACraffle - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)
    
    try:
        user = userDB.find_one({"id":member.id})
    except:
        pass

    currenttime = datetime.datetime.utcnow()
    try:
        cooldownVal = user['acrCooldown']
        hours_added = datetime.timedelta(hours=1)
        futureTime = cooldownVal + hours_added
        if currenttime < futureTime:
            cooldownTimer = futureTime - currenttime
            #print(cooldownTimer)
            # print(cooldownTimer.seconds)
            em = discord.Embed(title = f"ACraffle Cooldown - {ctx.author.name}",description = '**!acr** is on cooldown for you.',color = discord.Color.teal())
            if cooldownTimer.seconds >= 3600:
                em.add_field(name = "Time Left", value = f'**{int(cooldownTimer.seconds/3600)}** hours **{int(cooldownTimer.seconds/60) - (60*int(cooldownTimer.seconds/3600))}** minutes')
            elif cooldownTimer.seconds < 3600 and cooldownTimer.seconds >= 60:
                em.add_field(name = "Time Left", value = '**{:.2f}** minutes'.format(cooldownTimer.seconds / 60))
                #em.add_field(name = "Time Left", value = f'**{int(cooldownTimer.seconds/60)}** minutes **{cooldownTimer.seconds}** seconds')
            else:
                em.add_field(name = "Time Left", value = f'**{cooldownTimer.seconds}** seconds')
            em.set_thumbnail(url = ctx.author.avatar_url)
            try:
                if user['lstype'] == "Select":
                    loadingscreen = user['currentloadingscreen']
                    em.set_image(url = loadingscreen)
                elif user['lstype'] == "Random":
                    screenList = []
                    screens = user['loadingscreens']
                    it = 0
                    for var in screens:
                        it+=1
                        screenList.append(int(var['number']))
                    it = it-1
                    randScreen = random.randint(0,it)
                    screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
                    em.set_image(url = screenFound['gif'])
            except:
                pass
            await ctx.send(embed = em)
            await send_logs_cooldown(ctx.author,ctx.message.guild)
            return
    except:
        pass
    

    em = discord.Embed(title = f"ACraffle - {member.name.capitalize()}",description="Press Raffle to roll for a character!\nCommon, Uncommon, Rare, Epic, Legendary",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)

    secondem = discord.Embed(title = f"ACraffle\nRolling character for {member.name.capitalize()}...",color = discord.Color.teal())
    secondem.set_thumbnail(url = member.avatar_url)

    try:
        if user['lstype'] == "Select":
            loadingscreen = user['currentloadingscreen']
            em.set_image(url = loadingscreen)
            secondem.set_image(url = loadingscreen)
        elif user['lstype'] == "Random":
            screenList = []
            screens = user['loadingscreens']
            it =0
            for var in screens:
                it+=1
                screenList.append(int(var['number']))
            it = it-1
            randScreen = random.randint(0,it)
            screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
            em.set_image(url = screenFound['gif'])
            secondem.set_image(url = screenFound['gif'])
    except:
        pass


    raffleComp = [
        [
            Button(style=ButtonStyle.green,label='Raffle'),
            Button(style=ButtonStyle.red,label='Cancel')
        ]        

    ]

    message = await ctx.send(embed=em, components=raffleComp)

    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    
    while True:
        try:
            event = await client.wait_for("interaction",check=checkauthor(member),timeout=10.0)

            if event.component.label == f'Raffle':
                clrButtons = []
                await message.edit(embed=secondem,components=clrButtons)

                userDB.update_one({"id":member.id}, {"$set":{"acrCooldown":currenttime}})
                result = random.choices(rarities,chance,k=1)
                
                await addRollStat()

                await asyncio.sleep(2)
                
                newuser = True
                try:
                    userChars = user["characters"]
                    newuser = False
                except:
                    pass

                if newuser == True:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACraffle - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n1 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n{3*level + 3} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n{3*level + 3} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus")
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n3 SP")
                        em.add_field(name=f"**Thanks for using ACraffle!**",value=f"If you are new and want to get started use **!actutorial (!actut)**",inline=False)
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)
                        
                else:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACraffle - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n1 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n{3*level + 3} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n{3*level + 3} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus")
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacr']} for raffling\n3 SP")
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)

                
                duperate = int(botStats["duperate"])
                for x in range(len(rarities)):
                    if result[0] == rarities[x]:
                        #print(rarities[x])
                        max = charDB.count_documents({"rarity":rarities[x]})
                        randomInt = random.randint(1,max) 
                        Char = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                        try:
                            ublocks = blockDB.find_one({'id':member.id})
                            blist = ublocks['blocklist']
                            newblist = []
                            for itm in blist:
                                newblist.append(itm['show'])
                        except:
                            newblist=[]
                        
                        if rarities[x] == 'legendary':
                            legmax = charDB.count_documents({"rarity":"legendary"})
                            legsun = user['legendsunlocked'] 
                            if legmax != legsun:
                                while checkDupes(member,Char["name"]) == "Duplicate":
                                    if checkDupes(member,Char["name"]) == "Duplicate":
                                        random.seed(random.randint(1,5000000))
                                        randomInt = random.randint(1,max) 
                                        Char = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                                    if Char['show'] in newblist:
                                        random.seed(random.randint(1,5000000))
                                        randomInt = random.randint(1,max) 
                                        Char = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                        else:
                            for y in range(duperate):
                                if checkDupes(member,Char["name"]) == "Duplicate":
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                                if Char['show'] in newblist:
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                                else:
                                    break

                        isDupe = checkDupes(member,Char["name"])
                        showFound = showDB.find_one({"name":Char["show"]})
                        oldChar = Char
                        if isDupe == "Duplicate":
                            charlist = charDB.find({'show':showFound['name'],'rarity':Char['rarity']})
                            for x in charlist:
                                if isDupe == "Duplicate":
                                    Char = charDB.find_one({"name":x['name']})
                                    isDupe = checkDupes(member,Char["name"])
                                else:
                                    break
                        
                        if isDupe == "Duplicate":
                            Char = oldChar

                        pres = presDB.find_one({'id':member.id})
                        level = 0
                        if pres != None:
                            pshows = pres['shows']
                            for shw in pshows:
                                if Char['show'] == shw['show']:
                                    level = shw['tier']
                                    break


                        await outputEmbed(Char["name"],Char["rarity"],showFound["title"],Char["gif"],getColor(Char["rarity"]), isDupe,level)
                        try:
                            await send_logs_acraffle_more(member, guild, "acraffle",Char["name"], isDupe,Char["rarity"])
                        except:
                            pass
                        
                        userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":Char["name"],"show":Char["show"],"rarity":Char["rarity"]}}})

                        updateLegendaryandEpic(member)
                        updateCharsAmount(member)
                        
                        addfunds(member,botStats["amountacr"])      #base acr value 
                        if isDupe == "Duplicate" and level == 0:    #duplicate no pres  
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe == "Duplicate" and level != 0:  #duplicate and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe != "Duplicate" and level != 0:  #new and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])
                        
                        sznDB.update_one({"id":member.id}, {"$inc":{"xp":3}})
                        return

            elif event.component.label == f'Cancel':
                buttons = []
                await message.edit(components=buttons)

                return

                        
        except:
            break
    buttons = []
    await message.edit(components=buttons)

    return



def setRandTime():
    randseed = random.randint(1,1000)
    random.seed(randseed)
    randTime = random.randint(14400,21600)
    return randTime

acrpRarities = ["rare","epic","legendary"]
acrpChance = [66,30,4]


@client.command(aliases = ["acrp","ACraffleplus","ACRP","acrplus",'acrafflep','Acraffleplus','Acrp'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def acraffleplus(ctx):
    member = ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline == False:
        em = discord.Embed(title = f"ACraffleplus - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)

    try:
        user = userDB.find_one({"id":member.id})
    except:
        pass


    currenttime = datetime.datetime.utcnow()
    #print(currenttime)
    try:
        #cooldownVal = user['acrpCooldown']
        endcooldown = user['acrpCooldown']
        #print(endcooldown)
        if currenttime < endcooldown:
            cooldownTimer = endcooldown - currenttime
            #print(cooldownTimer)
            # print(cooldownTimer.seconds)
            em = discord.Embed(title = f"ACraffleplus Cooldown - {ctx.author.name}",description = '**!acrp** is on cooldown for you.',color = discord.Color.teal())
            if cooldownTimer.seconds >= 3600:
                em.add_field(name = "Time Left", value = f'**{int(cooldownTimer.seconds/3600)}** hours **{int(cooldownTimer.seconds/60) - (60*int(cooldownTimer.seconds/3600))}** minutes')
            elif cooldownTimer.seconds < 3600 and cooldownTimer.seconds >= 60:
                em.add_field(name = "Time Left", value = '**{:.2f}** minutes'.format(cooldownTimer.seconds / 60))
                #em.add_field(name = "Time Left", value = f'**{int(cooldownTimer.seconds/60)}** minutes **{cooldownTimer.seconds}** seconds')
            else:
                em.add_field(name = "Time Left", value = f'**{cooldownTimer.seconds}** seconds')
            em.set_thumbnail(url = ctx.author.avatar_url)
            try:
                if user['lstype'] == "Select":
                    loadingscreen = user['currentloadingscreen']
                    em.set_image(url = loadingscreen)
                elif user['lstype'] == "Random":
                    screenList = []
                    screens = user['loadingscreens']
                    it =0
                    for var in screens:
                        it+=1
                        screenList.append(int(var['number']))
                    it = it-1
                    randScreen = random.randint(0,it)
                    screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
                    em.set_image(url = screenFound['gif'])
            except:
                pass
            await ctx.send(embed = em)
            await send_logs_cooldown(ctx.author,ctx.message.guild)
            return
    except:
        pass


    em = discord.Embed(title = f"ACraffleplus - {member.name.capitalize()}",description="Press Raffle to roll for a character!\nRare, Epic, Legendary",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)

    secondem = discord.Embed(title = f"ACraffleplus\nRolling character for {member.name.capitalize()}...",color = discord.Color.teal())
    secondem.set_thumbnail(url = member.avatar_url)
    
    

    try:
        if user['lstype'] == "Select":
            loadingscreen = user['currentloadingscreen']
            em.set_image(url = loadingscreen)
            secondem.set_image(url = loadingscreen)
        elif user['lstype'] == "Random":
            screenList = []
            screens = user['loadingscreens']
            it =0
            for var in screens:
                it+=1
                screenList.append(int(var['number']))
            it = it-1
            randScreen = random.randint(0,it)
            screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
            em.set_image(url = screenFound['gif'])
            secondem.set_image(url = screenFound['gif'])
    except:
        pass    

    raffleComp = [
        [
            Button(style=ButtonStyle.green,label='Raffle'),
            Button(style=ButtonStyle.red,label='Cancel')
        ]        
    ]

    message = await ctx.send(embed=em, components=raffleComp)

    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    
    while True:
        try:
            event = await client.wait_for("interaction",check=checkauthor(member),timeout=10.0)

            if event.component.label == f'Raffle':
                clrButtons = []
                await message.edit(embed=secondem,components=clrButtons)

                hours_added = datetime.timedelta(seconds=setRandTime())
                futureTime = currenttime + hours_added

                userDB.update_one({"id":member.id}, {"$set":{"acrpCooldown":futureTime}})
                result = random.choices(acrpRarities,acrpChance,k=1)

                await addRollStat()

                await asyncio.sleep(2)

                newuser = True
                try:
                    userChars = user["characters"]
                    newuser = False
                except:
                    pass

                if newuser == True:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACraffleplus - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n3 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level+5} SP (Prestige)\n${level * botStats['presBonus'] + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level + 5} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus") 
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n5 SP")
                        em.add_field(name=f"**Thanks for using ACraffle!**",value=f"If you are new and want to get started use **!actutorial (!actut)**",inline=False)
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)
                        
                else:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACraffleplus - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n3 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level+5} SP (Prestige)\n${level * botStats['presBonus'] + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level + 5} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus") 
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n5 SP")
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)

                
                duperate = int(botStats["duperate"])
                for x in range(len(acrpRarities)):
                    if result[0] == acrpRarities[x]:
                        #print(rarities[x])
                        max = charDB.count_documents({"rarity":acrpRarities[x]})
                        randomInt = random.randint(1,max) 
                        Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                        try:
                            ublocks = blockDB.find_one({'id':member.id})
                            blist = ublocks['blocklist']
                            newblist = []
                            for itm in blist:
                                newblist.append(itm['show'])
                        except:
                            newblist=[]
                        if acrpRarities[x] == 'legendary':
                            legmax = charDB.count_documents({"rarity":"legendary"})
                            legsun = user['legendsunlocked'] 
                            if legmax != legsun:
                                while checkDupes(member,Char["name"]) == "Duplicate":
                                    if checkDupes(member,Char["name"]) == "Duplicate":
                                        random.seed(random.randint(1,5000000))
                                        randomInt = random.randint(1,max) 
                                        Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                    if Char['show'] in newblist:
                                        random.seed(random.randint(1,5000000))
                                        randomInt = random.randint(1,max) 
                                        Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                        else:
                            for y in range(duperate):
                                if checkDupes(member,Char["name"]) == "Duplicate":
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                if Char['show'] in newblist:
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                else:
                                    break


                        showFound = showDB.find_one({"name":Char["show"]})

                        isDupe = checkDupes(member,Char["name"])

                        oldChar = Char
                        if isDupe == "Duplicate":
                            charlist = charDB.find({'show':showFound['name'],'rarity':Char['rarity']})
                            for x in charlist:
                                if isDupe == "Duplicate":
                                    Char = charDB.find_one({"name":x['name']})
                                    isDupe = checkDupes(member,Char["name"])
                                else:
                                    break
                                
                        
                        if isDupe == "Duplicate":
                            Char = oldChar

                        pres = presDB.find_one({'id':member.id})
                        level = 0
                        if pres != None:
                            pshows = pres['shows']
                            for shw in pshows:
                                if Char['show'] == shw['show']:
                                    level = shw['tier']
                                    break


                        await outputEmbed(Char["name"],Char["rarity"],showFound["title"],Char["gif"],getColor(Char["rarity"]), isDupe,level)
                        try:
                            await send_logs_acraffle_more(member, guild, "acraffleplus",Char["name"], isDupe,Char["rarity"])
                        except:
                            #await send_logs_error(member,"acr worked but dont have manage permissions")
                            pass
                        addfunds(member,botStats["amountacrp"])
                        userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":Char["name"],"show":Char["show"],"rarity":Char["rarity"]}}})
                        updateLegendaryandEpic(member)
                        updateCharsAmount(member)

                        if isDupe == "Duplicate" and level == 0:    #duplicate no pres  
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe == "Duplicate" and level != 0:  #duplicate and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe != "Duplicate" and level != 0:  #new and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])

                        sznDB.update_one({"id":member.id}, {"$inc":{"xp":5}})
                       

                        return

            elif event.component.label == f'Cancel':
                buttons = []
                await message.edit(components=buttons)

                return
        except:
            break

    buttons = []
    await message.edit(components=buttons)

    return


@client.command(aliases= ['acrv','ACRV','Acrv','ACRAFFLEVOTE'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def acrafflevote(ctx):
    member = ctx.author
    guild=ctx.message.guild
    botStats=botstatsDB.find_one({'id':573})
    if botStats['botOffline']==True or botOnline == False:
        em = discord.Embed(title = f"ACrafflevote - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createvoter(member)
    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)

    userProf = voteDB.find_one({'id':member.id})
    creds = userProf['credits']
    

    
    if creds <= 0:
        buttons = [
                    [
                    Button(style=ButtonStyle.green,label=f'Raffle Once',disabled=True),
                    Button(style=ButtonStyle.grey,label=f'Credits: {creds}',disabled=True),
                    ]
        ]
    else:
        buttons = [
                [
                Button(style=ButtonStyle.green,label=f'Raffle Once'),
                    Button(style=ButtonStyle.grey,label=f'Credits: {creds}',disabled=True),
                ]
        ]

    em = discord.Embed(title = f"ACrafflevote - {member.name}",description = f"**Vote Credits: {creds}**\n(You can raffle {creds} times!)\nTo get vote credits do **!acvote**",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)

    secondem = discord.Embed(title = f"ACrafflevote\nRolling character for {member.name.capitalize()}...",color = discord.Color.teal())
    secondem.set_thumbnail(url = member.avatar_url)

    user = userDB.find_one({"id":member.id})

    try:
        if user['lstype'] == "Select":
            loadingscreen = user['currentloadingscreen']
            em.set_image(url = loadingscreen)
            secondem.set_image(url = loadingscreen)
        elif user['lstype'] == "Random":
            screenList = []
            screens = user['loadingscreens']
            it =0
            for var in screens:
                it+=1
                screenList.append(int(var['number']))
            it = it-1
            randScreen = random.randint(0,it)
            screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
            em.set_image(url = screenFound['gif'])
            secondem.set_image(url = screenFound['gif'])
    except:
        pass    
    
    
    message = await ctx.send(embed = em,components=buttons)


    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    
  
    while True:
        try:
            event = await client.wait_for("interaction",check=checkauthor(member),timeout=10.0)

            if event.component.label == f'Raffle Once':
                buttons=[]
                await event.respond(content='',embed=em,components=buttons,type=7)
                voteDB.update_one({"id":member.id}, {"$inc":{"credits":-1}})


                result = random.choices(acrpRarities,acrpChance,k=1)
            
                
                await message.edit(embed=secondem)


                await asyncio.sleep(2)

                newuser = True
                try:
                    userChars = user["characters"]
                    newuser = False
                except:
                    pass


                if newuser == True:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACrafflevote - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n5 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level+10} SP (Prestige)\n${level * botStats['presBonus'] + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level + 10} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus") 
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n10 SP")
                        em.add_field(name=f"**Thanks for using ACraffle!**",value=f"If you are new and want to get started use **!actutorial (!actut)**",inline=False)
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)
                        
                else:
                    async def outputEmbed(name,rarity,show,gif,color,duplicate,level):
                        em = discord.Embed(title = f"ACrafflevote - {member.name} got {name.capitalize()}",color = color)
                        em.add_field(name=f"**Details**",value=f"Show: **{show}**\nRarity: **{rarity.capitalize()}**\n**{duplicate}**")
                        if isDupe == "Duplicate" and level == 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n${getpricedupe(Char['rarity'])} for duplicate\n5 SP")
                        elif isDupe == "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level+10} SP (Prestige)\n${level * botStats['presBonus'] + getpricedupe(Char['rarity'])} Prestige Bonus")
                        elif isDupe != "Duplicate" and level != 0:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n{3*level + 10} SP (Prestige)\n${botStats['presBonus']*level + getpricedupe(Char['rarity'])} Prestige Bonus")
                        else:
                            em.add_field(name=f"**Money**",value=f"${botStats['amountacrp']} for raffling\n10 SP")
                        em.set_image(url=gif)
                        em.set_thumbnail(url = member.avatar_url)
                        acraffleNote = botStats["acraffleNote"]
                        em.set_footer(text=f"Version {versionNumber} - {acraffleNote} - See {ouptputprefix(ctx)}acan")
                        await message.edit(embed=em)

                await addRollStat()
                
                duperate = int(botStats["duperate"])
                for x in range(len(acrpRarities)):
                    if result[0] == acrpRarities[x]:
                        #print(rarities[x])
                        max = charDB.count_documents({"rarity":acrpRarities[x]})
                        randomInt = random.randint(1,max) 
                        Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                        try:
                            ublocks = blockDB.find_one({'id':member.id})
                            blist = ublocks['blocklist']
                            newblist = []
                            for itm in blist:
                                newblist.append(itm['show'])
                        except:
                            newblist=[]
                        if acrpRarities[x] == 'legendary':
                            while checkDupes(member,Char["name"]) == "Duplicate":
                                if checkDupes(member,Char["name"]) == "Duplicate":
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                if Char['show'] in newblist:
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                        else:
                            for y in range(duperate):
                                if checkDupes(member,Char["name"]) == "Duplicate":
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                if Char['show'] in newblist:
                                    random.seed(random.randint(1,5000000))
                                    randomInt = random.randint(1,max) 
                                    Char = charDB.find_one({"rarity":acrpRarities[x], "raritynumber": randomInt})
                                else:
                                    break


                        showFound = showDB.find_one({"name":Char["show"]})

                        isDupe = checkDupes(member,Char["name"])

                        oldChar = Char
                        if isDupe == "Duplicate":
                            charlist = charDB.find({'show':showFound['name'],'rarity':Char['rarity']})
                            for x in charlist:
                                if isDupe == "Duplicate":
                                    Char = charDB.find_one({"name":x['name']})
                                    isDupe = checkDupes(member,Char["name"])
                                else:
                                    break
                                
                        
                        if isDupe == "Duplicate":
                            Char = oldChar

                        pres = presDB.find_one({'id':member.id})
                        level = 0
                        if pres != None:
                            pshows = pres['shows']
                            for shw in pshows:
                                if Char['show'] == shw['show']:
                                    level = shw['tier']

                        await outputEmbed(Char["name"],Char["rarity"],showFound["title"],Char["gif"],getColor(Char["rarity"]), isDupe,level)
                        try:
                            await send_logs_acraffle_more(member, guild, "acrafflevote",Char["name"], isDupe,Char["rarity"])
                        except:
                            # await send_logs_error(member,"acr worked but dont have manage permissions")
                            pass
                        addfunds(member,botStats["amountacrp"])
                        userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":Char["name"],"show":Char["show"],"rarity":Char["rarity"]}}})
                        updateLegendaryandEpic(member)
                        updateCharsAmount(member)

                        if isDupe == "Duplicate" and level == 0:    #duplicate no pres  
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe == "Duplicate" and level != 0:  #duplicate and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])
                        elif isDupe != "Duplicate" and level != 0:  #new and pres
                            addfundspres(member,level)
                            addfundsdupe(member, Char['rarity'])

                        sznDB.update_one({"id":member.id}, {"$inc":{"xp":10}})
                        return
                                
                break

        except:
            break


    buttons = []
    await message.edit(components=buttons)

    return

@client.command(aliases=['act','ACT','ACtrade'])
@commands.cooldown(1, 1, commands.BucketType.user)
async def actrade(ctx, member:discord.Member = None, characterGive=None,characterRecieve=None ):
    commanduser = ctx.author
    guild=ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACtrade - {commanduser.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed = em)
        return
    
    if member is None:
        em = discord.Embed(title = "ACtrade",description=f"Allows you to trade a character of the same rarity to another person in the server for a character of the same rarity.\nSyntax: **{ouptputprefix(ctx)}actrade  @user  *characterYouGive characterYouRecieve***\nExample: **!actrade @user *levi armin***",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    
    if characterGive is None:
        em = discord.Embed(title = "ACtrade",description=f"Allows you to trade a character of the same rarity to another person in the server for a character of the same rarity.\nSyntax: **{ouptputprefix(ctx)}actrade  @user  *characterYouGive characterYouRecieve***\nExample: **!actrade @user *levi armin***",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return

    if characterRecieve is None:
        em = discord.Embed(title = "ACtrade",description=f"Allows you to trade a character of the same rarity to another person in the server for a character of the same rarity.\nSyntax: **{ouptputprefix(ctx)}actrade  @user  *characterYouGive characterYouRecieve***\nExample: **!actrade @user *levi armin***",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return

   
    await send_logs_actrade(commanduser, guild, "actrade",member,characterGive,characterRecieve)
   
    characterGive=characterGive.lower()
    characterRecieve=characterRecieve.lower()

    
    
    if member.id == commanduser.id:
        em = discord.Embed(title = "ACtrade",description=f"Can't trade with yourself!!",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    if characterGive == characterRecieve:
        em = discord.Embed(title = "ACtrade",description=f"Can't trade the same character **{characterGive.capitalize()}**!",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return


    characterRecfound = charDB.find_one({"name":characterRecieve})
    characterGivefound = charDB.find_one({"name":characterGive})

    if characterRecfound == None:
        em = discord.Embed(title = "ACtrade",description=f"Character, **{characterRecieve.capitalize()}**, not found.\nFor a list of characters do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    
    if characterGivefound == None:
        em = discord.Embed(title = "ACtrade",description=f"Character, **{characterGive.capitalize()}**, not found.\nFor a list of characters do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    
    # userhasChar = False
    # memberhasChar = False
    guild = ctx.message.guild
    await createuser(commanduser,guild)
    await createuser(member,guild)
    await createachuser(member)
    await createachuser(commanduser)
    

    userhasChar = userDB.find_one({"id":commanduser.id, "characters":{"$elemMatch": {"name":characterGive}}})
    memberhasChar = userDB.find_one({"id":member.id, "characters":{"$elemMatch": {"name":characterRecieve}}})

    userProf = userDB.find_one({"id":commanduser.id})
    userhasHL = False
    try:
        userChars = userProf['characters']
    except:
        pass
    for x in userChars:
        if characterGivefound["show"] == x["show"]:
            if x["rarity"] == "hyperlegendary":
                userhasHL = True
                break


    userpres = presDB.find_one({'id':commanduser.id})
    if userpres == None:
        userisPres = False
    else:
        userisPres = False
        preslist = userpres['shows']
        for shws in preslist:
            if shws['show'] == characterGivefound['show']:
                userisPres = True
        


    memberProf = userDB.find_one({"id":member.id})
    memberhasHL = False
    try:
        memberChars = memberProf['characters']
    except:
        pass
    
    for x in memberChars:
        if characterRecfound["show"] == x["show"]:
            if x["rarity"] == "hyperlegendary":
                memberhasHL = True
                break
    
    memberpres = presDB.find_one({'id':member.id})
    if memberpres == None:
        memberisPres = False
    else:
        memberisPres = False
        preslist = memberpres['shows']
        for shws in preslist:
            if shws['show'] == characterRecfound['show']:
                memberisPres = True


    if userhasChar is None:
        em = discord.Embed(title = "ACtrade",description=f"{commanduser.name.capitalize()} doesn't have {characterGive.capitalize()} unlocked.",color = discord.Color.teal())
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return

    if memberhasChar is None:
        em = discord.Embed(title = "ACtrade",description=f"{member.name.capitalize()} doesn't have {characterRecieve.capitalize()} unlocked.",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    if characterRecfound['rarity'] != characterGivefound['rarity']:
        em = discord.Embed(title = "ACtrade",description=f"**{characterGive.capitalize()}** is not the same rarity as **{characterRecieve.capitalize()}**.",color = discord.Color.teal())
        em.add_field(name="You can only trade characters of the same rarity.",value=f"For example:\nCommon for Common")
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return

    if characterRecfound == "hyperlegendary" or characterGivefound == "hyperlegendary":
        em = discord.Embed(title = "ACtrade",description=f"**Hyper Legendaries can't be traded**!",color = discord.Color.teal())
        # em.add_field(name="Trade Between:",value=f"{commanduser.name.capitalize()} and {member.name.capitalize()}")
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    

    characterRecieveProf = charDB.find_one({"name":characterRecieve})
    characterGiveProf = charDB.find_one({"name":characterGive})

    charrecievename = characterRecieveProf["name"]
    chargivename = characterGiveProf["name"]

    charrecieveshow = characterRecieveProf["show"]
    chargiveshow = characterGiveProf["show"]
    
    charrecieverarity = characterRecieveProf["rarity"]
    chargiverrarity = characterGiveProf["rarity"]

    maxRar = charDB.count_documents({"rarity":charrecieverarity})

    rcp = 0
    rcm = 0
    for chars in userProf['characters']:
        if chars['rarity'] == charrecieverarity:
            rcp += 1

    if rcp == maxRar:
        em = discord.Embed(title = "ACtrade",description=f"**{commanduser.name} has the max number of {charrecieverarity.capitalize()} characters. Please prestige at least 1 show in order to trade with this rarity",color = discord.Color.teal())
        # em.add_field(name="Trade Between:",value=f"{commanduser.name.capitalize()} and {member.name.capitalize()}")
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    
    for chars in memberProf['characters']:
        if chars['rarity'] == charrecieverarity:
            rcm += 1

    if rcm == maxRar:
        em = discord.Embed(title = "ACtrade",description=f"**{member.name} has the max number of {charrecieverarity.capitalize()} characters. Please prestige at least 1 show in order to trade with this rarity",color = discord.Color.teal())
        # em.add_field(name="Trade Between:",value=f"{commanduser.name.capitalize()} and {member.name.capitalize()}")
        em.set_thumbnail(url = commanduser.avatar_url)
        await ctx.send(embed=em)
        return
    

    acceptPage = discord.Embed (
        title = f"ACtrade\nRarity: {charrecieverarity.capitalize()}",
        description = f"**{commanduser.name.capitalize()}** gets **{characterRecieve.capitalize()}**\n**{member.name.capitalize()}** gets **{characterGive.capitalize()}**\n\n{member.name.capitalize()} press accept to confirm the trade!\nYou have 20 seconds.",
        colour = getColor("botColor")
    )
    acceptPage.set_thumbnail(url = commanduser.avatar_url)
    
    buttons = [
            
        [
        Button(style=ButtonStyle.green,label='Accept'),
        Button(style=ButtonStyle.red,label='Deny')
        ]

    ]

    message = await ctx.send(embed = acceptPage,components=buttons)
    
    def checkauthor(user):
            return lambda res: res.author == user and res.message == message

    
    while True:
        try:
            res = await client.wait_for('button_click',check = checkauthor(member),timeout=20.0)

            if res.component.label == 'Accept':
                #recheck if both users still have the characters
                check1 = userDB.find_one({"id":commanduser.id, "characters":{"$elemMatch": {"name":characterGive}}})
                check2 = userDB.find_one({"id":member.id, "characters":{"$elemMatch": {"name":characterRecieve}}})
                if check1 is None:
                    blankcomp = []
                    em = discord.Embed(title = "ACtrade",description=f"**Trade Cancelled!**\n{commanduser.name} no longer has {characterGive.capitalize()} in their bank. This probably happened if one of you accepted a trade for the same character while this window was open.",color = discord.Color.teal())
                    em.set_thumbnail(url = commanduser.avatar_url)
                    await message.edit(embed=em,components=blankcomp)
                    return
                
                if check2 is None:
                    blankcomp = []
                    em = discord.Embed(title = "ACtrade",description=f"**Trade Cancelled!**\n{member.name} no longer has {characterGive.capitalize()} in their bank. This probably happened if one of you accepted a trade for the same character while this window was open.",color = discord.Color.teal())
                    em.set_thumbnail(url = member.avatar_url)
                    await message.edit(embed=em,components=blankcomp)
                    return

                #proceed with trade
                userDB.update_one({"id":commanduser.id}, {"$pull":{"characters":{"name":chargivename,"show":chargiveshow,"rarity":chargiverrarity}}})
                userDB.update_one({"id":member.id}, {"$pull":{"characters":{"name":charrecievename,"show":charrecieveshow,"rarity":charrecieverarity}}})
                
                userDB.update_one({"id":commanduser.id}, {"$addToSet":{"characters":{"name":charrecievename,"show":charrecieveshow,"rarity":charrecieverarity}}})
                userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":chargivename,"show":chargiveshow,"rarity":chargiverrarity}}})

                if userProf["currentchar"] == characterGive:
                    userDB.update_one({"id":commanduser.id}, {"$set":{"currentchar":characterRecieve}})
                if memberProf["currentchar"] == characterRecieve:
                    userDB.update_one({"id":member.id}, {"$set":{"currentchar":characterGive}})

                    
                if userhasHL is True and userisPres == False:
                    userDB.update_one({"id":commanduser.id}, {"$pull":{"characters":{"show":chargiveshow,"rarity":"hyperlegendary"}}})
                    hyperlegUser = charDB.find_one({"show":chargiveshow,"rarity":"hyperlegendary"})
                    if userProf["currentchar"] == hyperlegUser["name"]:
                        userDB.update_one({"id":commanduser.id}, {"$set":{"currentchar":characterRecieve}})
                    try:
                        userFavs= userProf["favorites"]
                        for x in userFavs:
                            if x["name"] == hyperlegUser["name"]:
                                userDB.update_one({"id":commanduser.id}, {"$pull":{"favorites":{"name":hyperlegUser["name"]}}})
                    except:
                        pass


                if memberhasHL is True and memberisPres == False:
                    userDB.update_one({"id":member.id}, {"$pull":{"characters":{"show":charrecieveshow,"rarity":"hyperlegendary"}}})
                    hyperlegMember = charDB.find_one({"show":charrecieveshow,"rarity":"hyperlegendary"})
                    if memberProf["currentchar"] == hyperlegMember["name"]:
                        userDB.update_one({"id":member.id}, {"$set":{"currentchar":characterGive}})
                    try:
                        memberFavs= memberProf["favorites"]
                        for x in memberFavs:
                            if x["name"] == hyperlegMember["name"]:
                                userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":hyperlegMember["name"]}}})
                    except:
                        pass
                    
                try:
                    userFavs= userProf["favorites"]
                    for x in userFavs:
                        if x["name"]== chargivename:
                            userDB.update_one({"id":commanduser.id}, {"$pull":{"favorites":{"name":chargivename}}})
                except:
                    pass
                try:
                    memberFavs= memberProf["favorites"]
                    for x in memberFavs:
                        if x["name"]== charrecievename:
                            userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":charrecievename}}})
                except:
                    pass
                
                updateHyperLeg(member)
                updateHyperLeg(commanduser)


                em = discord.Embed(title = f"ACtrade",description=f"Trade successful!",color = getColor("botColor"))
                em.add_field(name="Results:",value=f"{commanduser.name.capitalize()} got **{characterRecieve.capitalize()}** and {member.name.capitalize()} got **{characterGive.capitalize()}**")
                em.set_thumbnail(url = member.avatar_url)

                currenttime = datetime.datetime.utcnow()
                achMem = achDB.find_one({'id':member.id})
                achCom = achDB.find_one({'id':commanduser.id})


                try:
                    cooldownVal = achMem['tradecool']
                    secadded = datetime.timedelta(seconds=30)
                    futureTime = cooldownVal + secadded
                    if currenttime > futureTime:
                        achDB.update_one({"id":member.id}, {"$inc":{'trades':1}})
                        achDB.update_one({"id":member.id}, {"$set":{'tradecool':currenttime}}) 
                except:
                    achDB.update_one({"id":member.id}, {"$inc":{'trades':1}})
                    achDB.update_one({"id":member.id}, {"$set":{'tradecool':currenttime}}) 
                
                try:
                    cooldownVal = achCom['tradecool']
                    secadded = datetime.timedelta(seconds=30)
                    futureTime = cooldownVal + secadded
                    if currenttime > futureTime:
                        achDB.update_one({"id":commanduser.id}, {"$inc":{'trades':1}})
                        achDB.update_one({"id":commanduser.id}, {"$set":{'tradecool':currenttime}}) 
                except:
                    achDB.update_one({"id":commanduser.id}, {"$inc":{'trades':1}})
                    achDB.update_one({"id":commanduser.id}, {"$set":{'tradecool':currenttime}}) 

                newButtons = []

                await res.respond(content='',embed=em,components=newButtons,type=7)
                break
            
            elif res.component.label == 'Deny':
                em = discord.Embed(title = "ACtrade",description=f"Trade denied by {member.name}",color = discord.Color.teal())
                em.set_thumbnail(url = member.avatar_url)
                newButtons = []
                await res.respond(content='',embed=em,components=newButtons,type=7)
                break



        except:
            newcomps = []
            em = discord.Embed(title = "ACtrade",description=f"Trade denied\n{member.name} did not respond within 20 seconds.",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)

            await message.edit(embed=em,components=newcomps)
            break


        return


@client.command(aliases=['acu','ACU','ACupgrade'])
@commands.cooldown(1, 1, commands.BucketType.user)
async def acupgrade (ctx, show=None, rarity=None):
    member = ctx.author
    guild=ctx.message.guild
    
    if show is None or rarity is None:
        em = discord.Embed(title = "ACupgrade",description=f"Allows you to upgrade **4** characters of the same tier and same show to the next tier, those characters will be deleted and you will be given a random character from the next tier for the selected show.\nNote: This only works with the shows with a lot of characters since it's easier to finish the shows with less characters.\nExample: 4 commons -> 1 uncommon\n**Syntax: {ouptputprefix(ctx)}acupgrade *show rarity_to_upgrade_from***",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
    if rarity == "legendary":
        em = discord.Embed(title = "ACupgrade",description=f"Can't upgrade Legendary to HyperLegendary!",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return


    show = show.lower()
    rarity = rarity.lower()
    showfound = False
    #botstats = botstatsDB.find_one({"id":573})
    showlist = showDB.find().sort("name")
    for x in showlist:
        if show == x["name"]:
            showfound=True
            break
        elif show == x["abv"]:
            show = x["name"]
            showfound = True
            break

    if showfound ==False:
            em = discord.Embed(title = f"Show not found.",description = f"Example: *{ouptputprefix(ctx)}acupgrade demonslayer common*\n**Remember** It's easiest to use the Abbreviation for a show such as aot,ds,fmab, etc.",color = discord.Color.teal())
            await ctx.send(embed=em)
            return
    if rarity not in rarities:
            em = discord.Embed(title = f"Rarity not found.",description = f"Example: *{ouptputprefix(ctx)}acupgrade demonslayer common*\nTry pasting one of these:",color = discord.Color.teal())
            raritieslen = len(rarities)
            for x in range(raritieslen-1):
                em.add_field(name=f'\u200b',value=f"{rarities[x]}", inline=False)
            await ctx.send(embed=em)
            return

    
    user = userDB.find_one({"id":member.id})
    userChars = user["characters"]

    amountChars = 0
    charnames = []
    for x in userChars:
        if amountChars < 4:
            if show == x["show"] and rarity == x["rarity"]:
                charnames.append(x["name"])
                amountChars += 1 
        else:
            break
    rarityranklist =  ["common", "uncommon", "rare","epic","legendary"]
    def nextRarity():
        for x in range(len(rarityranklist)):
            if rarity == rarityranklist[x]:
                return(rarityranklist[x+1])

    if amountChars < 4:
        em = discord.Embed(title = "ACupgrade",description=f"**{member.name.capitalize()}** doesn't have enough *{rarity}* characters for **{show.capitalize()}** to upgrade to *{nextRarity()}*.\n**4** are needed to upgrade to the next rarity.",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        charnames.clear()
        return

    max = charDB.count_documents({"show":show,"rarity":nextRarity()})
    
    i = 0
    for x in userChars:
        if x["rarity"] == nextRarity() and show == x["show"]:
            i+=1
    
    if i == max:
        em = discord.Embed(title = "ACupgrade",description=f"**{member.name.capitalize()}** already has all the characters in the **{nextRarity().capitalize()}** category for {show.capitalize()} ",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        charnames.clear()
        return

    
    else:
        charlistNew = []
        for x in userChars:
            if x["show"] == show and x["rarity"] == nextRarity():
                charlistNew.append(x["name"])

        upgradedChar = charDB.find({"show":show,"rarity":nextRarity()})
        for x in upgradedChar:
            if x["name"] not in charlistNew:
                pullChars = []
                num=0
                for y in userChars:
                    if num < 4:
                        if y["show"] == show and y["rarity"] == rarity:
                            pullChars.append(y["name"])
                            num+=1
                    else:
                        break

                for z in range(len(pullChars)):
                    character = charDB.find_one({"name":pullChars[z]})
                    userDB.update_one({"id":member.id}, {"$pull":{"characters":{"name":character["name"],"show":character["show"],"rarity":character["rarity"]}}})
                        
                
                userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":x["name"],"show":x["show"],"rarity":x["rarity"]}}})
                em = discord.Embed(title = "ACupgrade",description=f"**{member.name.capitalize()}** upgraded four **{rarity.capitalize()}** characters to:\nName: **{x['name'].capitalize()}**\nRarity: **{nextRarity().capitalize()}**",color = getColor(nextRarity()))
                em.set_image(url=x["gif"])
                em.set_thumbnail(url = member.avatar_url)
                await ctx.send(embed=em)
                
                updateLegendaryandEpic(member)
                updateCharsAmount(member)
                charnames.clear()
                charlistNew.clear()
                pullChars.clear()
                await send_logs_acraffle(member, guild, "acupgrade",show)
                return

    
def getColor(rarity):
    if rarity == "common":
        color = discord.Color.default()
    elif rarity == "uncommon":
        color = discord.Color.green()
    elif rarity == "rare":
        color = discord.Color.blue()
    elif rarity == "epic":
        color = discord.Color.purple()
    elif rarity == "legendary":
        color = discord.Color.gold()
    elif rarity == "hyperlegendary":
        color = discord.Color(int('ff9cfc', 16))
    elif rarity == "botColor":
        color = discord.Color.teal()
    elif rarity == "loadingscreen":
        color = discord.Color.orange()
    
    return color


def updateHyperLeg(member):
        user = userDB.find_one({"id":member.id})
        HypLeg = 0
        for x in user["characters"]:
            if x["rarity"] == "hyperlegendary":
                HypLeg+=1
                
        userDB.update_one({"id":member.id}, {"$set":{"hypersunlocked":HypLeg}})

@client.command(aliases=['achl','ACHL','AChyperlengendary'])
async def achyperlegendary(ctx ,show=None):
    member = ctx.author
    guild=ctx.message.guild
    if show == None:
        em = discord.Embed(title = "AChyperlegendary",description=f"Allows the user to unlock the **Hyper Legendary** character after collecting all the characters for a single show.\nSyntax: **{ouptputprefix(ctx)}achl *show***\nExample:  **{ouptputprefix(ctx)}achl *attackontitan***\nDo **{ouptputprefix(ctx)}acbs *show*** to see how close you are to finishing a certain show!",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
    #botstat = botstatsDB.find_one({"id":573})
    inshowlist = False 
    showlist = showDB.find().sort("name")
    for p in showlist:
        if show == p["name"]:
            showfound = showDB.find_one({"name":show})
            inshowlist = True
            break
        elif show == p["abv"]:
            show = p["name"]
            showfound = showDB.find_one({"name":show})
            inshowlist = True
            break
    if inshowlist==False:
        em = discord.Embed(title = "AChyperlegendary",description=f"Show: **{show}** not found.\nTo see all shows do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
    
    
    amountCharsinShow = charDB.count_documents({"show":show})
    # print(amountCharsinShow)
    i = 0
    user = userDB.find_one({"id":member.id})
    userchars = user["characters"]
    hashypleg = False
    for p in userchars:
        if p["show"] == show:
            i+=1
        if p["show"] == show and p["rarity"] == "hyperlegendary":
            hashypleg = True


    if (amountCharsinShow-1) == i and hashypleg == False:
        charhypleg = charDB.find_one({"show":show,"rarity":"hyperlegendary"})
        charhyplegname = charhypleg["name"]
        charhyplegshow = charhypleg["show"]
        charhyplegrarity = charhypleg["rarity"]
        charhypleggif = charhypleg["gif"]
        userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":charhyplegname,"show":charhyplegshow,"rarity":charhyplegrarity}}})

        em = discord.Embed(title = f"AChyperlegendary",description= f"**{member.name} claimed a Hyper Legendary!**\n**Name: {charhyplegname.capitalize()}**\nShow: {showfound['title']}\nRarity: {charhyplegrarity.capitalize()}",color = getColor("hyperlegendary"))
        em.set_thumbnail(url = member.avatar_url)
        em.set_image(url=charhypleggif)
        await ctx.send(embed=em)
        await send_logs_acraffle(member, guild, "achyperlegendary",charhyplegname)
        updateHyperLeg(member)
        return

    elif hashypleg == True:
        em = discord.Embed(title = "AChyperlegendary",description=f"{member.name} already claimed the Hyper Legendary for **{showfound['title']}**.",color = getColor("hyperlegendary"))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        em = discord.Embed(title = "AChyperlegendary",description=f"{member.name} doesn't have all other available characters (Common, Uncommon, Rare, Epic, Legendary) unlocked for **{showfound['title']}**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return


@client.command(aliases=["acpc","ACPC","ACPROFILECOLOR"])
async def acprofilecolor(ctx, color = None):
    botstat = botstatsDB.find_one({"id":573})
    member = ctx.author
    guild=ctx.message.guild
    await createuser(member,guild)
    await createshopuser(member,guild)
    user = userDB.find_one({"id":member.id})
    shopStuff = shopDB.find_one({'id':member.id})
    if color == None:
        em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"**Allows you to change the color of your !acprofile.**\nChoose a listed color or enter a HEX code if you want a custom color!\n**Default Colors: Red, Blue, Green, Yellow, Purple.\nHEX Website: https://www.color-hex.com/ \nExample: !acpc red\nExample (HEX): !acpc b3346c\nPrice: ${botstat['colorprice']} - Your Balance: ${shopStuff['money']}**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    try:
        color = color.lower()
    except:
        pass
    
    if color == "red":
        color = "ff0000"
    if color == "blue":
        color = "0000FF"
    if color == "green":
        color = "45ce00"
    if color == "yellow":
        color = "FFFF00"
    if color == "purple":
        color = "aa00e5"

    try:
        colorINT =  int(color, 16)
    except:
        em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"**Invalid Color!**\nChoose a listed color or enter a HEX code if you want a custom color!\n**Default Colors: Red, Blue, Green, Yellow, Purple.\nHEX Website: https://www.color-hex.com/ \nExample: !acpc red\nExample (HEX): !acpc b3346c\nPrice: ${botstat['colorprice']}**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
    
    
    if shopStuff["money"] >= botstat['colorprice']:
        em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"Change Profile Color to **{color}**?\n**Cost: ${botstat['colorprice']}**\nYour Balance: **${shopStuff['money']}**",color = discord.Color(colorINT))
        em.set_thumbnail(url = member.avatar_url)


        buttons = [
            
            [
            Button(style=ButtonStyle.green,label='Confirm'),
            Button(style=ButtonStyle.red,label='Cancel')
            ]

        ]

        message = await ctx.send(embed = em,components=buttons)
        
        def checkauthor(user):
                return lambda res: res.author == user and res.message == message


        while True:
            try:
                res = await client.wait_for('button_click',check = checkauthor(member),timeout=10.0)
                if res.component.label == 'Confirm':
                    em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"Profile Color changed to **{color}**",color = discord.Color(colorINT))
                    em.set_thumbnail(url = member.avatar_url)
                    await message.edit(embed=em)
                    userDB.update_one({"id":member.id}, {"$set":{"profilecolor":colorINT}})
                    shopDB.update_one({"id":member.id}, {"$inc":{"money":-1*botstat['colorprice']}})
                    await send_logs_profile_color(member,guild,"acprofilecolor",color)
                    newcomps = []
                    await res.respond(content='',embed=em,components=newcomps,type=7)
                    return
                if res.component.label == 'Cancel':
                    em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"Profile Color not changed.",color = discord.Color(colorINT))
                    em.set_thumbnail(url = member.avatar_url)
                    await message.edit(embed=em)
                    newcomps = []
                    await res.respond(content='',embed=em,components=newcomps,type=7)
                    return

            except:
                break
   
    else:
        em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"{member.name} does not have **${botstat['colorprice']}**\n{member.name}'s balance: **${shopStuff['money']}**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    
    em = discord.Embed(title = f"ACprofilecolor - {member.name}",description=f"Profile Color NOT changed\n{member.name} did not respond within 10 seconds.",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)
    newcomps=[]
    await message.edit(embed=em,components=newcomps)
    return

def getSznTier(percent):
    if percent >= 90: #Top 90%
        return "⬜️"
    elif percent >= 80 and percent < 90: #Top 80%
        return "⬛️"
    elif percent >= 70 and percent < 80:
        return "🟫"
    elif percent >= 60 and percent < 70:
        return "🟧"
    elif percent >= 50 and percent < 60:
        return "🟥"
    elif percent >= 40 and percent < 50:
        return "🟩"
    elif percent >= 30 and percent < 40:
        return "🟦"
    elif percent >= 20 and percent < 30:
        return "🟪"
    elif percent > 5 and percent < 20: #Top 10
        return "🟨"
    elif percent > 1 and percent <= 5: #Top 10
        return "⭐️"
    elif percent <= 1:
        return "👑"

@client.command(aliases=['acp','ACP','ACprofile'])
async def acprofile(ctx ,member:discord.Member=None):
    if member is None:
        member = ctx.author
    favorites = []
    commandUser = ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACprofile - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)
    await send_logs_profile(commandUser, member, guild, "acprofile")

    user = userDB.find_one({"id":member.id})
    moneyProf = shopDB.find_one({'id':member.id})
    usermoney = moneyProf["money"]

    em = discord.Embed(title = f"ACprofile - {member.name}\nLoading...",color = getColor("botColor"))
    em.set_thumbnail(url = member.avatar_url)
    message = await ctx.send(embed = em)
    hasmal = True
    hasanilist = True
    hasbio = True
    try:
        usermal = user["mal"]
    except:
        hasmal = False

    try:
        useranilist = user["anilist"]
    except:
        hasanilist = False

    try:
        userbio = user["bio"]
    except:
        hasbio = False

    try:
        userfavorites = user["favorites"]
    except:
        userfavorites=[]

    for x in userfavorites:
        if x["name"] is not None:
            favorites.append(x["name"])
    
    gifList = []
    for x in userfavorites:
        char = charDB.find_one({"name":x["name"]})
        gifList.append(char["gif"])

    try:
        charsUnlocked = user["charsunlocked"]
    except:
        charsUnlocked = 0

    try:
        hypersUnl = user["hypersunlocked"]
    except:
        hypersUnl = 0

    # i = userDB.count_documents({"charsunlocked": { "$gt" : charsUnlocked}}) + 1

    #hypers = userDB.count_documents({"hypersunlocked": { "$gt" : hypersUnl}}) + 1
    #totHypUsers = userDB.count_documents({"hypersunlocked": { "$gt" : 0}})

    pres = presDB.find_one({'id':member.id})
    try:
        totPres = pres['totPres']
    except:
        totPres = 0

    presRank = presDB.count_documents({"totPres": { "$gt" : totPres}}) + 1
    totPresUsers = presDB.count_documents({"totPres": { "$gt" : 0}})
    
    botstat = botstatsDB.find_one({"id": 573})
    uniqueuser = botstat["uniqueUser"]
    totalChars = charDB.estimated_document_count()

    charFound = True
    try:
        currentchar = user["currentchar"]
    except:
        pass
    if currentchar == None:
        charFound = False
        try:
            userChars = user['characters']
            for x in userChars:
                currentchar = x['name']
                break
        except:
            em = discord.Embed(title = f"ACprofile",description=f"{member.name} does not have any characters unlocked!\nTo unlock a character to display on your profile do **!acr and !acrp**",color = getColor("botColor"))
            em.set_thumbnail(url = member.avatar_url)
            await message.edit(embed=em)
            return


    # try:
    #     hypleg = user["hypersunlocked"]
    # except:
    #     hypleg = 0

    try:
        leg = user["legendsunlocked"]
    except:
        leg = 0

    # try:
    #     epics = user["legunlocked"]
    # except:
    #     epics = 0


    try:
        color = user["profilecolor"]
    except:
        color = getColor("common")
        
    char = charDB.find_one({"name":currentchar})
    charname=char["name"]
    chargif=char["gif"]
    charshow=char["show"]
    # charrarity=char["rarity"]

    show = showDB.find_one({"name":charshow})
    showOutput = show["title"]

    sznUser = sznDB.find_one({'id':member.id})
    sznRank = sznDB.count_documents({"xp": { "$gt" : sznUser['xp']}}) + 1
    totSzn = sznDB.count_documents({})

    sznPer = math.ceil(100 * (sznRank / totSzn))
    
    if sznPer <= 10:
        rounded = round(sznPer/5)*5
    else:
        sznPer = sznPer - (sznPer % 10)
        rounded = round(sznPer/10)*10
    
    if rounded == 0:
        rounded = 1

    joinVar = ' - '
    
    homeem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
    homeem.add_field(name=f"**Character:  {charname.capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
    homeem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
    if len(favorites) != 0:
        homeem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
    
    homeem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
    homeem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
    
    
    if hasmal is True:
        homeem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
    if hasanilist is True:
        homeem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
    if hasbio is True:
        userbio = str(userbio)
        homeem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

    if color == getColor("common") and charFound == True:
        homeem.set_footer(text=f"Tip: Change profile color with !acpc")
    if color == getColor("common") and charFound == False:
        homeem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")

    homeem.set_thumbnail(url = member.avatar_url)
    homeem.set_image(url=chargif)

    
    
    lenFav = len(favorites)
    if lenFav == 0:
        await message.edit(embed = homeem)
        favorites.clear()
        gifList.clear()
        return
    else:
        if lenFav == 1:
            components = [
                [
                    Select(placeholder=f"Display Character",
                    options=[
                        SelectOption(label=f'{currentchar.capitalize()}',value='option1'),
                        SelectOption(label=f'{favorites[0].capitalize()}',value='option2')
                    ]
                )]
            ]
            

        elif lenFav == 2:
           components = [
                [
                    Select(placeholder=f"Display Character",
                    options=[
                        SelectOption(label=f'{currentchar.capitalize()}',value='option1'),
                        SelectOption(label=f'{favorites[0].capitalize()}',value='option2'),
                        SelectOption(label=f'{favorites[1].capitalize()}',value='option3') 
                    ]
                )]
            ]
        elif lenFav == 3:
            components = [
                [
                    Select(placeholder=f"Display Character",
                    options=[
                        SelectOption(label=f'{currentchar.capitalize()}',value='option1'),
                        SelectOption(label=f'{favorites[0].capitalize()}',value='option2'),
                        SelectOption(label=f'{favorites[1].capitalize()}',value='option3'),
                        SelectOption(label=f'{favorites[2].capitalize()}',value='option4')
                        
                    ]
                )]
            ]
        elif lenFav == 4:
            components = [
                [
                    Select(placeholder=f"Display Character",
                    options=[
                        SelectOption(label=f'{currentchar.capitalize()}',value='option1'),
                        SelectOption(label=f'{favorites[0].capitalize()}',value='option2'),
                        SelectOption(label=f'{favorites[1].capitalize()}',value='option3'),
                        SelectOption(label=f'{favorites[2].capitalize()}',value='option4'),
                        SelectOption(label=f'{favorites[3].capitalize()}',value='option5')
                        
                    ]
                )]
            ]
        
        elif lenFav == 5:
            components = [
                [
                    Select(placeholder=f"Display Character",
                    options=[
                        SelectOption(label=f'{currentchar.capitalize()}',value='option1'),
                        SelectOption(label=f'{favorites[0].capitalize()}',value='option2'),
                        SelectOption(label=f'{favorites[1].capitalize()}',value='option3'),
                        SelectOption(label=f'{favorites[2].capitalize()}',value='option4'),
                        SelectOption(label=f'{favorites[3].capitalize()}',value='option5'),
                        SelectOption(label=f'{favorites[4].capitalize()}',value='option6')
                    ]
                )]
            ]


        await message.edit(embed = homeem,components=components)
        
        def checkauthor(user):
            return lambda res: res.author == user and res.message == message
    
        while True:
            try:
                profileInteract = await client.wait_for('interaction',check = checkauthor(ctx.author),timeout=12.0)

                if profileInteract.values[0] == 'option1':
                    await profileInteract.respond(content='',embed=homeem,type=7)
                    
                elif profileInteract.values[0] == 'option2':
                    newchar = charDB.find_one({'name':favorites[0]})
                    show = showDB.find_one({"name":newchar['show']})
                    showOutput = show["title"]
                    newem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
                    newem.add_field(name=f"**Character:  {newchar['name'].capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
                    newem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
                    if len(favorites) != 0:
                        newem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
                    
                    newem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
                    newem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
                    if hasmal is True:
                        newem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
                    if hasanilist is True:
                        newem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
                    if hasbio is True:
                        userbio = str(userbio)
                        newem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

                    if color == getColor("common") and charFound == True:
                        newem.set_footer(text=f"Tip: Change profile color with !acpc")
                    if color == getColor("common") and charFound == False:
                        newem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")
                    newem.set_image(url=gifList[0])
                    newem.set_thumbnail(url = member.avatar_url)
                    await profileInteract.respond(content='',embed=newem,type=7)


                elif profileInteract.values[0] == 'option3':
                    newchar = charDB.find_one({'name':favorites[1]})
                    show = showDB.find_one({"name":newchar['show']})
                    showOutput = show["title"]
                    
                    newem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
                    newem.add_field(name=f"**Character:  {newchar['name'].capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
                    newem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
                    if len(favorites) != 0:
                        newem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
                    
                    newem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
                    newem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
                    if hasmal is True:
                        newem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
                    if hasanilist is True:
                        newem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
                    if hasbio is True:
                        userbio = str(userbio)
                        newem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

                    if color == getColor("common") and charFound == True:
                        newem.set_footer(text=f"Tip: Change profile color with !acpc")
                    if color == getColor("common") and charFound == False:
                        newem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")
                    newem.set_image(url=gifList[1])
                    newem.set_thumbnail(url = member.avatar_url)
                    await profileInteract.respond(content='',embed=newem,type=7)



                elif profileInteract.values[0] == 'option4':
                    newchar = charDB.find_one({'name':favorites[2]})
                    show = showDB.find_one({"name":newchar['show']})
                    
                    showOutput = show["title"]
                    
                    newem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
                    newem.add_field(name=f"**Character:  {newchar['name'].capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
                    newem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
                    if len(favorites) != 0:
                        newem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
                    
                    newem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
                    newem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
                    if hasmal is True:
                        newem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
                    if hasanilist is True:
                        newem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
                    if hasbio is True:
                        userbio = str(userbio)
                        newem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

                    if color == getColor("common") and charFound == True:
                        newem.set_footer(text=f"Tip: Change profile color with !acpc")
                    if color == getColor("common") and charFound == False:
                        newem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")
                    newem.set_image(url=gifList[2])
                    newem.set_thumbnail(url = member.avatar_url)
                    await profileInteract.respond(content='',embed=newem,type=7)


                elif profileInteract.values[0] == 'option5':
                    newchar = charDB.find_one({'name':favorites[3]})
                    show = showDB.find_one({"name":newchar['show']})
                    showOutput = show["title"]
                    
                    newem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
                    newem.add_field(name=f"**Character:  {newchar['name'].capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
                    newem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
                    if len(favorites) != 0:
                        newem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
                    
                    newem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
                    newem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
                    if hasmal is True:
                        newem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
                    if hasanilist is True:
                        newem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
                    if hasbio is True:
                        userbio = str(userbio)
                        newem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

                    if color == getColor("common") and charFound == True:
                        newem.set_footer(text=f"Tip: Change profile color with !acpc")
                    if color == getColor("common") and charFound == False:
                        newem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")
                    newem.set_image(url=gifList[3])
                    newem.set_thumbnail(url = member.avatar_url)
                    await profileInteract.respond(content='',embed=newem,type=7)


                elif profileInteract.values[0] == 'option6':
                    newchar = charDB.find_one({'name':favorites[4]})
                    show = showDB.find_one({"name":newchar['show']})
                    showOutput = show["title"]
                    
                    newem = discord.Embed(title = f"ACprofile - {member.name}",color = color)
                    newem.add_field(name=f"**Character:  {newchar['name'].capitalize()}**",value=f"\nShow: {showOutput}", inline=True)
                    newem.add_field(name=f'**Money**', value=f'${usermoney}', inline=True)
                    if len(favorites) != 0:
                        newem.add_field(name="**Favorites**",value = f'{joinVar.join(favorites[i].capitalize() for i in range(0,len(favorites)))}',inline = False)
                    
                    newem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(rounded)} Top {rounded}%', inline=False)
                    newem.add_field(name=f'**Stats**', value=f'Total Characters: {charsUnlocked}/{totalChars}\nPrestige Level: {totPres}\nLegendaries: {leg}\nHyper Legendaries: {hypersUnl}', inline=True)
                    if hasmal is True:
                        newem.add_field(name=f"**MAL**",value=f"{usermal}", inline=False)
                    if hasanilist is True:
                        newem.add_field(name=f"**Anilist**",value=f"{useranilist}", inline=False)
                    if hasbio is True:
                        userbio = str(userbio)
                        newem.add_field(name=f"**Bio**",value=f"{userbio}", inline=False)

                    if color == getColor("common") and charFound == True:
                        newem.set_footer(text=f"Tip: Change profile color with !acpc")
                    if color == getColor("common") and charFound == False:
                        newem.set_footer(text=f"Your profile is displaying the first character you unlocked.\nTo choose a different character you have unlocked use !acsc\nYou can also change your profile color with !acpc")
                    newem.set_image(url=gifList[4])
                    newem.set_thumbnail(url = member.avatar_url)
                    await profileInteract.respond(content='',embed=newem,type=7)
               
            except:
                break

        profileCompEmpty = []
        await message.edit(components=profileCompEmpty)
        return

@client.command(aliases=['acsmal','ACsetMAL','ACsmal'])
async def acsetmal(ctx, mal=None): 
    member = ctx.author
    guild = ctx.message.guild
    await createuser(member, guild)
    
    if mal is None:
        em = discord.Embed(title = "ACsetmal",description=f"Puts a link to your MAL profile in your {ouptputprefix(ctx)}acprofile\nSyntax: **{ouptputprefix(ctx)}acsmal *link*** ",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    if "myanimelist" and "profile" not in mal:
        em = discord.Embed(title = "ACsetmal",description=f"*Link:* {mal}\n is not valid, please use a *My Anime List* profile link.",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
        
    userDB.update_one({"id":member.id}, {"$set":{"mal":mal}})
    em = discord.Embed(title = f"ACsetmal",description=f"{member.name.capitalize()}'s MAL: {mal}\nUpdated on your profile use {ouptputprefix(ctx)}acprofile to check it out",color = discord.Color.teal())
    await ctx.send(embed=em)
    await send_logs_profile_base(member, guild, "acsetmal")
    return

@client.command(aliases=['acsb','ACsetbio','ACSETBIO'])
async def acsetbio(ctx, bio=None): 
    member = ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACsetbio - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member, guild)
    
    if bio is None:
        em = discord.Embed(title = "ACsetbio",description=f'Adds a bio to your {ouptputprefix(ctx)}acprofile (Max **300** characters)\nSyntax: **{ouptputprefix(ctx)}acsetbio "*Put bio here*"**\n**IMPORTANT!** You need to include the quotes for multiple word bios.',color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    if bio == "":
        em = discord.Embed(title = "ACsetbio",description=f'Adds a bio to your {ouptputprefix(ctx)}acprofile (Max **300** characters)\nSyntax: **{ouptputprefix(ctx)}acsetbio "*Put bio here*"**\n**IMPORTANT!** You need to include the quotes for multiple word bios.',color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    if len(bio) > 300:
        em = discord.Embed(title = "ACsetbio",description=f"*Bio* has to be less than 300 characters.",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    if "https" in bio:
        em = discord.Embed(title = "ACsetbio",description=f"You cannot have links in your bio!",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return

    em = discord.Embed(title = f"ACsetbio - {member.name}",description=f"Update bio to: **{bio}**",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)

    buttons = [
            
            [
            Button(style=ButtonStyle.green,label='Confirm'),
            Button(style=ButtonStyle.red,label='Cancel')
            ]

        ]

    message = await ctx.send(embed = em,components=buttons)
    
    def checkauthor(user):
            return lambda res: res.author == user and res.message == message
            
    
    while True:
        try:
            res = await client.wait_for('button_click',check = checkauthor(member),timeout=10.0)
            if res.component.label == 'Confirm':
                userDB.update_one({"id":member.id}, {"$set":{"bio":bio}})
                em = discord.Embed(title = f"ACsetbio - {member.name}",description=f"Bio Updated: **{bio}**\nUse **{ouptputprefix(ctx)}acprofile** to check it out!",color = discord.Color.teal())
                em.set_thumbnail(url = member.avatar_url)
                await message.edit(embed=em)
                await send_logs_profile_change(member, guild, "acsetbio",bio)
                newButtons = []
                await res.respond(content='',embed=em,components=newButtons,type=7)
                return
            if res.component.label == 'Cancel':
                em = discord.Embed(title = f"ACsetbio- {member.name}",description=f"**Bio not updated**",color = discord.Color.teal())
                em.set_thumbnail(url = member.avatar_url)
                await message.edit(embed=em)
                newButtons = []
                await res.respond(content='',embed=em,components=newButtons,type=7)
                return
        except:
            break

    em = discord.Embed(title = f"ACsetbio - {member.name}",description=f"Bio not changed\n{member.name} did not respond within 10 seconds.",color = discord.Color.teal())
    em.set_thumbnail(url = member.avatar_url)
    newcomps=[]
    await message.edit(embed=em,components=newcomps)
    return


@client.command(aliases=['acsanilist','ACsetanilist','ACSETANILIST'])
async def acsetanilist(ctx, anilist=None): 
    member = ctx.author
    guild = ctx.message.guild
    await createuser(member, guild)
    
    if anilist is None:
        em = discord.Embed(title = "acsetanilist",description=f"Puts a link to your Anilist profile in your {ouptputprefix(ctx)}acprofile\nSyntax: **{ouptputprefix(ctx)}acsetanilist *link*** ",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    if "anilist" and "user" not in anilist:
        em = discord.Embed(title = "acsetanilist",description=f"*Link:* {anilist}\n is not valid, please use a *Anilist* profile link.",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
        
    userDB.update_one({"id":member.id}, {"$set":{"anilist":anilist}})
    em = discord.Embed(title = f"acsetanilist",description=f"{member.name.capitalize()}'s Anilist: {anilist}\nUpdated on your profile use {ouptputprefix(ctx)}acprofile to check it out",color = discord.Color.teal())
    await ctx.send(embed=em)
    await send_logs_profile_base(member, guild, "acsetanilist")
    return

@client.command(aliases=['acsc','ACsetcharacter','ACSC'])
async def acsetcharacter(ctx, character=None): 
    member = ctx.author
    guild = ctx.message.guild
    await createuser(member, guild)
    if character is None:
        em = discord.Embed(title = "ACsetcharacter",description=f"Sets a character that you have unlocked to appear on your {ouptputprefix(ctx)}acprofile.\nUse {ouptputprefix(ctx)}acbank to see your unlocked characters.\n**Syntax:{ouptputprefix(ctx)}acsc *character*** ",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    character = character.lower()
    charfound = charDB.find_one({"name":character})
    
    user = userDB.find_one({"id":member.id})
    userChars = user['characters']
    for p in userChars:
        if p["name"] == character:
            userDB.update_one({"id":member.id}, {"$set":{"currentchar":character}})
            char = charDB.find_one({"name":character})
            gif = char["gif"]
            show = char["show"]
            rarity = char["rarity"]
            em = discord.Embed(title = f"ACsetcharacter - {member.name}",description=f"Character: **{character.capitalize()}**\nShow: **{show.capitalize()}**\nRarity: **{rarity.capitalize()}**\n\n**Do !acprofile to check it out!**",color = getColor(rarity))
            em.set_image(url=gif)
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            if char['name'] == 'eren':
                achDB.update_one({"id":member.id}, {"$set":{"setEren":True}})
            await send_logs_profile_change(member, guild, "acsetcharacter",character)
            return

    if charfound == None:
        em = discord.Embed(title = "ACsetcharacter",description=f"{character.capitalize()} is not available.\nFor a list of characters do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        em = discord.Embed(title = "ACsetcharacter",description=f"**{member.name}** hasn't unlocked **{character.capitalize()}**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    
@client.command(aliases=['acsf','ACsetfavorite','ACSF'])
async def acsetfavorite(ctx, character1=None):
    member = ctx.author
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACsetfavorite - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if character1 is None:
        em = discord.Embed(title = "ACsetfavorite",description=f"Sets a character as your favorite which appears on your {ouptputprefix(ctx)}acprofile.\nUse {ouptputprefix(ctx)}acbank to see your unlocked characters.\nSyntax:{ouptputprefix(ctx)}acsf <character>",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    character1=character1.lower()

    guild = ctx.message.guild

    character1Found = charDB.find_one({"name":character1})
    
    if character1Found == None:
        em = discord.Embed(title = "ACsetfavorite",description=f"Character, **{character1.capitalize()}**, not found.\nFor a list of your unlocked characters do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    
    user = userDB.find_one({"id":member.id})
    userchars= user["characters"]
    haschar = False
    
    #userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":"placeHolder"}}})
    userFavorites = user["favorites"]
    userfavlist = []
    amountFavs = 0
    for x in userFavorites:
        userfavlist.append(x["name"])
        amountFavs+=1
        if character1 == x["name"]:
            em = discord.Embed(title = "ACsetfavorite",description=f"**{x['name'].capitalize()}** is already in your favorites.",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return


    for x in userchars:
        if x["name"] == character1:
            haschar = True
        else:
            continue

    if haschar == False:
        em = discord.Embed(title = "ACsetfavorite",description=f"**{member.name}** hasn't unlocked **{character1.capitalize()}**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
        
    await send_logs_profile_change(member,guild,'acsetfavorite',character1)

    if amountFavs < 5:
        userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
        em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        userfavlist.clear()
        return
    else:
        em = discord.Embed(title = "ACsetfavorite",description=f"**{member.name}** already has 5 favorites.\nPlease choose a character to replace from the menu below",color = getColor("botColor"))
        em.set_thumbnail(url=member.avatar_url)
        components = [
            [
                Select(placeholder=f"Select a Character",
                options=[
                    SelectOption(label= f'{userfavlist[0].capitalize()}',value='option1'),
                    SelectOption(label= f'{userfavlist[1].capitalize()}',value='option2'),
                    SelectOption(label= f'{userfavlist[2].capitalize()}',value='option3'),
                    SelectOption(label= f'{userfavlist[3].capitalize()}',value='option4'),
                    SelectOption(label= f'{userfavlist[4].capitalize()}',value='option5')
                ]

            )]
        ]

        message = await ctx.send(embed = em,components=components)
        def checkauthor(user):
            return lambda res: res.author == user and res.message == message
        
        while True:
            try:
                event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=10.0)

                if event.values[0] == 'option1':
                    userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":userfavlist[0]}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
                    em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
                    em.set_thumbnail(url=member.avatar_url)
                    
                    newcomps = []
                    await event.respond(content='',components=newcomps,embed=em,type=7)
                    break

                elif event.values[0] == 'option2':
                    userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":userfavlist[1]}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
                    em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
                    em.set_thumbnail(url=member.avatar_url)
                    newcomps = []
                    await event.respond(content='',components=newcomps,embed=em,type=7)
                    break

                elif event.values[0] == 'option3':
                    userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":userfavlist[2]}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
                    em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
                    em.set_thumbnail(url=member.avatar_url)
                    newcomps = []
                    await event.respond(content='',components=newcomps,embed=em,type=7)
                    break

                elif event.values[0] == 'option4':
                    userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":userfavlist[3]}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
                    em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
                    em.set_thumbnail(url=member.avatar_url)
                    newcomps = []
                    await event.respond(content='',components=newcomps,embed=em,type=7)
                    break

                elif event.values[0] == 'option5':
                    userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":userfavlist[4]}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"favorites":{"name":character1}}})
                    em = discord.Embed(title = "ACsetfavorite",description=f"**{character1.capitalize()}** added to your favorites.",color = getColor("botColor"))
                    em.set_thumbnail(url=member.avatar_url)
                    newcomps = []
                    await event.respond(content='',components=newcomps,embed=em,type=7)
                    break
                

            except:
                newcomps = []
                em = discord.Embed(title = "ACsetfavorite",description=f"Request Timed Out\nPlease Try Again!",color = getColor("botColor"))
                em.set_thumbnail(url=member.avatar_url)

                await message.edit(embed=em,components=newcomps)
                break

        userfavlist.clear()
        return

@client.command(aliases = ['acrs', 'ACRS', 'ACresetshop', 'Acresetshop','Acrs'])
async def acresetshop(ctx,confirm = None):
    member = ctx.author
    botStats = botstatsDB.find_one({"id":573})
    await createshopuser(member,ctx.message.guild)
    userProf = shopDB.find_one({"id":member.id})

    if confirm != None:
        confirm = confirm.lower()

    def resetShop():
        shopDB.update_one({"id":member.id}, {"$set":{"boughtuncommon":False,"boughtrare":False,"boughtepic":False,"boughtlegendary1":False,"boughtlegendary2":False,"boughtloading":False}})

        for x in range(7):
            randNum = random.randint(1,100000000000)
            # randseed = int(member.id + randNum)
            random.seed(randNum)
            try:
                ublocks = blockDB.find_one({'id':member.id})
                blist = ublocks['blocklist']
                newblist = []
                for itm in blist:
                    newblist.append(itm['show'])
            except:
                newblist=[]
            if x == 1:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                uncChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while uncChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    uncChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":uncChar["name"],"show":uncChar["show"],"rarity":uncChar["rarity"]}}})
            if x == 2:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                rareChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while rareChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    rareChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":rareChar["name"],"show":rareChar["show"],"rarity":rareChar["rarity"]}}})
            if x == 3:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                epicChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while epicChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    epicChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":epicChar["name"],"show":epicChar["show"],"rarity":epicChar["rarity"]}}})
            if x == 4:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                legendaryChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while legendaryChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    legendaryChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":legendaryChar["name"],"show":legendaryChar["show"],"rarity":legendaryChar["rarity"]}}})
            if x == 5:
                max = charDB.count_documents({"rarity":rarities[4]})
                randomInt = random.randint(1,max) 
                legChar2 = charDB.find_one({"rarity":rarities[4], "raritynumber": randomInt})
                while legChar2['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    legChar2 = charDB.find_one({"rarity":rarities[4], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":legChar2["name"],"show":legChar2["show"],"rarity":legChar2["rarity"]}}})
            if x == 6:
                max = loadingScreenDB.count_documents({})
                randomInt = random.randint(1,max) 
                loadingScreen = loadingScreenDB.find_one({'number':randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"number":loadingScreen["number"]}}})
            

    if userProf["money"] >= botStats["shopresetamount"]:
        if confirm == "confirm": 
            shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"]-botStats['shopresetamount']}})
            userShop = userProf["characterShop"]
            for x in userShop:
                try:
                    shopDB.update_one({"id":member.id}, {"$pull":{"characterShop":{"name":x["name"]}}})
                except:
                    shopDB.update_one({"id":member.id}, {"$pull":{"characterShop":{"number":x["number"]}}})
            resetShop()

            em = discord.Embed(title = f"ACresetshop - {member.name}",description=f"**Your shop has been reset check it out with !accs**",color = discord.Color.teal())
            em.set_thumbnail(url = member.avatar_url)
            await ctx.send(embed=em)
            await send_logs(member,ctx.message.guild,"acresetshop")
            return
        else:
            em = discord.Embed(title = f"ACresetshop - {member.name}" ,description=f"Allows you to reset your shop at any time!\n**Cost: ${botStats['shopresetamount']}**\nTo reset your shop type **'!acresetshop confirm'**",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return


    else:
        em = discord.Embed(title = f"ACresetshop - {member.name}" ,description=f"Allows you to reset your shop at any time!\n**Cost: ${botStats['shopresetamount']}**\nTo reset your shop type **'!acresetshop confirm'**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return


# pageNames= ["attack on titan","akame ga kill","black clover","bleach","bunny girl senpai","code geass","death note","demon slayer","dragon ball","dragon maid","evangelion","fairy tail","fire force","fmab","haikyuu!!","hunter x hunter","horimiya",
#             "jojo","jujutsu kaisen","k-on","konosuba","love is war","mob psycho 100","my hero academia","naruto","noragami","one piece","one punch man","oregairu","rent a girl friend","sk8","slime","soul eater","sword art online","steins gate","the quintessential quintuplets","tokyo ghoul","tokyo revengers","vinland saga","your lie in april"]

# pageNamesNoSpace = ["attackontitan","akamegakill","blackclover","bleach","bunnygirlsenpai","codegeass","deathnote","demonslayer","dragonball","dragonmaid","evangelion","fairytail","fireforce","fmab","haikyuu!!","hunterxhunter","horimiya",
#             "jojo","jujutsukaisen","k-on","konosuba","loveiswar","mobpsycho100","myheroacademia","naruto","noragami","onepiece","onepunchman","oregairu","rentagirlfriend","sk8","slime","souleater","swordartonline","steinsgate","thequintessentialquintuplets","tokyoghoul","tokyorevengers","vinlandsaga","yourlieinapril"]

# abrvNames = ["aot","agk","bc","bleach","bgs","cg","dn","ds","db","dm","eva","ft","ff","fmab","haikyuu","hxh","horimiya","jojo","jjk","k-on","konosuba","liw","mp100","mha","naruto","noragami","op","opm","snafu","ragf","sk8","slime","se","sao","sg","tqq","tg","tr","vs","ylia"]

# numshows = len(pageNames)
@client.command(aliases = ['Acshows','ACSHOWS','ACshows'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def acshows(ctx,member:discord.Member=None):
    member = ctx.author
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACsetfavorite - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    
    numshows = showDB.count_documents({})
    pagesNeeded = math.ceil(numshows/15)
    #print(pagesNeeded)

    showlist = showDB.find().sort('title')
    newShowsList = []
    numInList = 1
    for t in showlist:
        newShowsList.append(f'{numInList}. {t["title"]} ({t["abv"]})')
        numInList+=1
    joinVar = '\n'

    #print(newShowsList)
    acshowsPages = []
    startNum = 0
    stopNum = 15

    for pages in range(pagesNeeded):
        embed = discord.Embed (
        title = f"**ACshows - User: {member.name}\nTo see the characters in a show do !acbs show\nExample: !acbs aot**",
        description = f'{joinVar.join(newShowsList[i] for i in range(startNum,stopNum))}',
        colour = getColor('botColor')
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f'Page: ({pages+1}/{pagesNeeded})')
        acshowsPages.append(embed)
        startNum+=15
        stopNum+=15
        if stopNum >= numshows:
            stopNum = numshows
        

    components = [
            [
            Button(style=ButtonStyle.grey,label='Prev'),
            Button(style=ButtonStyle.grey,label='Next')
            ]
            
        ]


    message = await ctx.send(embed=acshowsPages[0],components=components)

    def checkauthor(user):
        return lambda res: res.author == user and res.message == message

    acShowIt = 0
    while True:
        try:
            acbrInteract = await client.wait_for('button_click',check = checkauthor(ctx.author),timeout=15.0)

            if acbrInteract.component.label == 'Prev':
                if acShowIt > 0:
                    acShowIt -= 1
                

            elif acbrInteract.component.label == 'Next':
                if acShowIt < pagesNeeded-1:
                    acShowIt += 1

            await acbrInteract.respond(content='',embed=acshowsPages[acShowIt],type=7)

        except:
            break


    acShowsButnew = []
    await message.edit(components=acShowsButnew)

    acshowsPages.clear()
    newShowsList.clear()
    await send_logs(member,ctx.message.guild,"acshows")
    return

@client.command(aliases = ['Acblock','ACBLOCK','ACblock'])
async def acblock(ctx, show = None, show2=None):
    member = ctx.author
    if show == None :
        em = discord.Embed(title = f"ACblock - {member.name}",description=f"Allows you to **block** a show. This means you won't roll any characters from that show and they won't appear in your shop.\nSyntax: **!acblock *show***\nTo see a list of shows do *!acshows*\nTo remove a block a block do **!acblock remove *show***\nTo view your current blocklist do **!acblock view**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    if show == "view":
        try:
            userBlocks = blockDB.find_one({"id":member.id})
            blocklist = userBlocks['blocklist']
        except:
            em = discord.Embed(title = f"ACblock - {member.name}",description=f"{member.name} currently has no blocked shows",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return

        newbl = []
        numb = 0
        for t in blocklist:
            getShow = showDB.find_one({"name":t['show']})
            newbl.append(f'{numb+1}. {getShow["title"]} ({getShow["abv"]})')
            numb+=1
        joinVar = '\n'

        if numb != 0:
            em = discord.Embed (
            title = f"**ACblock - {member.name}\nShows Blocked**:",
            description = f'{joinVar.join(newbl[i] for i in range(0,numb))}',
            colour = getColor('botColor'))
        if numb == 0:
            em = discord.Embed (
            title = f"**ACblock - {member.name}\n{member.name}'s blocklist is currently empty.**",
            colour = getColor('botColor'))

        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    if show == "remove":
        if show2 == None:
            em = discord.Embed(title = f"ACblock - {member.name}",description=f"Show not specified. To remove a show please use\n **!acblock remove *show***\nTo see a list of shows do *!acshows*",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        
        show2 = show2.lower()

        try:
            showFound = showDB.find_one({'name':show2})
        except:
            showFound = None

        if showFound == None:
            try:
                showFound = showDB.find_one({'abv':show2})
            except:
                pass

        if showFound == None:
            em = discord.Embed(title = f"ACblock - {member.name.capitalize()}",description = f"Show '{show2}' not found, please you the abbreviations found in *!acshows*\nSyntax: **!acblock *show***",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        
        try:
            userBlocks = blockDB.find_one({"id":member.id})
            blocklist = userBlocks['blocklist']
        except:
            blocklist = []

        blockFound = False

        for item in blocklist:
            if item['show'] == showFound['name']:
                blockFound = True
        
        if blockFound == False:
            em = discord.Embed(title = f"ACblock - {member.name.capitalize()}",description = f"{showFound['name'].capitalize()} not in your blocklist. To view your current blocklist do **!acblock view**",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        else:
            blockDB.update_one({"id":member.id}, {"$pull":{"blocklist":{"show":showFound['name']}}})
            em = discord.Embed(title = f"ACblock - {member.name.capitalize()}",description = f"{showFound['name'].capitalize()} removed from your blocklist. To view your current blocklist do **!acblock view**",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        

    show = show.lower()

    try:
        showFound = showDB.find_one({'name':show})
    except:
        showFound = None

    if showFound == None:
        try:
            showFound = showDB.find_one({'abv':show})
        except:
            pass

    if showFound == None:
        em = discord.Embed(title = f"ACblock - {member.name.capitalize()}",description = f"Show '{show}' not found, please you the abbreviations found in *!acshows*\nSyntax: **!acblock *show***",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    
    await createblock(member)

    try:
        userBlocks = blockDB.find_one({"id":member.id})
        blocklist = userBlocks['blocklist']
    except:
        blocklist = []


    blockFound = False
    blcount = 0
    for item in blocklist:
        blcount+=1
        if item == showFound['name']:
            blockFound = True


    if blockFound == True:
        em = discord.Embed(title = f"ACblock - {member.name}",description = f"{showFound['name'].capitalize()} already in your Block List.",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    elif blcount >= 3:
        em = discord.Embed(title = f"ACblock - {member.name}",description = f"{member.name} already has three blocked shows. To view your current blocklist do **!acblock view**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        blockDB.update_one({"id":member.id}, {"$addToSet":{"blocklist":{"show":showFound['name']}}})
        em = discord.Embed(title = f"ACblock - {member.name}",description = f"{showFound['name'].capitalize()} added to your blocklist. To view your current blocklist do **!acblock view**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return


@client.command(aliases = ['acb','Acb','ACB','ACBANK','ACbank','Acbank'])
@commands.cooldown(1, 20, commands.BucketType.user)
async def acbank(ctx,member:discord.Member=None):
    if member == None:
        member = ctx.author
    guild=ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACbank - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member,guild)
    
    
    user = userDB.find_one({"id":member.id})
    try:
        userChars = user["characters"]
    except:
        em = discord.Embed(title = f"{member.name.capitalize()} hasn't unlocked any characters!\nDo *{ouptputprefix(ctx)}acr* to get started then come back to see a list of all the characters and shows!",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    showlist = showDB.find().sort("title")

 
    showlist = showlist
    numshows = showDB.estimated_document_count()


    i = 0
    show = showlist[i]
    amountUnlocked = 0
    amountCharsinShow = charDB.count_documents({"show":show["name"]})
    for y in userChars:
        if show["name"] == y["show"]:
            amountUnlocked+=1


    userpres = presDB.find_one({'id':member.id})
    if userpres == None:
        level = 0
    else:
        level = 0
        preslist = userpres['shows']
        for shws in preslist:
            if shws['show'] == show['name']:
                level = shws['tier']

    stars = ''
    for x in range(level):
        stars += '⭐'
    
    embedDef = discord.Embed (
    title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
    description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
    colour = getPresCol(level)
    )

    user = userDB.find_one({"id":member.id})
    userChars = user["characters"]
    
    charlist = charDB.find({"show":show['name']}).sort("rarityrank")
    embedDef.set_thumbnail(url= show['thumbnail'])
    for y in charlist:
        charFound=False
        for t in userChars:
            if y['name'] == t["name"]:
                
                embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                charFound = True
                break
        if charFound == False:
            embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
    
    embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")
    message = await ctx.send(embed = embedDef)
   
  
    
    bankButtons = [
            #Button(style=ButtonStyle.blue,label='Page -5',emoji="✅") Sample with emoji
        [
        Button(style=ButtonStyle.blue,label='First'),
        Button(style=ButtonStyle.blue,label='Last'),
        Button(style=ButtonStyle.red,label='Close')
        ],
        [
        Button(style=ButtonStyle.grey,label='-5'),
        Button(style=ButtonStyle.grey,label='-1'),
        Button(style=ButtonStyle.grey,label='+1'),
        Button(style=ButtonStyle.grey,label='+5')
        ]
    ]

    await message.edit(components=bankButtons)

    def checkauthor(user):
            return lambda res: res.author == user and res.message == message

    while True:
        try:
            res = await client.wait_for('button_click',check = checkauthor(ctx.author),timeout=20.0)

            if res.component.label == 'First':
                i = 0
                show = showlist[i]
                amountUnlocked = 0
                amountCharsinShow = charDB.count_documents({"show":show["name"]})
                # amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                for y in userChars:
                    if show["name"] == y["show"]:
                        amountUnlocked+=1


                userpres = presDB.find_one({'id':member.id})
                if userpres == None:
                    level = 0
                else:
                    level = 0
                    preslist = userpres['shows']
                    for shws in preslist:
                        if shws['show'] == show['name']:
                            level = shws['tier']

                stars = ''
                for x in range(level):
                    stars += '⭐'
                
                embedDef = discord.Embed (
                title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                colour = getPresCol(level)
                )
                charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                embedDef.set_thumbnail(url= show['thumbnail'])
                for y in charlist:
                    # tempname = y["name"]
                    # #charshow=y["show"]
                    # rarity=y["rarity"]
                    charFound=False
                    #print(charshow,show)
                    for t in userChars:
                        if y['name'] == t["name"]:
                            #addfield(pages[it],tempname,rarity,"✅")
                            embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                            charFound = True
                            break
                    if charFound == False:
                        #addfield(pages[it],tempname,rarity,"❌")
                        embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")


            elif res.component.label == '-5':
                if i > 5:
                    i -= 5
                    show = showlist[i]
                    amountUnlocked = 0
                    amountCharsinShow = charDB.count_documents({"show":show["name"]})
                    #amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                    for y in userChars:
                        if show["name"] == y["show"]:
                            amountUnlocked+=1
                    userpres = presDB.find_one({'id':member.id})
                    if userpres == None:
                        level = 0
                    else:
                        level = 0
                        preslist = userpres['shows']
                        for shws in preslist:
                            if shws['show'] == show['name']:
                                level = shws['tier']


                    stars = ''
                    for x in range(level):
                        stars += '⭐'
                    
                    embedDef = discord.Embed (
                    title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                    description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                    colour = getPresCol(level)
                    )
                    charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                    embedDef.set_thumbnail(url= show['thumbnail'])
                    for y in charlist:
                        # tempname = y["name"]
                        # #charshow=y["show"]
                        # rarity=y["rarity"]
                        charFound=False
                        #print(charshow,show)
                        for t in userChars:
                            if y['name'] == t["name"]:
                                #addfield(pages[it],tempname,rarity,"✅")
                                embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                                charFound = True
                                break
                        if charFound == False:
                            #addfield(pages[it],tempname,rarity,"❌")
                            embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                    embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")
            
            elif res.component.label == '-1':
                if i > 0:
                    i -= 1
                    show = showlist[i]
                    amountUnlocked = 0
                    amountCharsinShow = charDB.count_documents({"show":show["name"]})
                    #amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                    for y in userChars:
                        if show["name"] == y["show"]:
                            amountUnlocked+=1
                    userpres = presDB.find_one({'id':member.id})
                    if userpres == None:
                        level = 0
                    else:
                        level = 0
                        preslist = userpres['shows']
                        for shws in preslist:
                            if shws['show'] == show['name']:
                                level = shws['tier']


                    stars = ''
                    for x in range(level):
                        stars += '⭐'
                    
                    embedDef = discord.Embed (
                    title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                    description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                    colour = getPresCol(level)
                    )
                    charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                    embedDef.set_thumbnail(url= show['thumbnail'])
                    for y in charlist:
                        # tempname = y["name"]
                        # #charshow=y["show"]
                        # rarity=y["rarity"]
                        charFound=False
                        #print(charshow,show)
                        for t in userChars:
                            if y['name'] == t["name"]:
                                #addfield(pages[it],tempname,rarity,"✅")
                                embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                                charFound = True
                                break
                        if charFound == False:
                            #addfield(pages[it],tempname,rarity,"❌")
                            embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                    embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")

            elif res.component.label == '+1':
                if i < numshows-1:
                    i += 1
                    show = showlist[i]
                    amountUnlocked = 0
                    amountCharsinShow = charDB.count_documents({"show":show["name"]})
                    #amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                    for y in userChars:
                        if show["name"] == y["show"]:
                            amountUnlocked+=1
                    userpres = presDB.find_one({'id':member.id})
                    if userpres == None:
                        level = 0
                    else:
                        level = 0
                        preslist = userpres['shows']
                        for shws in preslist:
                            if shws['show'] == show['name']:
                                level = shws['tier']


                    stars = ''
                    for x in range(level):
                        stars += '⭐'
                    
                    embedDef = discord.Embed (
                    title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                    description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                    colour = getPresCol(level)
                    )
                    charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                    embedDef.set_thumbnail(url= show['thumbnail'])
                    for y in charlist:
                        # tempname = y["name"]
                        # #charshow=y["show"]
                        # rarity=y["rarity"]
                        charFound=False
                        #print(charshow,show)
                        for t in userChars:
                            if y['name'] == t["name"]:
                                #addfield(pages[it],tempname,rarity,"✅")
                                embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                                charFound = True
                                break
                        if charFound == False:
                            #addfield(pages[it],tempname,rarity,"❌")
                            embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                    embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")

            elif res.component.label == '+5':
                if i < numshows-5:
                    i += 5
                    show = showlist[i]
                    amountUnlocked = 0
                    amountCharsinShow = charDB.count_documents({"show":show["name"]})
                    #amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                    for y in userChars:
                        if show["name"] == y["show"]:
                            amountUnlocked+=1
                    userpres = presDB.find_one({'id':member.id})
                    if userpres == None:
                        level = 0
                    else:
                        level = 0
                        preslist = userpres['shows']
                        for shws in preslist:
                            if shws['show'] == show['name']:
                                level = shws['tier']


                    stars = ''
                    for x in range(level):
                        stars += '⭐'
                    
                    embedDef = discord.Embed (
                    title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                    description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                    colour = getPresCol(level)
                    )
                    charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                    embedDef.set_thumbnail(url= show['thumbnail'])
                    for y in charlist:
                        # tempname = y["name"]
                        # #charshow=y["show"]
                        # rarity=y["rarity"]
                        charFound=False
                        #print(charshow,show)
                        for t in userChars:
                            if y['name'] == t["name"]:
                                #addfield(pages[it],tempname,rarity,"✅")
                                embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                                charFound = True
                                break
                        if charFound == False:
                            #addfield(pages[it],tempname,rarity,"❌")
                            embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)

                    embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")

            elif res.component.label == "Close":
                break

            elif res.component.label == 'Last':
                i = numshows-1
                show = showlist[i]
                amountUnlocked = 0
                amountCharsinShow = charDB.count_documents({"show":show["name"]})
                # amountUnlocked = userDB.find({"id":member.id,"characters":{"$elemMatch":{"show":show["name"]}}})
                for y in userChars:
                    if show["name"] == y["show"]:
                        amountUnlocked+=1
                userpres = presDB.find_one({'id':member.id})
                if userpres == None:
                    level = 0
                else:
                    level = 0
                    preslist = userpres['shows']
                    for shws in preslist:
                        if shws['show'] == show['name']:
                            level = shws['tier']


                stars = ''
                for x in range(level):
                    stars += '⭐'
                
                embedDef = discord.Embed (
                title = f"ACbank - {member.name.capitalize()}\n({i+1}/{numshows})",
                description = f"**{show['title']} ({show['abv']})\nUnlocked: {amountUnlocked}/{amountCharsinShow}\nPrestige: {level}**\n{stars}",
                colour = getPresCol(level)
                )
                charlist = charDB.find({"show":show['name']}).sort("rarityrank")
                embedDef.set_thumbnail(url= show['thumbnail'])
                for y in charlist:
                    # tempname = y["name"]
                    # #charshow=y["show"]
                    # rarity=y["rarity"]
                    charFound=False
                    #print(charshow,show)
                    for t in userChars:
                        if y['name'] == t["name"]:
                            #addfield(pages[it],tempname,rarity,"✅")
                            embedDef.add_field(name=f"{'✅'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                            charFound = True
                            break
                    if charFound == False:
                        #addfield(pages[it],tempname,rarity,"❌")
                        embedDef.add_field(name=f"{'❌'} {y['name'].capitalize()}",value=f"{y['rarity'].capitalize()}", inline=True)
                embedDef.set_footer(text=f"Page ({i+1}/{numshows}) - {show['title']} ({show['abv']})")
            
            await res.respond(content='',embed=embedDef,components=bankButtons,type=7)

        except:
            break
       
    
    bankButtons = []

    await message.edit(components=bankButtons)
    commanduser = ctx.author
    await send_logs_acbs(commanduser,member, guild, "acbank","full_bank")
    return

@client.command(aliases = ['acbr','ACbankrarity','ACBR','Acbr'])
@commands.cooldown(1, 2, commands.BucketType.user)
async def acbankrarity(ctx,userRarity = None,member:discord.Member=None):
    if member == None:
        member = ctx.author
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACbankrarity - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    
    if userRarity == None:
        em = discord.Embed(title = f"ACbankrarity - {member.name}",description=f"Syntax: **!acbr *rarity***\nTo look at another user do: **!acbr *rarity @user***\nRarites: Common, Uncommon, Rare, Epic, Legendary, Hyperlegendary",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    userRarity = userRarity.lower()

    if userRarity == 'c':
        userRarity = 'common'
    elif userRarity == 'u':
        userRarity = 'uncommon'
    elif userRarity == 'r':
        userRarity = 'rare'
    elif userRarity == 'e':
        userRarity = 'epic'
    elif userRarity == 'l':
        userRarity = 'legendary'
    elif userRarity == 'hl':
        userRarity = 'hyperlegendary'
    
    if userRarity not in rarities and userRarity != 'hyperlegendary':
        em = discord.Embed(title = f"ACbankrarity - {member.name}",description=f"Syntax: **!acbr *rarity***\nTo look at another user do: **!acbr *rarity @user***\nRarites: Common, Uncommon, Rare, Epic, Legendary, Hyperlegendary",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    

    commanduser = ctx.author
    
    guild=ctx.message.guild
    await createuser(member,guild)
    membername = member.name
    
    user = userDB.find_one({"id":member.id})
    
    try:
        userChars = user["characters"]
    except:
        em = discord.Embed(title = f"{member.name} hasn't unlocked any characters!\nDo *{ouptputprefix(ctx)}acr* to get started!",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return


    embed = discord.Embed(title = f"ACbankrarity - {member.name}\nLoading...",color = discord.Color.teal())
    embed.set_thumbnail(url=member.avatar_url)
    message = await ctx.send(embed = embed)
   
    
    acbrI=0
    acbrO=0
    acbrJ=18
    acbrE=1
    charlist = charDB.find().sort("show")
    for x in userChars:
        if x["rarity"] == userRarity:
            acbrI+=1

    for xx in charlist:
        if xx["rarity"] == userRarity:
            acbrO+=1
            if acbrO > acbrJ:
                acbrJ+=18
                acbrE+=1
       

    bankraritypages = []
    for acbrX in range(acbrE):
        embed = discord.Embed (
        title = f"ACbankrarity\nUser: {commanduser.name} - Viewing: {membername}\nPage: ({acbrX+1}/{acbrE})",
        description = f"**{userRarity.capitalize()} characters unlocked: {acbrI}**",
        colour = getColor(userRarity)
        )
        embed.set_footer(text=f'{userRarity.capitalize()} characters unlocked: {acbrI} - Page: ({acbrX+1}/{acbrE})')
        bankraritypages.append(embed)
           
    
    def addfield(page,tempname,show):
        page.add_field(name=f"✅ **{tempname.capitalize()}**",value=f"{show}", inline=True)

    def addfield2(page,tempname,show):
        page.add_field(name=f"❌ **{tempname.capitalize()}**",value=f"{show}", inline=True)

    def setThumbnail(page):
        page.set_thumbnail(url=member.avatar_url)

    acbrF = 0
    acbrG = 18
    acbrnewnamelist = []
    
    for acbrZ in userChars:
        if acbrZ["rarity"] == userRarity:
            acbrnewnamelist.append(acbrZ["name"])

    charlist = charDB.find().sort("show")
    showlist = showDB.find()
 
    for acbrY in range(acbrE):
        setThumbnail(bankraritypages[acbrY])
        for z in charlist:
            if z["name"] in acbrnewnamelist:
                # showFound = showDB.find_one({'name':z['show']})
                acbrF+=1
                # addfield(bankraritypages[acbrY],z["name"],showFound['abv'])
                addfield(bankraritypages[acbrY],z["name"],z['abv'])
                if acbrF == acbrG:
                    acbrG+=18
                    break
            elif z['name'] not in acbrnewnamelist and z['rarity'] == userRarity:
                # showFound = showDB.find_one({'name':z['show']})
                acbrF+=1
                # addfield2(bankraritypages[acbrY],z["name"],showFound['abv'])
                addfield2(bankraritypages[acbrY],z["name"],z['abv'])
                if acbrF == acbrG:
                    acbrG+=18
                    break
                    
   
    if acbrE == 1:
        await message.edit(embed = bankraritypages[0])
        bankraritypages.clear()
        #await send_logs_acbr(commanduser,member, guild, "acbankrairty",userRarity)
        return
    else:
      
        acBRbuttons = [
            [
            Button(style=ButtonStyle.blue,label='Prev'),
            Button(style=ButtonStyle.blue,label='Next'),
            Button(style=ButtonStyle.red,label='Close')
            ]
            
        ]

        await message.edit(components=acBRbuttons,embed = bankraritypages[0])

        def checkauthor(user):
            return lambda res: res.author == user and res.message == message

        acbrT = 0
        while True:
            try:
                acbrInteract = await client.wait_for('button_click',check = checkauthor(ctx.author),timeout=15.0)

                if acbrInteract.component.label == 'Prev':
                    if acbrT > 0:
                        acbrT -= 1
                    
                elif acbrInteract.component.label == 'Next':
                    if acbrT < acbrE-1:
                        acbrT += 1
                
                elif acbrInteract.component.label == 'Close':
                    break

                await acbrInteract.respond(content='',embed=bankraritypages[acbrT],type=7)

            except:
                break


        acBRbuttons = []
        await message.edit(components=acBRbuttons)

        bankraritypages.clear()
        acbrnewnamelist.clear()
        try:
            await send_logs_acbr(commanduser,member, guild, "acbankrarity",userRarity)
        except:
            pass
        return

@client.command(aliases = ['ACPREMOVE'])
async def acpremove(ctx,item = None, char = None):
    member = ctx.author
    if item == None:
        em = discord.Embed(title = f"ACpremove - {member.name}",description=f"Allows you to **remove** something from your profile. You can remove a Bio, MAL, Anilist, or Favorite Character.\n**Syntax:\n!acpremove *bio* \n!acpremove *mal*\n!acpremove *anilist*\n!acpremove *favorite*  *charname***",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    item = item.lower()
    items = ["mal", "anilist", "bio"]

    found = False

    for thing in items:
        if item == thing:
            userDB.update_one({"id":member.id}, {"$unset":{thing:""}})
            found = True
            break
    
    if item == "favorite":
        if char == None:
            em = discord.Embed(title = f"ACpremove - {member.name}",description=f"No character specified. Syntax for removing a favorite:\n**!acpremove favorite *charname***",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        charFound = False
        userFound = userDB.find_one({'id':member.id})
        favs = userFound['favorites']
        for ch in favs:
            if char == ch['name']:
                charFound = True
                break

        if charFound == False:
            em = discord.Embed(title = f"ACpremove - {member.name}",description=f"{char.capitalize()} is not in your favorites.",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return

        userDB.update_one({"id":member.id}, {"$pull":{"favorites":{"name":char}}})
        em = discord.Embed(title = f"ACpremove - {member.name}",description=f"{char.capitalize()} successfully removed from your profile.",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        await send_logs_profile_change(member,ctx.message.guild,"acpremove",item)
        return
        

    if found == False:
        em = discord.Embed(title = f"ACpremove - {member.name}",description=f"**Please use one of these Syntax**\n!acpremove bio\n!acpremove anilist\n!acpremove mal\n!acpremove favorite *charname*",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    
    em = discord.Embed(title = f"ACpremove - {member.name}",description=f"{item.capitalize()} successfully removed from your profile.",color = discord.Color.teal())
    em.set_thumbnail(url=member.avatar_url)
    await ctx.send(embed=em)
    try:    
        await send_logs_profile_change(member,ctx.message.guild,"acpremove",item)
    except:
        pass
    return

@client.command(aliases = ['acbs','ACbankshow','ACBS'])
@commands.cooldown(1, 2, commands.BucketType.user)
async def acbankshow(ctx,showInput=None,member:discord.Member=None):
    try:
        if "@" in showInput:
            membername=ctx.author.name
            em = discord.Embed(title = f"ACbankshow - {membername.capitalize()}" ,description=f"Allows you to view a users bank for a specific show\nSyntax: **{ouptputprefix(ctx)}acbs *show @user***\nExample: {ouptputprefix(ctx)}acbs aot @exampleuser\n**Note**: Don't enter a user to view your own bank for a specific show.\n**Important!** Use the Abbreviations that are listed in !acbank for this command. ",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return
        else:
            pass
    except:
        pass
    if member == None:
        member = ctx.author
    guild=ctx.message.guild
    await createuser(member,guild)
    membername = member.name
   
    if showInput is None:
        em = discord.Embed(title = f"ACbankshow - {membername.capitalize()}" ,description=f"Allows you to view a users bank for a specific show\nSyntax: **{ouptputprefix(ctx)}acbs *show @user***\nExample: {ouptputprefix(ctx)}acbs aot @exampleuser\n**Note**: Don't enter a user to view your own bank for a specific show.\n**Important!** Use the Abbreviations that are listed in !acbank for this command. ",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    
    if showInput is not None:
        showInput= showInput.lower()

    user = userDB.find_one({"id":member.id})
    try:
        userChars = user["characters"]
    except:
        em = discord.Embed(title = f"{member.name.capitalize()} hasn't unlocked any characters!\nDo *{ouptputprefix(ctx)}acr*  to get started!",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    
    try:
        showFound = showDB.find_one({'name':showInput})
    except:
        showFound = None

    if showFound == None:
        try:
            showFound = showDB.find_one({'abv':showInput})
        except:
            pass

    if showFound == None:
        em = discord.Embed(title = f"ACbankshow- Show not found.",description = f"**Remember to use the *abbreviation* of the show *or* how it is formatted in !acbank but without spaces** :\nExample: *{ouptputprefix(ctx)}acbs demonslayer\nExample: !acbs ds*",color = discord.Color.teal())
        await ctx.send(embed=em)
        return

    showPrint = showFound["title"]
    showAbv = showFound["abv"]
    showInput = showFound['name']
    

    amtCharsInShow = charDB.count_documents({"show":showInput})
    amountUnlocked = 0

    for y in userChars:
        if showInput == y["show"]:
            amountUnlocked+=1
    

    userpres = presDB.find_one({'id':member.id})
    if userpres == None:
        level = 0
    else:
        level = 0
        preslist = userpres['shows']
        for shws in preslist:
            if shws['show'] == showInput:
                level = shws['tier']

    stars = ''
    for x in range(level):
        stars += '⭐'
  
    singlePage = discord.Embed (
        title = f'ACbankshow - {membername.capitalize()}',
        description = f"**{showPrint} ({showAbv})\nUnlocked: {amountUnlocked}/{amtCharsInShow}\nPrestige: {level}**\n{stars}",
        colour = getPresCol(level)
    )
    singlePage.set_footer(text=f"{showPrint} ({showAbv}) - Unlocked: {amountUnlocked}/{amtCharsInShow}")

 
    def addfield(page,tempname,rarity,have):
        page.add_field(name=f"{have} {tempname.capitalize()}",value=f"{rarity.capitalize()}", inline=True)


    # hashyper = userDB.find_one({"id":member.id, "characters":{"$elemMatch": {"show":showInput,"rarity":'hyperlegendary'}}})
    # if hashyper == None:
    charlist = charDB.find({"show":showInput}).sort("rarityrank")
    for y in charlist:
        charshow=y["show"]
        if charshow == showInput: 
            charFound=False
            for t in userChars:
                if y['name'] == t["name"]:
                    addfield(singlePage,y["name"],y["rarity"],"✅")
                    charFound = True
            if charFound == False:
                addfield(singlePage,y["name"],y["rarity"],"❌")
    # else:
    #     charlist = charDB.find({"show":showInput}).sort("rarityrank")
    #     for y in charlist:
    #         addfield(singlePage,y['name'],y['rarity'],"✅")


    singlePage.set_thumbnail(url = showFound['thumbnail'])
  
    await ctx.send(embed = singlePage)
    commanduser = ctx.author
    await send_logs_acbs(commanduser,member, guild, "acbankspecific",showInput)
    return

def ouptputprefix(ctx):
    # getPrefix = prefixDB.find_one({"serverid":ctx.guild.id})
    # prefix = getPrefix["prefix"]
    return "!"

# async def createServerPrefix(guild):
#     guildname = guild.name
#     newuser = {"serverid": guild.id,"servername":guildname,"prefix":"!"}
#     prefixDB.insert_one(newuser)

# @client.command(aliases=['ACprefix'])
# @has_permissions(administrator=True)
# async def acprefix(ctx, prefix=None):
#     if prefix is None:
#         em = discord.Embed(title = f"{cmdPrefix}prefix <prefix>",color = discord.Color.red())
#         await ctx.send(embed=em)
#         return
#     guild = ctx.message.guild
#     guildid = guild.id
#     data = prefixDB.find_one({"serverid":guildid})
#     if data is None:
#         await createServerPrefix(guild)
#         prefixDB.update_one({"serverid":guildid}, {"$set":{"prefix":prefix}})
#         return
#     else:
#         prefixDB.update_one({"serverid":guildid}, {"$set":{"prefix":prefix}})
#         em = discord.Embed(title = f"Prefix changed to {prefix}",color = discord.Color.teal())
#         await ctx.send(embed=em)
#         return

# @client.command(aliases = ['aclb', 'acLeaderboard', 'ACLb', 'acLB','ACLEADERBOARD'])
# @commands.cooldown(1, 5, commands.BucketType.user)
# async def acleaderboard(ctx,type = None): 
#     member = ctx.author
#     guild=ctx.message.guild
#     botStats = botstatsDB.find_one({"id":573})
#     if botStats['botOffline']==True or botOnline==False:
#         em = discord.Embed(title = f"ACleaderboard - {member.name}\nThe bot is rebooting...!\nTry again in a few minutes.",color = getColor('botColor'))
#         em.set_thumbnail(url = member.avatar_url)
#         await ctx.send(embed = em)
#         return


#     rankings = userDB.find().sort("charsunlocked", -1)
#     i = 1
#     homeem = discord.Embed(title = f"Local Characters Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.teal())
#     for x in rankings:
#         try:
#             temp = ctx.guild.get_member(x["id"])
#             if x["currentchar"] == None:
#                 tempcurr = "None"
#             else:
#                 tempcurr = x["currentchar"]
#             homeem.add_field(name=f'**{i}: {temp.name}**', value=f'Characters: **{x["charsunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#             i += 1
#         except:
#             pass
#         if i == 11:
#             break
#     homeem.set_thumbnail(url = member.avatar_url)
    
    
        

#     components = [

#         [
#             Select(placeholder=f"Leaderboard Type",
#             options=[
#                 SelectOption(label= 'Total Characters',value='option1',emoji='💯'),
#                 SelectOption(label= 'Hyper Legendaries',value='option2',emoji='👑'),
#                 SelectOption(label= 'Legendaries',value='option3',emoji='🟡'),
#                 SelectOption(label= 'Epics',value='option4',emoji='🟣')
                
#             ]
        
#         )],
        
#         [
#             Button(style=ButtonStyle.blue,label='Local',disabled=True),
#             Button(style=ButtonStyle.blue,label='Global'),
#             Button(style=ButtonStyle.red,label='Close')
#         ]
#     ]
#     Globalcomponents = [

#         [
#             Select(placeholder=f"Leaderboard Type",
#             options=[
#                 SelectOption(label= 'Total Characters',value='option1',emoji='💯'),
#                 SelectOption(label= 'Hyper Legendaries',value='option2',emoji='👑'),
#                 SelectOption(label= 'Legendaries',value='option3',emoji='🟡'),
#                 SelectOption(label= 'Epics',value='option4',emoji='🟣')
                
#             ]
        
#         )],
        
#         [
#             Button(style=ButtonStyle.blue,label='Local'),
#             Button(style=ButtonStyle.blue,label='Global',disabled=True),
#             Button(style=ButtonStyle.red,label='Close')
#         ]
#     ]




#     message = await ctx.send(embed = homeem,components = components)
#     def checkauthor(user):
#         return lambda res: res.author == user and res.message == message

#     lbType = 0 # 0 = local, 1 = global
#     lbpageOn = 1

#     while True:
#         try:
#             event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=15.0)
#             try:
#                 if event.values[0] == 'option1':
#                     lbpageOn = 1
#                     if lbType == 0:
#                         rankings = userDB.find().sort("charsunlocked", -1)
#                         i = 1
#                         homeem = discord.Embed(title = f"Local Characters Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.teal())
#                         for x in rankings:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 homeem.add_field(name=f'**{i}: {temp.name}**', value=f'Characters: **{x["charsunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         homeem.set_thumbnail(url = member.avatar_url)
#                     else:
#                         rankings = userDB.find().sort("charsunlocked", -1)
#                         i = 1
#                         homeem = discord.Embed(title = f"Global Characters Leaderboard",description=f"Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)", color = discord.Color.teal())
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 homeem.add_field(name=f'**{i}: {x["name"]}**', value=f'Characters: **{x["charsunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         homeem.set_thumbnail(url = member.avatar_url)
#                     await event.respond(content='',embed=homeem,type=7)

#                 elif event.values[0] == 'option2':
#                     lbpageOn = 2
#                     if lbType == 0:
#                         rankings = userDB.find().sort("hypersunlocked", -1)
#                         hyplegendaryem = discord.Embed(title = f"Local Hyper Legendary Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = getColor("hyperlegendary"))
#                         i=1
#                         for x in rankings:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 hyplegendaryem.add_field(name=f'**{i}: {temp.name}**', value=f'Hyper Legendaries: **{x["hypersunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         hyplegendaryem.set_thumbnail(url = member.avatar_url)
#                     else:
#                         rankings = userDB.find().sort("hypersunlocked", -1)
#                         hyplegendaryem = discord.Embed(title = f"Global Hyper Legendary Leaderboard", color = getColor("hyperlegendary"))
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 hyplegendaryem.add_field(name=f'**{i}: {x["name"]}**', value=f'Hyper Legendaries: **{x["hypersunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         hyplegendaryem.set_thumbnail(url = member.avatar_url)
#                     await event.respond(content='',embed=hyplegendaryem,type=7)

#                 elif event.values[0] == 'option3':
#                     lbpageOn = 3
#                     if lbType == 0:
#                         rankingsL = userDB.find().sort("legendsunlocked", -1)
#                         legendaryem = discord.Embed(title = f"Local Legendary Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.gold())
#                         i=1
#                         for x in rankingsL:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 legendaryem.add_field(name=f'**{i}: {temp.name}**', value=f'Legendaries: **{x["legendsunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         legendaryem.set_thumbnail(url = member.avatar_url)
#                     else:
#                         rankings = userDB.find().sort("legendsunlocked", -1)
#                         legendaryem = discord.Embed(title = f"Global Legendary Leaderboard", color = discord.Color.gold())
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 legendaryem.add_field(name=f'**{i}: {x["name"]}**', value=f'Legendaries: **{x["legendsunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         legendaryem.set_thumbnail(url = member.avatar_url)
#                     await event.respond(content='',embed=legendaryem,type=7)


#                 elif event.values[0] == 'option4':
#                     lbpageOn = 4
#                     if lbType == 0:
#                         rankingsE = userDB.find().sort("legunlocked", -1)
#                         epicem = discord.Embed(title = f"Local Epic Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.purple())
#                         i=1
#                         for x in rankingsE:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 epicem.add_field(name=f'**{i}: {temp.name}**', value=f'Epics: **{x["legunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         epicem.set_thumbnail(url = member.avatar_url)
#                     else:
#                         rankings = userDB.find().sort("legunlocked", -1)
#                         epicem = discord.Embed(title = f"Global Epic Leaderboard", color = discord.Color.purple())
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 epicem.add_field(name=f'**{i}: {x["name"]}**', value=f'Epics: **{x["legunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         epicem.set_thumbnail(url = member.avatar_url)
#                     await event.respond(content='',embed=epicem,type=7)

#             except:
#                 if event.component.label == 'Close':
#                     break

#                 elif event.component.label == 'Local':
#                     lbType = 0
#                     if lbpageOn == 1:
#                         rankings = userDB.find().sort("charsunlocked", -1)
#                         i = 1
#                         homeem = discord.Embed(title = f"Local Characters Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.teal())
#                         for x in rankings:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 homeem.add_field(name=f'**{i}: {temp.name}**', value=f'Characters: **{x["charsunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         homeem.set_thumbnail(url = member.avatar_url)

#                         await event.respond(content='',embed=homeem,components=components,type=7)

#                     elif lbpageOn == 2:
#                         rankings = userDB.find().sort("hypersunlocked", -1)
#                         hyplegendaryem = discord.Embed(title = f"Local Hyper Legendary Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = getColor("hyperlegendary"))
#                         i=1
#                         for x in rankings:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 hyplegendaryem.add_field(name=f'**{i}: {temp.name}**', value=f'Hyper Legendaries: **{x["hypersunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         hyplegendaryem.set_thumbnail(url = member.avatar_url)

#                         await event.respond(content='',embed=hyplegendaryem,components=components,type=7)

#                     elif lbpageOn == 3:
#                         rankingsL = userDB.find().sort("legendsunlocked", -1)
#                         legendaryem = discord.Embed(title = f"Local Legendary Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.gold())
#                         i=1
#                         for x in rankingsL:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 legendaryem.add_field(name=f'**{i}: {temp.name}**', value=f'Legendaries: **{x["legendsunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         legendaryem.set_thumbnail(url = member.avatar_url)
#                         await event.respond(content='',embed=legendaryem,components=components,type=7)
                    
#                     elif lbpageOn == 4:
#                         rankingsE = userDB.find().sort("legunlocked", -1)
#                         epicem = discord.Embed(title = f"Local Epic Leaderboard",description=f"**Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)**", color = discord.Color.purple())
#                         i=1
#                         for x in rankingsE:
#                             try:
#                                 temp = ctx.guild.get_member(x["id"])
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 epicem.add_field(name=f'**{i}: {temp.name}**', value=f'Epics: **{x["legunlocked"]}**\nSelected Character: **{tempcurr.capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         epicem.set_thumbnail(url = member.avatar_url)

#                         await event.respond(content='',embed=epicem,components=components,type=7)


#                 elif event.component.label == 'Global':
#                     lbType = 1
#                     if lbpageOn == 1:
#                         rankings = userDB.find().sort("charsunlocked", -1)
#                         i = 1
#                         homeem = discord.Embed(title = f"Global Characters Leaderboard",description=f"Your personal rank is displayed on your profile! ({ouptputprefix(ctx)}acp)", color = discord.Color.teal())
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 homeem.add_field(name=f'**{i}: {x["name"]}**', value=f'Characters: **{x["charsunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         homeem.set_thumbnail(url = member.avatar_url)
#                         await event.respond(content='',embed=homeem,components=Globalcomponents,type=7)

#                     elif lbpageOn == 2:
#                         rankings = userDB.find().sort("hypersunlocked", -1)
#                         hyplegendaryem = discord.Embed(title = f"Global Hyper Legendary Leaderboard", color = getColor("hyperlegendary"))
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 hyplegendaryem.add_field(name=f'**{i}: {x["name"]}**', value=f'Hyper Legendaries: **{x["hypersunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         hyplegendaryem.set_thumbnail(url = member.avatar_url)
#                         await event.respond(content='',embed=hyplegendaryem,components=Globalcomponents,type=7)
                    
#                     elif lbpageOn == 3:
#                         rankings = userDB.find().sort("legendsunlocked", -1)
#                         legendaryem = discord.Embed(title = f"Global Legendary Leaderboard", color = discord.Color.gold())
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 legendaryem.add_field(name=f'**{i}: {x["name"]}**', value=f'Legendaries: **{x["legendsunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         legendaryem.set_thumbnail(url = member.avatar_url)
#                         await event.respond(content='',embed=legendaryem,components=Globalcomponents,type=7)

#                     elif lbpageOn == 4:
#                         rankings = userDB.find().sort("legunlocked", -1)
#                         epicem = discord.Embed(title = f"Global Epic Leaderboard", color = discord.Color.purple())
#                         i=1
#                         for x in rankings:
#                             try:
#                                 if x["currentchar"] == None:
#                                     tempcurr = "None"
#                                 else:
#                                     tempcurr = x["currentchar"]
#                                 epicem.add_field(name=f'**{i}: {x["name"]}**', value=f'Epics: **{x["legunlocked"]}**\nSelected Character: **{x["currentchar"].capitalize()}**', inline=False)
#                                 i += 1
#                             except:
#                                 pass
#                             if i == 11:
#                                 break
#                         epicem.set_thumbnail(url = member.avatar_url)
#                         await event.respond(content='',embed=epicem,components=Globalcomponents,type=7)

#         except:
#             break

   

#     buttons = []
#     await message.edit(components=buttons)
#     await send_logs(member,guild,"acleaderboard")
#     return


@client.command(aliases = ['acls','ACLS','Acls','ACLOADINGSCREEN','ACloadingcreen','ACls'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def acloadingscreen(ctx,member:discord.Member=None):
    member = ctx.author
    botstat = botstatsDB.find_one({'id':573})
    if botstat['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    userProfile = userDB.find_one({'id':member.id})
    
    screenList = []
    amntScreens=0
    try:
        userScreens = userProfile['loadingscreens']
        for x in userScreens:
            amntScreens+=1
            screenList.append(int(x['number']))
    except:
        pass

    try:
        currentLS = userProfile['currentloadingscreen']
    except:
        try:
            findLS = loadingScreenDB.find_one({'number':screenList[0]})
            userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLS['gif']}})
            currentLS = findLS['gif']
            userProfile = userDB.find_one({'id':member.id})
        except:
            em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"You don't have any unlocked Loading Screens!\nYou can buy loading screens in the shop (!accs) for ${botstat['lsbaseprice']}",color = discord.Color.teal())
            em.set_thumbnail(url=member.avatar_url)
            await ctx.send(embed=em)
            return


    try:
        lstype = userProfile['lstype']
    except:
        userDB.update_one({"id":member.id}, {"$set":{"lstype":'Select'}})
        lstype = 'Select'
        userProfile = userDB.find_one({'id':member.id})


    if amntScreens==0:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"You don't have any unlocked Loading Screens!\nYou can buy loading screens in the shop (!accs) for ${botstat['lsbaseprice']}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    elif amntScreens == 1:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        await ctx.send(embed=em)
        await send_logs_loading(member,ctx.message.guild,"acls","full")
        return
    
    elif amntScreens==2:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3')
                    

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3')
                    

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]

    elif amntScreens == 3:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4')
                

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4')
                    
                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]


    elif amntScreens == 4:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5')
                   

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5')
                    

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]


    elif amntScreens == 5:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]
    
    elif amntScreens == 6:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6'),
                    SelectOption(label= 'Loading Screen 6',value='option7')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6'),
                        SelectOption(label= 'Loading Screen 6',value='option7')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]
    
    elif amntScreens == 7:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6'),
                    SelectOption(label= 'Loading Screen 6',value='option7'),
                    SelectOption(label= 'Loading Screen 7',value='option8')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6'),
                        SelectOption(label= 'Loading Screen 6',value='option7'),
                        SelectOption(label= 'Loading Screen 7',value='option8')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]
    
    elif amntScreens == 8:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6'),
                    SelectOption(label= 'Loading Screen 6',value='option7'),
                    SelectOption(label= 'Loading Screen 7',value='option8'),
                    SelectOption(label= 'Loading Screen 8',value='option9')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6'),
                        SelectOption(label= 'Loading Screen 6',value='option7'),
                        SelectOption(label= 'Loading Screen 7',value='option8'),
                        SelectOption(label= 'Loading Screen 8',value='option9')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]

    elif amntScreens == 9:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6'),
                    SelectOption(label= 'Loading Screen 6',value='option7'),
                    SelectOption(label= 'Loading Screen 7',value='option8'),
                    SelectOption(label= 'Loading Screen 8',value='option9'),
                    SelectOption(label= 'Loading Screen 9',value='option10')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6'),
                        SelectOption(label= 'Loading Screen 6',value='option7'),
                        SelectOption(label= 'Loading Screen 7',value='option8'),
                        SelectOption(label= 'Loading Screen 8',value='option9'),
                        SelectOption(label= 'Loading Screen 9',value='option10')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]
    
    elif amntScreens == 10:
        em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        em.set_image(url=currentLS)
        homecomponents=[
            [
                Select(placeholder=f"Select Loading Screen",
                options=[
                    SelectOption(label= 'Current Loading Screen',value='option1'),
                    SelectOption(label= 'Loading Screen 1',value='option2'),
                    SelectOption(label= 'Loading Screen 2',value='option3'),
                    SelectOption(label= 'Loading Screen 3',value='option4'),
                    SelectOption(label= 'Loading Screen 4',value='option5'),
                    SelectOption(label= 'Loading Screen 5',value='option6'),
                    SelectOption(label= 'Loading Screen 6',value='option7'),
                    SelectOption(label= 'Loading Screen 7',value='option8'),
                    SelectOption(label= 'Loading Screen 8',value='option9'),
                    SelectOption(label= 'Loading Screen 9',value='option10'),
                    SelectOption(label= 'Loading Screen 10',value='option11')

                ]
            )],
            
            [
                Button(style=ButtonStyle.green,label='Select',disabled=True),
                Button(style=ButtonStyle.blue,label='Random'),
                Button(style=ButtonStyle.red,label='Close')
            ]
        ]
    
        newcomponents=[
                [
                    Select(placeholder=f"Select Loading Screen",
                    options=[
                        SelectOption(label= 'Current Loading Screen',value='option1'),
                        SelectOption(label= 'Loading Screen 1',value='option2'),
                        SelectOption(label= 'Loading Screen 2',value='option3'),
                        SelectOption(label= 'Loading Screen 3',value='option4'),
                        SelectOption(label= 'Loading Screen 4',value='option5'),
                        SelectOption(label= 'Loading Screen 5',value='option6'),
                        SelectOption(label= 'Loading Screen 6',value='option7'),
                        SelectOption(label= 'Loading Screen 7',value='option8'),
                        SelectOption(label= 'Loading Screen 8',value='option9'),
                        SelectOption(label= 'Loading Screen 9',value='option10'),
                        SelectOption(label= 'Loading Screen 10',value='option11')

                    ]
                )],
                
                [
                    Button(style=ButtonStyle.green,label='Select'),
                    Button(style=ButtonStyle.blue,label='Random'),
                    Button(style=ButtonStyle.red,label='Close')
                ]
            ]


    
    message = await ctx.send(embed=em,components=homecomponents)

    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    
    pageOnLs = 0

    while True:
        try:
            event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=15.0)

            try:
                if event.values[0] == 'option1':
                    pageOnLs=0
                    await event.respond(content='',embed=em,components=homecomponents,type=7)
                    
                
                elif event.values[0] == 'option2':
                    pageOnLs = 1
                    ls = loadingScreenDB.find_one({'number':screenList[0]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 1**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])
                    
                    await event.respond(content='',embed=newem,components=newcomponents,type=7)
                    
                
                elif event.values[0] == 'option3':
                    pageOnLs = 2
                    ls = loadingScreenDB.find_one({'number':screenList[1]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 2**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option4':
                    pageOnLs = 3
                    ls = loadingScreenDB.find_one({'number':screenList[2]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 3**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option5':
                    pageOnLs = 4
                    ls = loadingScreenDB.find_one({'number':screenList[3]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 4**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option6':
                    pageOnLs = 5
                    ls = loadingScreenDB.find_one({'number':screenList[4]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 5**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option7':
                    pageOnLs = 6
                    ls = loadingScreenDB.find_one({'number':screenList[5]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 6**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)
                
                elif event.values[0] == 'option8':
                    pageOnLs = 7
                    ls = loadingScreenDB.find_one({'number':screenList[6]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 7**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option9':
                    pageOnLs = 8
                    ls = loadingScreenDB.find_one({'number':screenList[7]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 8**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)

                elif event.values[0] == 'option10':
                    pageOnLs = 9
                    ls = loadingScreenDB.find_one({'number':screenList[8]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 9**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)
                
                elif event.values[0] == 'option11':
                    pageOnLs = 10
                    ls = loadingScreenDB.find_one({'number':screenList[9]})
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen 10**",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    newem.set_image(url=ls['gif'])

                    await event.respond(content='',embed=newem,components=newcomponents,type=7)


            except:
                if event.component.label == 'Close':
                    break
                elif event.component.label == 'Select':
                    if pageOnLs == 1:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[0]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[0])
                    elif pageOnLs == 2:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[1]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[1])
                    elif pageOnLs == 3:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[2]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[2])
                    elif pageOnLs == 4:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[3]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[3])
                    elif pageOnLs == 5:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[4]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[4])
                    elif pageOnLs == 6:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[5]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[5])
                    elif pageOnLs == 7:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[6]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[6])
                    elif pageOnLs == 8:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[7]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[7])
                    elif pageOnLs == 9:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[8]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[8])
                    elif pageOnLs == 10:
                        findLSnew = loadingScreenDB.find_one({'number':screenList[9]})
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLSnew['gif']}})
                        await send_logs_loading(member,ctx.message.guild,"select",screenList[9])

                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Selection Successful',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userDB.update_one({"id":member.id}, {"$set":{"lstype":'Select'}})
                    selectEm = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Loading Screen Selected**",color = discord.Color.teal())
                    selectEm.set_thumbnail(url=member.avatar_url)
                    selectEm.set_image(url=findLSnew['gif'])
                    

                    await event.respond(content='',embed=selectEm,components=newbuttons,type=7)

                elif event.component.label == 'Random':
                    newem = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"You will now get a **random** Loading Screen from your collection every !acr or !acrp",color = discord.Color.teal())
                    newem.set_thumbnail(url=member.avatar_url)
                    try:
                        newem.set_image(url=ls['gif'])
                    except:
                        newem.set_image(url=currentLS)

                    randbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Set to Random',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    userDB.update_one({"id":member.id}, {"$set":{"lstype":'Random'}})
                    await send_logs_loading(member,ctx.message.guild,"random","random")

                    await event.respond(content='',embed=newem,components=randbuttons,type=7)

                elif event.component.label == 'Home':
                    pageOnLs=0
                    userProfile = userDB.find_one({'id':member.id})
                    lstype = userProfile['lstype']
                    currentLS = userProfile['currentloadingscreen']
                    em = discord.Embed(title = f"ACloadingscreen - {member.name}",description=f"**Current Loading Screen**\nType: {lstype}",color = discord.Color.teal())
                    em.set_thumbnail(url=member.avatar_url)
                    em.set_image(url=currentLS)

                    await event.respond(content='',embed=em,components=homecomponents,type=7)

        except:
            break

    blankbuttons=[]
    await message.edit(components=blankbuttons)
    await send_logs_loading(member,ctx.message.guild,"acls","full")
    return

@client.command(aliases = ['accs', 'ACCS', 'ACCHARACTERSHOP', 'Accs','Accharactershop'])
@commands.cooldown(1, 2, commands.BucketType.user)
async def accharactershop(ctx): 
    member=ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACcharactershop - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createshopuser(member,ctx.message.guild)
    em = discord.Embed(title = f"ACcharactershop - {member.name}\nLoading...",color = getColor("botColor"))
    em.set_thumbnail(url = member.avatar_url)
    message = await ctx.send(embed = em)

    todayDisplay = datetime.datetime.utcnow()
    def resetShop():
        shopDB.update_one({"id":member.id}, {"$set":{"boughtuncommon":False,"boughtrare":False,"boughtepic":False,"boughtlegendary1":False,"boughtlegendary2":False,"boughtloading":False}})

        for x in range(7):
            randNum = random.randint(1,100000000000)
            # randseed = int(member.id + randNum)
            random.seed(randNum)
            try:
                ublocks = blockDB.find_one({'id':member.id})
                blist = ublocks['blocklist']
                newblist = []
                for itm in blist:
                    newblist.append(itm['show'])
            except:
                newblist=[]
            if x == 1:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                uncChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while uncChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    uncChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":uncChar["name"],"show":uncChar["show"],"rarity":uncChar["rarity"]}}})
            if x == 2:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                rareChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while rareChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    rareChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":rareChar["name"],"show":rareChar["show"],"rarity":rareChar["rarity"]}}})
            if x == 3:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                epicChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while epicChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    epicChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":epicChar["name"],"show":epicChar["show"],"rarity":epicChar["rarity"]}}})
            if x == 4:
                max = charDB.count_documents({"rarity":rarities[x]})
                randomInt = random.randint(1,max) 
                legendaryChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                while legendaryChar['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    legendaryChar = charDB.find_one({"rarity":rarities[x], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":legendaryChar["name"],"show":legendaryChar["show"],"rarity":legendaryChar["rarity"]}}})
            if x == 5:
                max = charDB.count_documents({"rarity":rarities[4]})
                randomInt = random.randint(1,max) 
                legChar2 = charDB.find_one({"rarity":rarities[4], "raritynumber": randomInt})
                while legChar2['show'] in newblist:
                    randomInt = random.randint(1,max) 
                    legChar2 = charDB.find_one({"rarity":rarities[4], "raritynumber": randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"name":legChar2["name"],"show":legChar2["show"],"rarity":legChar2["rarity"]}}})
            if x == 6:
                max = loadingScreenDB.count_documents({})
                randomInt = random.randint(1,max) 
                loadingScreen = loadingScreenDB.find_one({'number':randomInt})
                shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"number":loadingScreen["number"]}}})


    user = shopDB.find_one({"id":member.id})

    todaysDay = todayDisplay.day
    todaysMonth = todayDisplay.month 
    
    
    try:
        indvMonth = user["month"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"month":todaysMonth}})
        #userDB.update_one({"id":member.id}, {"$set":{"nextmonth":todayDisplay.month+1}})
        user = shopDB.find_one({"id":member.id})
        indvMonth = user["month"]
    
   
    if todaysMonth != indvMonth:
        #userDB.update_one({"id":member.id}, {"$set":{"today":1}})
        tomorow = datetime.datetime.utcnow() + datetime.timedelta(days = 1)
        shopDB.update_one({"id":member.id}, {"$set":{"tomorrow":tomorow.day}})
        shopDB.update_one({"id":member.id}, {"$set":{"month":todaysMonth}})
        try:
            userShop = user["characterShop"]
            shopDB.update_one({"id":member.id}, {"$set":{"characterShop":[]}})
        except:
            pass
        resetShop()
        em = discord.Embed(title = f"ACcharactershop - {member.name}\nYour shop has been reset since you last checked, please do !accs again to see what you got!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await message.edit(embed = em)
        return

    # if todaysMonth == 1:
    #     shopDB.update_one({"id":member.id}, {"$set":{"month":todaysMonth}})

    #print(todaysMonth)

    gethour = datetime.datetime.utcnow()
    currenthour = gethour.hour
    currentminute = gethour.minute
    # currentsecond = gethour.second

    user = shopDB.find_one({"id":member.id})
    charShoplist = []
    try:
        indvTomorrow = user["tomorrow"]
    except:
        #userDB.update_one({"id":member.id}, {"$set":{"today":todayDisplay.day}})
        tomorow = datetime.datetime.utcnow() + datetime.timedelta(days = 1)
        
        shopDB.update_one({"id":member.id}, {"$set":{"tomorrow":tomorow.day}})
        user = shopDB.find_one({"id":member.id})
        indvTomorrow = user["tomorrow"]
        try:
            userShop = user["characterShop"]
            shopDB.update_one({"id":member.id}, {"$set":{"characterShop":[]}})
        except:
            pass
        resetShop()
        em = discord.Embed(title = f"ACcharactershop - {member.name}\nYour shop has been reset since you last checked, please do !accs again to see what you got!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await message.edit(embed = em)
        return

    if indvTomorrow >= todaysDay + 2:
        tomorow = datetime.datetime.utcnow() + datetime.timedelta(days = 1)
        shopDB.update_one({"id":member.id}, {"$set":{"tomorrow":tomorow.day}})
        user = shopDB.find_one({"id":member.id})
        indvTomorrow = user["tomorrow"]
        try:
            userShop = user["characterShop"]
            shopDB.update_one({"id":member.id}, {"$set":{"characterShop":[]}})
        except:
            pass
        resetShop()
        em = discord.Embed(title = f"ACcharactershop - {member.name}\nYour shop has been reset since you last checked, please do !accs again to see what you got!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await message.edit(embed = em)
        return

    if ((indvTomorrow == 1 and todaysDay == 1) or (indvTomorrow == 1 and todaysDay == 31) or (indvTomorrow == 1 and todaysDay == 28) or (indvTomorrow == 1 and todaysDay == 29) or (indvTomorrow == 1 and todaysDay == 30)):
        user = shopDB.find_one({"id":member.id})
        userShop = user["characterShop"]
        for x in userShop:
            try:
                charShoplist.append(x["name"])
            except:
                charShoplist.append(x["number"])
    elif todaysDay >= indvTomorrow:
        d2 = datetime.datetime.utcnow() + datetime.timedelta(days = 1)
        shopDB.update_one({"id":member.id}, {"$set":{"tomorrow":d2.day}})
        try:
            shopDB.update_one({"id":member.id}, {"$set":{"characterShop":[]}})
            resetShop()
            user = shopDB.find_one({"id":member.id})
            userShop = user["characterShop"]
            for x in userShop:
                try:
                    charShoplist.append(x["name"])
                except:
                    charShoplist.append(x["number"])
        except:
            resetShop()
            userShop = user["characterShop"]
            for x in userShop:
                try:
                    charShoplist.append(x["name"])
                except:
                    charShoplist.append(x["number"])
        em = discord.Embed(title = f"ACcharactershop - {member.name}\nYour shop has been reset since you last checked, please do !accs again to see what you got!",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await message.edit(embed = em)
        return
    
    else:
        user = shopDB.find_one({"id":member.id})
        userShop = user["characterShop"]
        if len(userShop) != 6:
            shopDB.update_one({"id":member.id}, {"$set":{"characterShop":[]}})
            resetShop()
            user = shopDB.find_one({"id":member.id})
            userShop = user["characterShop"]
        for x in userShop:
            try:
                charShoplist.append(x["name"])
            except:
                charShoplist.append(x["number"])
    
  
    
    uncommonChar = charDB.find_one({"name":charShoplist[0]})
    rareChar = charDB.find_one({"name":charShoplist[1]})
    epicChar = charDB.find_one({"name":charShoplist[2]})
    legendaryChar1 = charDB.find_one({"name":charShoplist[3]})
    legendaryChar2 = charDB.find_one({"name":charShoplist[4]})
    loadingScreen = loadingScreenDB.find_one({"number":charShoplist[5]})

    #commonprice = botStats["commonbaseprice"]
    uncommonprice = botStats["uncommonbaseprice"]
    rareprice = botStats["rarebaseprice"]
    epicprice = botStats["epicbaseprice"]
    legendaryprice = botStats["legendarybaseprice"]
    loadingprice = botStats['lsbaseprice']


    usermoney = user["money"]

    homeem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"Resets at **5:00 PM** PST Daily!\n**Time Until Next Reset: {23 - currenthour} hours {60-currentminute} minutes**\nTo reset your shop manually for **${botStats['shopresetamount']}** use **!acresetshop**\n**User Balance: ${usermoney}**", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)
    homeem.set_image(url="https://media1.tenor.com/images/52950888781d0f27f61df71442f176cd/tenor.gif?itemid=5078001")
    

    userProf = shopDB.find_one({"id":member.id})
    try:
        boughtun = userProf["boughtuncommon"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtuncommon":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtun = userProf["boughtuncommon"]
    try:
        boughtrare = userProf["boughtrare"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtrare":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtrare = userProf["boughtrare"]
    try:
        boughtepic = userProf["boughtepic"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtepic":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtepic = userProf["boughtepic"]
    try:
        boughtleg1 = userProf["boughtlegendary1"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtlegendary1":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtleg1 = userProf["boughtlegendary1"]
    try:
        boughtleg2 = userProf["boughtlegendary2"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtlegendary2":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtleg2 = userProf["boughtlegendary2"]
    try:
        boughtloading = userProf["boughtloading"]
    except:
        shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":False}})
        userProf = shopDB.find_one({"id":member.id})
        boughtloading = userProf["boughtloading"]

    homecomponents=[
        [
            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
            options=[
                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
            ]
        
        )],
        
        [
            Button(style=ButtonStyle.green,label='Buy',disabled=True),
            Button(style=ButtonStyle.blue,label='Buy SP'),
            Button(style=ButtonStyle.blue,label='Reset LS'),
            Button(style=ButtonStyle.red,label='Close')
        ]
    ]
    components = [

        [
            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
            options=[
                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
            ]
        
        )],
        
        [
            Button(style=ButtonStyle.green,label='Buy'),
            Button(style=ButtonStyle.blue,label='Buy SP'),
            Button(style=ButtonStyle.blue,label='Reset LS'),
            Button(style=ButtonStyle.red,label='Close')
        ]
    ]

     
    await message.edit(components=homecomponents,embed = homeem)

    
    def checkauthor(user):
        return lambda res: res.author == user and res.message == message

    pageOn = 0

    botStat = botstatsDB.find_one({'id':573})
    while True:
        try:
            event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=15.0)
            
            try:
                if event.values[0] == 'option1':
                    pageOn = 0
                    await event.respond(content='',embed=homeem,components=homecomponents,type=7)

                elif event.values[0] == 'option2':
                    pageOn = 1
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    showOut = showDB.find_one({'name':uncommonChar['show']})
                    uncommonem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",color = getColor(uncommonChar['rarity']))
                    uncommonem.add_field(name=f"{uncommonChar['name'].capitalize()}",value=f"**Show:** {showOut['title']} ({showOut['abv']})\n**Rarity:** {uncommonChar['rarity'].capitalize()}",inline=True)
                    uncommonem.add_field(name="Price",value=f"${uncommonprice}",inline=True)
                    uprof = userDB.find_one({"id":member.id})
                    uchars = uprof['characters']
                    owned = False
                    for char in uchars:
                        if char['name'] == uncommonChar['name']:
                            owned = True
                            break
                    if owned == True:
                        uncommonem.add_field(name="**Owned**",value=f"✅",inline=True)
                    else:
                        uncommonem.add_field(name="**Owned**",value=f"❌",inline=True)
                    uncommonem.set_image(url = uncommonChar['gif'])
                    uncommonem.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=uncommonem,components=components,type=7)

                elif event.values[0] == 'option3':
                    pageOn = 2
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    showOutrare = showDB.find_one({'name':rareChar['show']})
                    rareem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",color = getColor(rareChar['rarity']))
                    rareem.add_field(name=f"**{rareChar['name'].capitalize()}**",value=f"Show: {showOutrare['title']} ({showOutrare['abv']})\nRarity: {rareChar['rarity'].capitalize()}",inline=True)
                    rareem.add_field(name="**Price**",value=f"${rareprice}",inline=True)
                    uprof = userDB.find_one({"id":member.id})
                    uchars = uprof['characters']
                    owned = False
                    for char in uchars:
                        if char['name'] == rareChar['name']:
                            owned = True
                            break
                    if owned == True:
                        rareem.add_field(name="**Owned**",value=f"✅",inline=True)
                    else:
                        rareem.add_field(name="**Owned**",value=f"❌",inline=True)
                    rareem.set_image(url = rareChar['gif'])
                    rareem.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=rareem,components=components,type=7)

                elif event.values[0] == 'option4':
                    pageOn = 3
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    showOutepic = showDB.find_one({'name':epicChar['show']})
                    epicem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",color = getColor(epicChar['rarity']))
                    epicem.add_field(name=f"{epicChar['name'].capitalize()}",value=f"**Show:** {showOutepic['title']} ({showOutepic['abv']})\n**Rarity:** {epicChar['rarity'].capitalize()}",inline=True)
                    epicem.add_field(name="Price",value=f"${epicprice}",inline=True)
                    uprof = userDB.find_one({"id":member.id})
                    uchars = uprof['characters']
                    owned = False
                    for char in uchars:
                        if char['name'] == epicChar['name']:
                            owned = True
                            break
                    if owned == True:
                        epicem.add_field(name="**Owned**",value=f"✅",inline=True)
                    else:
                        epicem.add_field(name="**Owned**",value=f"❌",inline=True)
                    epicem.set_image(url = epicChar['gif'])
                    epicem.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=epicem,components=components,type=7)

                elif event.values[0] == 'option5':
                    pageOn = 4
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    showOutleg = showDB.find_one({'name':legendaryChar1['show']})
                    legem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",color = getColor(legendaryChar1['rarity']))
                    legem.add_field(name=f"{legendaryChar1['name'].capitalize()}",value=f"**Show:** {showOutleg['title']} ({showOutleg['abv']})\n**Rarity:** {legendaryChar1['rarity'].capitalize()}",inline=True)
                    legem.add_field(name="Price",value=f"${legendaryprice}",inline=True)
                    uprof = userDB.find_one({"id":member.id})
                    uchars = uprof['characters']
                    owned = False
                    for char in uchars:
                        if char['name'] == legendaryChar1['name']:
                            owned = True
                            break
                    if owned == True:
                        legem.add_field(name="**Owned**",value=f"✅",inline=True)
                    else:
                        legem.add_field(name="**Owned**",value=f"❌",inline=True)
                    legem.set_image(url = legendaryChar1['gif'])
                    legem.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=legem,components=components,type=7)
                
                elif event.values[0] == 'option6':
                    pageOn = 5
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    showOutleg2 = showDB.find_one({'name':legendaryChar2['show']})
                    legem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",color = getColor(legendaryChar1['rarity']))
                    legem.add_field(name=f"{legendaryChar2['name'].capitalize()}",value=f"**Show:** {showOutleg2['title']} ({showOutleg2['abv']})\n**Rarity:** {legendaryChar2['rarity'].capitalize()}",inline=True)
                    legem.add_field(name="Price",value=f"${legendaryprice}",inline=True)
                    uprof = userDB.find_one({"id":member.id})
                    uchars = uprof['characters']
                    owned = False
                    for char in uchars:
                        if char['name'] == legendaryChar2['name']:
                            owned = True
                            break
                    if owned == True:
                        legem.add_field(name="**Owned**",value=f"✅",inline=True)
                    else:
                        legem.add_field(name="**Owned**",value=f"❌",inline=True)
                    legem.set_image(url = legendaryChar2['gif'])
                    legem.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=legem,components=components,type=7)
                
                elif event.values[0] == 'option7':
                    pageOn = 6
                    components = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy'),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]
                    Ls = loadingScreenDB.find_one({'number':loadingScreen['number']})
                    loadingEm = discord.Embed(title = f"ACraffle Character Shop - {member.name}\nLoading Screen",color = getColor('loadingscreen'))
                    loadingEm.add_field(name="Price",value=f"${loadingprice}",inline=True)
                    loadingEm.set_image(url = Ls['gif'])
                    loadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=loadingEm,components=components,type=7)

                elif event.values[0] == 'load1':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 1'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    await event.respond(content='',embed=findFirstLoadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load2':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 2'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    secondLoading = loadingScreenDB.find_one({'number':int(screenlist[1])})
                    secondLoadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    secondLoadingEm.set_image(url=secondLoading["gif"])
                    secondLoadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=secondLoadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load3':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 3'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    thirdLoading = loadingScreenDB.find_one({'number':int(screenlist[2])})
                    thirdLoadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    thirdLoadingEm.set_image(url=thirdLoading["gif"])
                    thirdLoadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=thirdLoadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load4':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 4'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    fourthLoading = loadingScreenDB.find_one({'number':int(screenlist[3])})
                    fourthLoadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    fourthLoadingEm.set_image(url=fourthLoading["gif"])
                    fourthLoadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=fourthLoadingEm,components=newbuttons,type=7)

                elif event.values[0] == 'load5':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 5'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    fifthLoading = loadingScreenDB.find_one({'number':int(screenlist[4])})
                    fifthLoadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    fifthLoadingEm.set_image(url=fifthLoading["gif"])
                    fifthLoadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=fifthLoadingEm,components=newbuttons,type=7)

                elif event.values[0] == 'load6':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 6'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    sixthloading = loadingScreenDB.find_one({'number':int(screenlist[5])})
                    sixthloadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    sixthloadingEm.set_image(url=sixthloading["gif"])
                    sixthloadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=sixthloadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load7':
                    newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 7'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]
                    seventhloading = loadingScreenDB.find_one({'number':int(screenlist[6])})
                    seventhloadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                    seventhloadingEm.set_image(url=seventhloading["gif"])
                    seventhloadingEm.set_thumbnail(url = member.avatar_url)
                    await event.respond(content='',embed=seventhloadingEm,components=newbuttons,type=7)
            
                elif event.values[0] == 'load8':
                        newbuttons = [
                                [
                                    Select(placeholder=f"Select One",
                                    options=[
                                        SelectOption(label= 'Loading Screen 1',value='load1'),
                                        SelectOption(label= 'Loading Screen 2',value='load2'),
                                        SelectOption(label= 'Loading Screen 3',value='load3'),
                                        SelectOption(label= 'Loading Screen 4',value='load4'),
                                        SelectOption(label= 'Loading Screen 5',value='load5'),
                                        SelectOption(label= 'Loading Screen 6',value='load6'),
                                        SelectOption(label= 'Loading Screen 7',value='load7'),
                                        SelectOption(label= 'Loading Screen 8',value='load8'),
                                        SelectOption(label= 'Loading Screen 9',value='load9'),
                                        SelectOption(label= 'Loading Screen 10',value='load10')
                                    ]

                                )],
                                [
                                Button(style=ButtonStyle.green,label=f'Replace 8'),
                                Button(style=ButtonStyle.red,label='Cancel Purchase')
                                ]
                            ]
                        eighthloading = loadingScreenDB.find_one({'number':int(screenlist[7])})
                        eighthloadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                        eighthloadingEm.set_image(url=eighthloading["gif"])
                        eighthloadingEm.set_thumbnail(url = member.avatar_url)
                        await event.respond(content='',embed=eighthloadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load9':
                        newbuttons = [
                                [
                                    Select(placeholder=f"Select One",
                                    options=[
                                        SelectOption(label= 'Loading Screen 1',value='load1'),
                                        SelectOption(label= 'Loading Screen 2',value='load2'),
                                        SelectOption(label= 'Loading Screen 3',value='load3'),
                                        SelectOption(label= 'Loading Screen 4',value='load4'),
                                        SelectOption(label= 'Loading Screen 5',value='load5'),
                                        SelectOption(label= 'Loading Screen 6',value='load6'),
                                        SelectOption(label= 'Loading Screen 7',value='load7'),
                                        SelectOption(label= 'Loading Screen 8',value='load8'),
                                        SelectOption(label= 'Loading Screen 9',value='load9'),
                                        SelectOption(label= 'Loading Screen 10',value='load10')
                                    ]

                                )],
                                [
                                Button(style=ButtonStyle.green,label=f'Replace 9'),
                                Button(style=ButtonStyle.red,label='Cancel Purchase')
                                ]
                            ]
                        ninthloading = loadingScreenDB.find_one({'number':int(screenlist[8])})
                        ninthloadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                        ninthloadingEm.set_image(url=ninthloading["gif"])
                        ninthloadingEm.set_thumbnail(url = member.avatar_url)
                        await event.respond(content='',embed=ninthloadingEm,components=newbuttons,type=7)
                
                elif event.values[0] == 'load10':
                        newbuttons = [
                                [
                                    Select(placeholder=f"Select One",
                                    options=[
                                        SelectOption(label= 'Loading Screen 1',value='load1'),
                                        SelectOption(label= 'Loading Screen 2',value='load2'),
                                        SelectOption(label= 'Loading Screen 3',value='load3'),
                                        SelectOption(label= 'Loading Screen 4',value='load4'),
                                        SelectOption(label= 'Loading Screen 5',value='load5'),
                                        SelectOption(label= 'Loading Screen 6',value='load6'),
                                        SelectOption(label= 'Loading Screen 7',value='load7'),
                                        SelectOption(label= 'Loading Screen 8',value='load8'),
                                        SelectOption(label= 'Loading Screen 9',value='load9'),
                                        SelectOption(label= 'Loading Screen 10',value='load10')
                                    ]

                                )],
                                [
                                Button(style=ButtonStyle.green,label=f'Replace 10'),
                                Button(style=ButtonStyle.red,label='Cancel Purchase')
                                ]
                            ]
                        tenthloading = loadingScreenDB.find_one({'number':int(screenlist[9])})
                        tenthloadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                        tenthloadingEm.set_image(url=tenthloading["gif"])
                        tenthloadingEm.set_thumbnail(url = member.avatar_url)
                        await event.respond(content='',embed=tenthloadingEm,components=newbuttons,type=7)
    
            except:
                if event.component.label == 'Close':
                    break

                elif event.component.label == 'Reset LS':
                    if userProf["money"] >= botStats["lsresetamount"]:
                        resetComps = [
                            
                            [
                                Button(style=ButtonStyle.green,label=f'Reset LS for ${botStats["lsresetamount"]}'),
                                Button(style=ButtonStyle.red,label='Cancel')
                            ]
                        ]
                    else:
                        resetComps = [
                            
                            [
                                Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                Button(style=ButtonStyle.red,label='Cancel')
                            ]
                        ]

                   
                    await event.respond(content='',components=resetComps,type=7)

                elif event.component.label == f'Reset LS for ${botStats["lsresetamount"]}':
                    def resetLoadingScreen():
                        shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":False}})
                        max = loadingScreenDB.count_documents({})
                        randomInt = random.randint(1,max) 
                        loadingScreen = loadingScreenDB.find_one({'number':randomInt})
                        shopDB.update_one({"id":member.id}, {"$addToSet":{"characterShop":{"number":loadingScreen["number"]}}})

                    if userProf["money"] >= botStats["lsresetamount"]:
                        shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"]-botStats['lsresetamount']}})
                        userShop = userProf["characterShop"]
                        for ls in userShop:
                            try:
                                shopDB.update_one({"id":member.id}, {"$pull":{"characterShop":{"number":ls["number"]}}})
                            except:
                                pass
                        resetLoadingScreen()


                        userProf = shopDB.find_one({"id":member.id})
                        boughtloading = userProf["boughtloading"]
                        usermoney = userProf["money"]
                        userShop = userProf['characterShop']
                    

                        charShoplist = []
                        for x in userShop:
                            try:
                                charShoplist.append(x["name"])
                            except:
                                charShoplist.append(x["number"])
                        
                        loadingScreen = loadingScreenDB.find_one({"number":charShoplist[5]})
                        
                        
                        rlsbuts = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Reset LS Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]

                    await event.respond(content='',embed=homeem,components=rlsbuts,type=7)
                    
                elif event.component.label == 'Buy':
                    if pageOn == 0:
                        await event.respond(content='',components=components,type=7)
                    elif pageOn == 1:
                        priceUn = botStat["uncommonbaseprice"]
                        if usermoney < priceUn:
                            newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                            
                        else:
                            if boughtun == False:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Buy: {uncommonChar["name"].capitalize()}'),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                            else:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                        await event.respond(content='',components=newbuttons,type=7)
                    elif pageOn == 2:
                        priceRare = botStat["rarebaseprice"]
                        if usermoney < priceRare:
                            newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        else:
                            if boughtrare == False:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Buy: {rareChar["name"].capitalize()}'),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                            else:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                        await event.respond(content='',components=newbuttons,type=7)
                    elif pageOn == 3:
                        priceEpic = botStat["epicbaseprice"]
                        if usermoney < priceEpic:
                            newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        else:
                            if boughtepic == False:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Buy: {epicChar["name"].capitalize()}'),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                            else:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                        await event.respond(content='',components=newbuttons,type=7)
                    elif pageOn == 4:
                        priceLeg = botStat["legendarybaseprice"]
                        if usermoney < priceLeg:
                            newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        else:
                            if boughtleg1 == False:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Buy: {legendaryChar1["name"].capitalize()}'),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                            else:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        await event.respond(content='',components=newbuttons,type=7)
                    elif pageOn == 5:
                        priceLeg = botStat["legendarybaseprice"]
                        if usermoney < priceLeg:
                            newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        else:
                            if boughtleg2 == False:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Buy: {legendaryChar2["name"].capitalize()}'),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]

                                ]
                            else:
                                newbuttons = [
                                    [
                                    Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                    Button(style=ButtonStyle.red,label='Cancel')
                                    ]
                                ]
                        await event.respond(content='',components=newbuttons,type=7)
                    elif pageOn == 6:
                        priceLoad = botStat['lsbaseprice']
                        try:
                            userData = userDB.find_one({'id':member.id})
                            loadingScreenBank = userData['loadingscreens']
                            screenlist = []
                            for screens in loadingScreenBank:
                                screenlist.append(int(screens['number']))
                        
                            if loadingScreen['number'] in screenlist:
                                newbuttons = [
                                        [
                                        Button(style=ButtonStyle.red,label=f'You Already Own This!',disabled=True),
                                        Button(style=ButtonStyle.red,label='Cancel')
                                        ]
                                    ]
                            else:
                                if usermoney < priceLoad:
                                    newbuttons = [
                                            [
                                            Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                            Button(style=ButtonStyle.red,label='Cancel')
                                            ]
                                        ]
                                else:
                                    if boughtloading == False:
                                        newbuttons = [
                                            [
                                            Button(style=ButtonStyle.green,label=f'Buy Loading Screen'),
                                            Button(style=ButtonStyle.red,label='Cancel')
                                            ]

                                        ]
                                    else:
                                        newbuttons = [
                                            [
                                            Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                            Button(style=ButtonStyle.red,label='Cancel')
                                            ]
                                        ]
                        except:
                            if usermoney < priceLoad:
                                    newbuttons = [
                                            [
                                            Button(style=ButtonStyle.red,label=f'Not Enough $',disabled=True),
                                            Button(style=ButtonStyle.red,label='Cancel')
                                            ]
                                        ]
                            else:
                                if boughtloading == False:
                                    newbuttons = [
                                        [
                                        Button(style=ButtonStyle.green,label=f'Buy Loading Screen'),
                                        Button(style=ButtonStyle.red,label='Cancel')
                                        ]

                                    ]
                                else:
                                    newbuttons = [
                                        [
                                        Button(style=ButtonStyle.red,label=f'Already Bought Today',disabled=True),
                                        Button(style=ButtonStyle.red,label='Cancel')
                                        ]
                                    ]

                        await event.respond(content='',components=newbuttons,type=7)
                     
                elif event.component.label == f'Buy: {uncommonChar["name"].capitalize()}':
                    priceUn = botStat["uncommonbaseprice"]
                    uncem = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought {uncommonChar['name'].capitalize()}!**",color = getColor('uncommon'))
                    uncem.set_image(url=uncommonChar["gif"])
                    uncem.set_thumbnail(url = member.avatar_url)


                    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":uncommonChar["name"],"show":uncommonChar["show"],"rarity":uncommonChar["rarity"]}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceUn}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtuncommon":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtun = userProf["boughtuncommon"]
                    usermoney = userProf["money"]
                    
                    await send_logs_shopbuy(member,guild,'uncommon',uncommonChar["name"])
                    await event.respond(content='',embed=uncem,components=newbuttons,type=7)

                elif event.component.label == f'Buy: {rareChar["name"].capitalize()}':
                    priceRare = botStat["rarebaseprice"]
                    rareEM = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought {rareChar['name'].capitalize()}!**",color = getColor('rare'))
                    rareEM.set_image(url=rareChar["gif"])
                    rareEM.set_thumbnail(url = member.avatar_url)


                    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":rareChar["name"],"show":rareChar["show"],"rarity":rareChar["rarity"]}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceRare}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtrare":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtrare = userProf["boughtrare"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'rare',rareChar["name"])
                    
                    await event.respond(content='',embed=rareEM,components=newbuttons,type=7)
                   
                elif event.component.label == f'Buy: {epicChar["name"].capitalize()}':
                    priceEpic = botStat["epicbaseprice"]
                    epicEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought {epicChar['name'].capitalize()}!**",color = getColor('epic'))
                    epicEm.set_image(url=epicChar["gif"])
                    epicEm.set_thumbnail(url = member.avatar_url)


                    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":epicChar["name"],"show":epicChar["show"],"rarity":epicChar["rarity"]}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceEpic}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtepic":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtepic = userProf["boughtepic"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'epic',epicChar["name"])
                    
                    await event.respond(content='',embed=epicEm,components=newbuttons,type=7)

                elif event.component.label == f'Buy: {legendaryChar1["name"].capitalize()}':
                    priceLeg = botStat["legendarybaseprice"]
                    legEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought {legendaryChar1['name'].capitalize()}!**",color = getColor('legendary'))
                    legEm.set_image(url=legendaryChar1["gif"])
                    legEm.set_thumbnail(url = member.avatar_url)


                    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":legendaryChar1["name"],"show":legendaryChar1["show"],"rarity":legendaryChar1["rarity"]}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLeg}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtlegendary1":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtleg1 = userProf["boughtlegendary1"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'legendary',legendaryChar1["name"])
                    
                    await event.respond(content='',embed=legEm,components=newbuttons,type=7)

                elif event.component.label == f'Buy: {legendaryChar2["name"].capitalize()}':
                    priceLeg = botStat["legendarybaseprice"]
                    legEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought {legendaryChar2['name'].capitalize()}!**",color = getColor('legendary'))
                    legEm.set_image(url=legendaryChar2["gif"])
                    legEm.set_thumbnail(url = member.avatar_url)


                    userDB.update_one({"id":member.id}, {"$addToSet":{"characters":{"name":legendaryChar2["name"],"show":legendaryChar2["show"],"rarity":legendaryChar2["rarity"]}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLeg}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtlegendary2":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close')
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtleg2 = userProf["boughtlegendary2"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'legendary',legendaryChar2["name"])
                    
                    await event.respond(content='',embed=legEm,components=newbuttons,type=7)
                elif event.component.label == f'Buy Loading Screen':
                    i=0
                    try:
                        for screens in screenlist:
                            i+=1
                    except:
                        pass
                    if i >= 10:
                        #Ask which one to replace
                        newbuttons = [
                            [
                                Select(placeholder=f"Select One",
                                options=[
                                    SelectOption(label= 'Loading Screen 1',value='load1'),
                                    SelectOption(label= 'Loading Screen 2',value='load2'),
                                    SelectOption(label= 'Loading Screen 3',value='load3'),
                                    SelectOption(label= 'Loading Screen 4',value='load4'),
                                    SelectOption(label= 'Loading Screen 5',value='load5'),
                                    SelectOption(label= 'Loading Screen 6',value='load6'),
                                    SelectOption(label= 'Loading Screen 7',value='load7'),
                                    SelectOption(label= 'Loading Screen 8',value='load8'),
                                    SelectOption(label= 'Loading Screen 9',value='load9'),
                                    SelectOption(label= 'Loading Screen 10',value='load10')
                                ]

                            )],
                            [
                            Button(style=ButtonStyle.green,label=f'Replace 1'),
                            Button(style=ButtonStyle.red,label='Cancel Purchase')
                            ]
                        ]

                        findFirstLoading = loadingScreenDB.find_one({'number':int(screenlist[0])})
                        findFirstLoadingEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**You can only have 10 loading screens! Please choose one to replace with the new one you are purchasing**",color = getColor('loadingscreen'))
                        findFirstLoadingEm.set_image(url=findFirstLoading["gif"])
                        findFirstLoadingEm.set_thumbnail(url = member.avatar_url)

                        await event.respond(content='',embed=findFirstLoadingEm,components=newbuttons,type=7)

                    
                    else:
                        priceLoad = botStat["lsbaseprice"]
                        loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                        loadEm.set_image(url=loadingScreen["gif"])
                        loadEm.set_thumbnail(url = member.avatar_url)

                        userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                        shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                        shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                        updateLegendaryandEpic(member)
                        updateCharsAmount(member)
                        newbuttons = [
                                        [
                                        Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                        Button(style=ButtonStyle.blue,label='Home'),
                                        Button(style=ButtonStyle.red,label='Close'),
                                        ]
                                    ]
                        
                        userProf = shopDB.find_one({"id":member.id})
                        boughtloading = userProf["boughtloading"]
                        usermoney = userProf["money"]
                        try:
                            currentLS = userProf['currentloadingscreen']
                        except:
                            try:
                                findLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                                userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":findLS['gif']}})
                                userDB.update_one({"id":member.id}, {"$set":{"lstype":'Select'}})
                                userProf = shopDB.find_one({'id':member.id})
                            except:
                                pass

                        await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    
                        await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 1':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[0])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[0])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 2':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[1])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[1])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 3':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[2])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[2])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 4':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[3])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[3])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 5':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[4])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[4])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 6':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[5])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[5])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Replace 7':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[6])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[6])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)
                
                elif event.component.label == f'Replace 8':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[7])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[7])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)
                
                elif event.component.label == f'Replace 9':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[8])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[8])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)
                
                elif event.component.label == f'Replace 10':
                    priceLoad = botStat["lsbaseprice"]
                    loadEm = discord.Embed(title = f"ACcharactershop - {member.name}",description=f"**{member.name} bought the Loading Screen!**\nIt has been added to your Loading Screen collection **(!acls)**",color = getColor('loadingscreen'))
                    loadEm.set_image(url=loadingScreen["gif"])
                    loadEm.set_thumbnail(url = member.avatar_url)

                    userProf = shopDB.find_one({"id":member.id})
                    findLS = loadingScreenDB.find_one({'number':int(screenlist[9])})
                    newLS = loadingScreenDB.find_one({'number':int(loadingScreen["number"])})
                    userUserDB = userDB.find_one({'id':member.id})
                    if userUserDB['currentloadingscreen'] == findLS['gif']:
                        userDB.update_one({"id":member.id}, {"$set":{"currentloadingscreen":newLS['gif']}})

                    userDB.update_one({"id":member.id}, {"$pull":{"loadingscreens":{"number":int(screenlist[9])}}})
                    userDB.update_one({"id":member.id}, {"$addToSet":{"loadingscreens":{"number":int(loadingScreen["number"])}}})
                    shopDB.update_one({"id":member.id}, {"$set":{"money":userProf["money"] - priceLoad}})
                    shopDB.update_one({"id":member.id}, {"$set":{"boughtloading":True}})

                    updateLegendaryandEpic(member)
                    updateCharsAmount(member)
                    newbuttons = [
                                    [
                                    Button(style=ButtonStyle.green,label=f'Purchase Successful!',disabled=True),
                                    Button(style=ButtonStyle.blue,label='Home'),
                                    Button(style=ButtonStyle.red,label='Close'),
                                    ]
                                ]
                    
                    userProf = shopDB.find_one({"id":member.id})
                    boughtloading = userProf["boughtloading"]
                    usermoney = userProf["money"]

                    await send_logs_shopbuy(member,guild,'loadingscreen',loadingScreen['description'])
                    await event.respond(content='',embed=loadEm,components=newbuttons,type=7)

                elif event.component.label == f'Cancel':
                    await event.respond(content='',components=components,type=7)
                
                elif event.component.label == f'Cancel Purchase':
                    await event.respond(content='',embed=loadingEm,components=components,type=7)

                elif event.component.label == f'Home':
                    userProf = shopDB.find_one({'id':member.id})
                    usermoney = userProf['money']

                    homeem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"Resets at **4:00 PM** PST Daily!\n**Time Until Next Reset: {23 - currenthour} hours {60-currentminute} minutes**\n**User Balance: ${usermoney}**", color = discord.Color.teal())
                    homeem.set_thumbnail(url = member.avatar_url)
                    homeem.set_image(url="https://media1.tenor.com/images/52950888781d0f27f61df71442f176cd/tenor.gif?itemid=5078001")
    
                    homecomponents = [

                        [
                            Select(placeholder=f"Rarity Selection - Balance: ${usermoney}",
                            options=[
                                SelectOption(label= 'Home',value='option1',emoji='🏠'),
                                SelectOption(label= 'Uncommon',value='option2',emoji='🟩'),
                                SelectOption(label= 'Rare',value='option3',emoji='🟦'),
                                SelectOption(label= 'Epic',value='option4',emoji='🟪'),
                                SelectOption(label= 'Legendary 1',value='option5',emoji='🟨'),
                                SelectOption(label= 'Legendary 2',value='option6',emoji='🟨'),
                                SelectOption(label= 'Loading Screen',value='option7',emoji='🖼️')
                            ]
                        
                        )],
                        
                        [
                            Button(style=ButtonStyle.green,label='Buy',disabled=True),
                            Button(style=ButtonStyle.blue,label='Buy SP'),
                            Button(style=ButtonStyle.blue,label='Reset LS'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]


                    await event.respond(content='',embed=homeem,components=homecomponents,type=7)
                
                elif event.component.label == f'Buy SP':
                    userSzn = sznDB.find_one({"id":member.id})
                    spem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"**How much SP do you want to buy?**\n$100 = 1 SP\n$1,000 = 10 SP\n$10,000 = 100 SP\n\nTotal Money: ${usermoney}\nTotal SP: {userSzn['xp']}", color = discord.Color.teal())
                    spem.set_thumbnail(url = member.avatar_url)
                    
                    spcomps = [
                        
                        [
                            Button(style=ButtonStyle.green,label='$100'),
                            Button(style=ButtonStyle.green,label='$1,000'),
                            Button(style=ButtonStyle.green,label='$10,000'),
                            Button(style=ButtonStyle.blue,label='Home'),
                            Button(style=ButtonStyle.red,label='Close')
                        ]
                    ]

                    await event.respond(content='',embed=spem,components=spcomps,type=7)
                
                elif event.component.label == f'$100':
                    if usermoney < 100:
                        spcomps = [
                        
                            [
                                Button(style=ButtonStyle.red,label='Not Enough $',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    else:
                        spcomps = [
                            
                            [
                                Button(style=ButtonStyle.green,label='Confirm $100'),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    
                    await event.respond(content='',components=spcomps,type=7)
                
                elif event.component.label == f'Confirm $100':

                    shopDB.update_one({"id":member.id}, {"$inc":{"money":-1*100}})
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":1}})

                    userp = shopDB.find_one({"id":member.id})
                    userSzn = sznDB.find_one({"id":member.id})
        
                    spem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"**How much SP do you want to buy?**\n$100 = 1 SP\n$1,000 = 10 SP\n$10,000 = 100 SP\n\nTotal Money: ${userp['money']}\nTotal SP: {userSzn['xp']}", color = discord.Color.teal())
                    spem.set_thumbnail(url = member.avatar_url)

                    spcomps = [
                            [
                                Button(style=ButtonStyle.green,label='Purchase Successful',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home'),
                                Button(style=ButtonStyle.red,label='Close')
                            ]
                        ]
                    
                    await event.respond(content='',embed=spem,components=spcomps,type=7)

                elif event.component.label == f'$1,000':
                    if usermoney < 1000:
                        spcomps = [
                        
                            [
                                Button(style=ButtonStyle.red,label='Not Enough $',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    else:
                        spcomps = [
                            
                            [
                                Button(style=ButtonStyle.green,label='Confirm $1,000'),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    
                    await event.respond(content='',components=spcomps,type=7)
                
                elif event.component.label == f'Confirm $1,000':

                    shopDB.update_one({"id":member.id}, {"$inc":{"money":-1*1000}})
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":10}})

                    userp = shopDB.find_one({"id":member.id})
                    userSzn = sznDB.find_one({"id":member.id})
        
                    spem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"**How much SP do you want to buy?**\n$100 = 1 SP\n$1,000 = 10 SP\n$10,000 = 100 SP\n\nTotal Money: ${userp['money']}\nTotal SP: {userSzn['xp']}", color = discord.Color.teal())
                    spem.set_thumbnail(url = member.avatar_url)

                    spcomps = [
                            [
                                Button(style=ButtonStyle.green,label='Purchase Successful',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home'),
                                Button(style=ButtonStyle.red,label='Close')
                            ]
                        ]
                    
                    await event.respond(content='',embed=spem,components=spcomps,type=7)

                elif event.component.label == f'$10,000':
                    if usermoney < 10000:
                        spcomps = [
                        
                            [
                                Button(style=ButtonStyle.red,label='Not Enough $',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    else:
                        spcomps = [
                            
                            [
                                Button(style=ButtonStyle.green,label='Confirm $10,000'),
                                Button(style=ButtonStyle.blue,label='Home')
                            ]
                        ]
                    
                    await event.respond(content='',components=spcomps,type=7)
                
                elif event.component.label == f'Confirm $10,000':

                    shopDB.update_one({"id":member.id}, {"$inc":{"money":-1*10000}})
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":100}})

                    userp = shopDB.find_one({"id":member.id})
                    userSzn = sznDB.find_one({"id":member.id})
        
                    spem = discord.Embed(title = f"ACraffle Character Shop - {member.name}",description = f"**How much SP do you want to buy?**\n$100 = 1 SP\n$1,000 = 10 SP\n$10,000 = 100 SP\n\nTotal Money: ${userp['money']}\nTotal SP: {userSzn['xp']}", color = discord.Color.teal())
                    spem.set_thumbnail(url = member.avatar_url)

                    spcomps = [
                            [
                                Button(style=ButtonStyle.green,label='Purchase Successful',disabled=True),
                                Button(style=ButtonStyle.blue,label='Home'),
                                Button(style=ButtonStyle.red,label='Close')
                            ]
                        ]
                    
                    await event.respond(content='',embed=spem,components=spcomps,type=7)

        except:
            break

    buttons = []
    await message.edit(components=buttons)
   

    charShoplist.clear()
    guild = ctx.message.guild
    try:
        await send_logs_shop(member,guild,"accharctershop")
    except:
        pass
    return




@client.command(aliases = ["acw"])
async def acwager(ctx,member:discord.Member=None,points = None):
    cmdUser = ctx.author
    if member == None:
        member=ctx.author
        em = discord.Embed(title = f"ACwager - {cmdUser.name}",description = f"**Wager your Season Points against another player!**\nSyntax: **!acw @user points**\nExample: !aw @user 10\nNote: Unlock this feature by getting **5 Hyper Legendaries**", color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if member == ctx.author:
        em = discord.Embed(title = f"ACwager - {cmdUser.name}",description = f"**Wager your Season Points against another player!**\nSyntax: **!acw @user points**\nExample: !aw @user 10\nNote: Unlock this feature by getting **5 Hyper Legendaries**", color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    
    if points == None:
        em = discord.Embed(title = f"ACwager - {cmdUser.name}",description = f"**Wager your Season Points against another player!**\nSyntax: **!acw @user points**\nExample: !aw @user 10\nNote: Unlock this feature by getting **5 Hyper Legendaries**", color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACwager - {cmdUser.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)

    points= int(points)

    #open both accounts
    cmdProf = sznDB.find_one({'id':cmdUser.id})
    memProf = sznDB.find_one({'id':member.id})

    #check to see if both users have enough points to wager
    if cmdProf['xp'] < points :
        em = discord.Embed(title = f"ACwager",description=f"{cmdUser.name} doesn't have enough Season Points to play this wager!",color = getColor('botColor'))
        em.set_thumbnail(url = cmdUser.avatar_url)
        await ctx.send(embed = em)
        return

    if memProf['xp'] < points:
        em = discord.Embed(title = f"ACwager",description=f"{member.name} doesn't have enough Season Points to play this wager!",color = getColor('botColor'))
        em.set_thumbnail(url = cmdUser.avatar_url)
        await ctx.send(embed = em)
        return

    #open userDBs
    cmdUserDB = userDB.find_one({'id':cmdUser.id})
    memUserDB = userDB.find_one({'id':member.id})

    #check hypers
    if cmdUserDB['hypersunlocked'] < 5:
        em = discord.Embed(title = f"ACwager",description=f"{cmdUser.name} doesn't have 5 Hyper Legendaries unlocked! They can play once they have met the requirement.",color = getColor('botColor'))
        em.set_thumbnail(url = cmdUser.avatar_url)
        await ctx.send(embed = em)
        return

    if memUserDB['hypersunlocked'] < 5:
        em = discord.Embed(title = f"ACwager",description=f"{member.name} doesn't have 5 Hyper Legendaries unlocked! They can play once they have met the requirement.",color = getColor('botColor'))
        em.set_thumbnail(url = cmdUser.avatar_url)
        await ctx.send(embed = em)
        return


    homeem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**Wager for {points} Season Points**\n\n{cmdUser.name}: {cmdProf['xp']} SP \n{member.name}: {memProf['xp']} SP", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)

    acComp = [
                [
                    Button(style=ButtonStyle.green,label='Accept'),
                    Button(style=ButtonStyle.red,label='Cancel')
                ]        
    ]

    cmdUserComp = [
                    [
                        Button(style=ButtonStyle.red,label= f'Red'),
                        Button(style=ButtonStyle.blue,label=f'Blue')
                    ]        
    ]

    

    var = 0

    message = await ctx.send(embed = homeem,components=acComp)
    
    
    def checkauthor(user):
        return lambda res: res.author == user and res.message == message

    
    while True:
        try:
            acahEvent = await client.wait_for('interaction',check = checkauthor(member),timeout=20.0)

            if acahEvent.component.label == 'Accept':
                newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**Wager Accepted!\n\n{cmdUser.name} please choose 🟥 or 🟦**", color = discord.Color.teal())
                newwem.set_thumbnail(url = member.avatar_url)

                await acahEvent.respond(content='',embed=newwem,components=cmdUserComp,type=7)
                break
        
        except:
            break
        break



    while True:
        try:
            acahEvent = await client.wait_for('interaction',check = checkauthor(cmdUser),timeout=20.0)

            if acahEvent.component.label == 'Red':
                var = 1
                newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose a color.\n\n{member.name} it's your turn!**\nChoose what you think {cmdUser.name} picked!", color = discord.Color.teal())
                newwem.set_thumbnail(url = cmdUser.avatar_url)

                await acahEvent.respond(content='',embed=newwem,components=cmdUserComp,type=7)
                break

            elif acahEvent.component.label == 'Blue':
                var = 2
                newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose a color.\n\n{member.name} it's your turn!**\nChoose what you think {cmdUser.name} picked!", color = discord.Color.teal())
                newwem.set_thumbnail(url = cmdUser.avatar_url)

                await acahEvent.respond(content='',embed=newwem,components=cmdUserComp,type=7)
                break
        
        except:
            break
        break


    while True:
        try:
            acahEvent = await client.wait_for('interaction',check = checkauthor(member),timeout=20.0)

            if acahEvent.component.label == 'Red':
                if var == 1:
                    newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose 🟥\n{member.name} chose 🟥\n\n{member.name} Wins {points} Season Point from {cmdUser.name}**!", color = discord.Color.teal())
                    newwem.set_thumbnail(url = member.avatar_url)

                    #add sp to db
                    sznDB.update_one({"id":cmdUser.id}, {"$inc":{"xp":-1*points}})
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":points}})


                if var == 2:
                    newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose 🟦\n{member.name} chose 🟥\n\n{cmdUser.name} Wins {points} Season Point from {member.name}**!", color = discord.Color.teal())
                    newwem.set_thumbnail(url = member.avatar_url)

                    #add sp to db
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":-1*points}})
                    sznDB.update_one({"id":cmdUser.id}, {"$inc":{"xp":points}})

                await acahEvent.respond(content='',embed=newwem,components=cmdUserComp,type=7)
                break

            if acahEvent.component.label == 'Blue':
                if var == 1:
                    newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose 🟥\n{member.name} chose 🟦\n\n{cmdUser.name} Wins {points} Season Point from {member.name}**!", color = discord.Color.teal())
                    newwem.set_thumbnail(url = member.avatar_url)

                    #add sp to db
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":-1*points}})
                    sznDB.update_one({"id":cmdUser.id}, {"$inc":{"xp":points}})

                if var == 2:
                    newwem = discord.Embed(title = f"ACwager - {cmdUser.name} vs {member.name}",description = f"**{cmdUser.name} chose 🟦\n{member.name} chose 🟦\n\n{member.name} Wins {points} Season Point from {cmdUser.name}**!", color = discord.Color.teal())
                    newwem.set_thumbnail(url = member.avatar_url)

                    #add sp to db
                    sznDB.update_one({"id":cmdUser.id}, {"$inc":{"xp":-1*points}})
                    sznDB.update_one({"id":member.id}, {"$inc":{"xp":points}})

                
                buts = []
                await acahEvent.respond(content='',embed=newwem,components=buts,type=7)
                break
        
        except:
            break
        break

    clr = []
    await message.edit(components=clr)
    return


    
@client.command(aliases = ["ACPREVIEW","ACpreview","acpre","ACPRE"])
async def acpreview(ctx, character = None,member:discord.Member=None):
    if member == None:
        member = ctx.author
    guild= ctx.message.guild
    if character is None:
        em = discord.Embed(title = f"ACpreview - {member.name}" ,description =f"**{cmdPrefix}acpreview  *character***",color = discord.Color.teal())
        await ctx.send(embed=em)
        return
    character=character.lower()
    characterFound = charDB.find_one({"name":character})
    if characterFound == None:
        em = discord.Embed(title = "ACpreview",description=f"Character, **{character.capitalize()}**, not found.\nFor a list of characters you can trade do **{ouptputprefix(ctx)}acbank**",color = discord.Color.teal())
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed=em)
        return
  
    hasChar = userDB.find_one({'id':member.id},{"characters":{"$elemMatch": {"name":character}}})
    owned = '❌'
    try:
        chList = hasChar['characters']
        owned = '✅'
    except:
        owned = '❌'


    usersWithChar = userDB.count_documents({"characters":{"$elemMatch": {"name":character}}})
 
    
    charname = characterFound["name"]
    show = showDB.find_one({"name":characterFound["show"]})
    rarity = characterFound["rarity"]
    gif = characterFound["gif"]
    if usersWithChar == 1:
        em = discord.Embed(title = f"ACpreview - {member.name}" ,description= f"**Name:** {charname.capitalize()} {owned}\n**Show:** {show['title']}\n**Rarity:** {rarity.capitalize()}\n**Stats**: {usersWithChar} person has {charname.capitalize()} unlocked",color = getColor(rarity))
        
    else:
        em = discord.Embed(title = f"ACpreview - {member.name}" ,description= f"**Name:** {charname.capitalize()} {owned}\n**Show:** {show['title']}\n**Rarity:** {rarity.capitalize()}\n**Stats**: {usersWithChar} people have {charname.capitalize()} unlocked",color = getColor(rarity))
       
    em.set_image(url=gif)
    await send_logs_preview(member,guild,character)
    await ctx.send(embed=em)
   

@client.command(aliases=['ACprestige','ACPRESTIGE','acPRESTIGE','acpres','ACPRES'])
async def acprestige(ctx, showInput=None):
    member = ctx.author 
    await createpres(member)
    if showInput is None:
        em = discord.Embed(title = f"ACprestige - {member.name}" ,description=f"Allows you to prestige a show in which you have unlocked all the characters! You trade in all the characters in the show as a flex, but also get increased Season Points and keep the Hyper Legendary forever.\nCheck out the Prestige Profile for a show using **!acpp *show***\nSyntax: **{ouptputprefix(ctx)}acprestige *show***",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        showInput = showInput.lower()

    try:
        showFound = showDB.find_one({'name':showInput})
    except:
        showFound = None

    if showFound == None:
        try:
            showFound = showDB.find_one({'abv':showInput})
        except:
            pass


    if showFound == None:
        em = discord.Embed(title = f"ACprestige - {member.name}" ,description=f"Show not found. To see a list of shows do **!acshows**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    showInput = showFound['name']

    try:
        presTier = 1
        presProf = presDB.find_one({'id':member.id})
        showlist = presProf['shows']
        for x in showlist:
            if x['show'] == showInput:
                presTier = x['tier']+1
    except:
        presTier = 1

    uprof = userDB.find_one({'id':member.id})
    userchars = uprof['characters']
    cntr = 0
    for char in userchars:
        if char['show'] == showInput:
            cntr+=1

    # hashyper = userDB.find_one({"id":member.id, "characters":{"$elemMatch": {"show":showInput,"rarity":'hyperlegendary'}}})
    charcnt = charDB.count_documents({"show":showInput})
    if charcnt != cntr:
        em = discord.Embed(title = f"ACprestige - {member.name}" ,description=f"{member.name} does not have all the characters unlocked for **{showFound['title']}**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        # print success message (include rewards for tier)
        em = discord.Embed(title = f"ACprestige - {member.name}" ,description=f"{member.name} successfully prestiged **{showFound['title']}**!\n**Prestige Tier: {presTier}**\n+{charcnt*10} SP",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        # pull all from user db for that show
        userDB.update_one({"id":member.id}, {"$pull":{"characters":{"show":showInput,"rarity":{'$ne':'hyperlegendary'}}}})
        
        
        # set prestige to 1 in presDB
        try:
            presDB.update_one({"id":member.id}, {"$pull":{"shows":{"show":showInput}}})
            presDB.update_one({"id":member.id}, {"$addToSet":{"shows":{'show':showInput,'tier':presTier}}})
        except:
            presDB.update_one({"id":member.id}, {"$addToSet":{"shows":{'show':showInput,'tier':presTier}}})


        presProf = presDB.find_one({'id':member.id})
        showlist = presProf['shows']
        totPres = 0
        for x in showlist:
            totPres += x['tier'] 
        presDB.update_one({"id":member.id}, {"$set":{"totPres":totPres}})
        getTime = datetime.datetime.utcnow()
        presDB.update_one({"id":member.id}, {"$addToSet":{"dates":{'date':f'{getTime.month}-{getTime.day}-{getTime.year}','show':showInput,'tier':presTier}}})
        sznDB.update_one({"id":member.id}, {"$inc":{"xp":charcnt*10}})
        await send_logs_pres(member,ctx.message.guild,showInput,presTier)
        return

@client.command(aliases=['ACprestigeprofile','ACPP','acpp'])
async def acprestigeprofile(ctx, showInput=None, member:discord.Member=None):
    if member == None:
        member = ctx.author 
    await createpres(member)
    if showInput is None:
        em = discord.Embed(title = f"ACprestigeprofile - {member.name}" ,description=f"Allows you to view a prestige profile for a show. Your prestige profile will show the date and tier in which you prestiged the show. It also shows the top user who has the highest tier of prestige for that show.\nSyntax: **{ouptputprefix(ctx)}acpp *show***",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return
    else:
        showInput = showInput.lower()

    try:
        showFound = showDB.find_one({'name':showInput})
    except:
        showFound = None

    if showFound == None:
        try:
            showFound = showDB.find_one({'abv':showInput})
        except:
            pass

    if showFound == None:
        em = discord.Embed(title = f"ACprestigeprofile - {member.name}" ,description=f"Show not found. To see a list of shows do **!acshows**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    showInput = showFound['name']
    dateList=[]
  
    
    presProf = presDB.find_one({'id':member.id})
    
    if presProf == None:
        em = discord.Embed(title = f"ACprestigeprofile - {member.name}" ,description=f"You have not prestiged a show yet! To prestige a show you must have the hyperlegendary unlocked and use **!acprestige**",color = discord.Color.teal())
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)
        return

    else:
        level = 0
        try:
            preslist = presProf['shows']
            for shws in preslist:
                if shws['show'] == showInput:
                    level = shws['tier']
            
            stars = ''
            for x in range(level):
                stars += '⭐'
        except:
            level = 0
            stars = ''
           
    
    dates = presProf['dates']
    for x in dates:
        if x['show'] == showInput:
            dateList.append(f"Tier {x['tier']}: {x['date']}")
        joinVar = '\n'
    
    if len(dateList) == 0:
        preslist = presDB.find({"shows":{"$elemMatch": {"show":showInput}}})
        maxtier = 0
        username = "None"
        for x in preslist:
            arr = x['shows']
            for y in arr:
                if y['show'] == showInput and y['tier'] > maxtier:
                    maxtier = y['tier']
                    username = x['name']
                    break

        embed = discord.Embed (
        title = f"**ACprestigeprofile - User: {member.name}\n{showFound['title']} - Prestige: {level}\n{stars}**\nTop Prestige: {username} ({maxtier})",
        colour = getColor('botColor')
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_image(url=showFound['thumbnail'])
        await ctx.send(embed=embed)
    else:
        preslist = presDB.find({"shows":{"$elemMatch": {"show":showInput}}})
        maxtier = 0
        username = "None"
        for x in preslist:
            arr = x['shows']
            for y in arr:
                if y['show'] == showInput and y['tier'] > maxtier:
                    maxtier = y['tier']
                    username = x['name']
                    break

        embed = discord.Embed (
        title = f"**ACprestigeprofile - User: {member.name}\n{showFound['title']} - Prestige: {level}\n{stars}**\nTop Prestige: {username} ({maxtier})",
        description = f'**{joinVar.join(dateList[i] for i in range(0,len(dateList)))}**',
        colour = getColor('botColor')
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_image(url=showFound['thumbnail'])
        await ctx.send(embed=embed)
    
    await send_logs_presprofile(member,ctx.message.guild,showInput)


@client.command(aliases = ['acbj'])
@commands.cooldown(1, 15, commands.BucketType.user)
async def acblackjack(ctx, bet=None):
    member=ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACblackjack - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    await createshopuser(member,ctx.message.guild)
    user = shopDB.find_one({"id":member.id})
    usermoney = user["money"]

    if bet == None:
        em = discord.Embed(title = f"ACblackjack - {member.name}\n",description = f"**Play Classic Blackjack (21)**\n\n**Total Money: ${usermoney}**\nSyntax: **!acbj amount**\nExample: **!acbj 500**\nMax Bet Per Play: $500",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    try:
        bet = int(bet)
    except:
        em = discord.Embed(title = f"ACblackjack - {member.name}\n",description = "Please enter a number!\n Example: **!acbj 100**",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if bet > 500:
        em = discord.Embed(title = f"ACblackjack - {member.name}\n",description = "Max Bet Per Play: $500\nUse a lower bet so you don't lose everything at once! (You're Welcome)",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    
    if bet <= 0:
        em = discord.Embed(title = f"ACblackjack - {member.name}\n",description = f"**Please use a bet greater than 0**\n\n**Total Money: ${usermoney}**\nSyntax: **!acbj amount**\nExample: **!acbj 500**\nMax Bet Per Play: $500",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if bet > usermoney:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = f"You only have **${usermoney}!**\nTry again with a lower amount.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    homeem = discord.Embed(title = f"ACblackjack  - {member.name}",description = f"**Bet: ${bet}**\n**Total Money: ${usermoney}**\nClick *Deal* to start!\nTry to get more than the dealer but don't go over 21!", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)
    

    coincomp = [
        [
            Button(style=ButtonStyle.blue,label='Deal'),
            Button(style=ButtonStyle.gray,label='Hit',disabled=True),
            Button(style=ButtonStyle.gray,label='Stand',disabled=True),
            Button(style=ButtonStyle.red,label='Cancel',disabled=False)
        ]        
    ]


    message = await ctx.send(components = coincomp,embed = homeem)

    
    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    

   
    cards = [2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8,8,8,8,9,9,9,9,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,11,11,11,11]

    while True:
        try:
            event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=15.0)

            if event.component.label == 'Deal':
                upCoin = [
                     [
                        Button(style=ButtonStyle.blue,label='Deal',disabled=True),
                        Button(style=ButtonStyle.green,label='Hit',disabled=False),
                        Button(style=ButtonStyle.red,label='Stand',disabled=False)
                    ]        
                ]
                dealem = discord.Embed(title = f"ACblackjack  - {member.name}", color = discord.Color.teal())
                
                dealem.set_thumbnail(url = member.avatar_url)


                d1 = random.choice(cards)
                cards.remove(d1)
                dealer = [d1,"?"]

                y1 = random.choice(cards)
                cards.remove(y1)
                y2 = random.choice(cards)
                if y1 == 11 and y2 == 11:
                    y2 = 1
                cards.remove(y2)
                you = [y1,y2]

                dealem.add_field(name=f"Dealer",value=f"{'[%s]' % ', '.join(map(str, dealer))}", inline=False)
                dealem.add_field(name=f"You",value=f"{you} ({sum(you)})", inline=False)

                if sum(you) == 21:
                    dealem.description('')
                    dealem.add_field(name=f"**You Won!**",value=f"**You won ${bet}**", inline=False)
                    dealem.set_image(url=random.choice(winGifs))

                    clearcomp = []
                    await message.edit(content='',components=clearcomp,embed=dealem,type=7)
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'win')
                    return
                    
                
                await event.respond(content='',components=upCoin,embed=dealem,type=7)

            elif event.component.label == 'Hit':
                newY = random.choice(cards)
                you.append(newY)

                if sum(you) > 21 and newY == 11:
                    you.pop()
                    you.append(1)

                dealem.clear_fields()

                dealem.add_field(name=f"Dealer",value=f"{'[%s]' % ', '.join(map(str, dealer))}", inline=False)
                dealem.add_field(name=f"You",value=f"{you} ({sum(you)})", inline=False)

                if sum(you) == 21:
                    #add money to account here
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':bet}})

                    user = shopDB.find_one({"id":member.id})
                    if user["money"] >= 100000:
                        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
                        user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    dealem.add_field(name=f"**✅ You Won! ✅**",value=f"**You won ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(winGifs))

                    

                    clearcomp = []
                    
                    await message.edit(content='',components=clearcomp,embed=dealem,type=7)
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'win')
                    
                    return

                if sum(you) > 21:
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':-1*bet}})

                    user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    dealem.add_field(name=f"**❌ Busted! ❌**",value=f"**You Lost ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(loseGifs))

                    

                    clearcomp = []
                    await message.edit(content='',components=clearcomp,embed=dealem,type=7)
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'lose')
                    return

                upCoin = [
                     [
                        Button(style=ButtonStyle.blue,label='Deal',disabled=True),
                        Button(style=ButtonStyle.green,label='Hit',disabled=False),
                        Button(style=ButtonStyle.red,label='Stand',disabled=False)
                    ]        
                ]

                

                await event.respond(content='',components=upCoin,embed=dealem,type=7)

            elif event.component.label == 'Stand':
                d2 = random.choice(cards)
                dealer.pop()
                dealer.append(d2)
                cards.remove(d2)

                dealem.clear_fields()
                dealem.add_field(name=f"Dealer",value=f"{dealer}", inline=False)
                dealem.add_field(name=f"You",value=f"{you} ({sum(you)})", inline=False)
                
                while(sum(dealer) <= 17):
                    newD = random.choice(cards)
                    dealer.append(newD)

                dealem.clear_fields()
                

                dealem.add_field(name=f"Dealer",value=f"{dealer} ({sum(dealer)})", inline=False)
                dealem.add_field(name=f"You",value=f"{you} ({sum(you)})", inline=False)

                if sum(dealer) > 21:
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':bet}})

                    user = shopDB.find_one({"id":member.id})
                    if user["money"] >= 100000:
                        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
                        user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    dealem.add_field(name=f"✅ Dealer Busts! You Win! ✅",value=f"**You win ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(winGifs))
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'win')

                
                if (sum(dealer) <= 21) and (sum(dealer) > sum(you)):
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':-1*bet}})

                    user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    dealem.add_field(name=f"❌ Dealer got {sum(dealer)}! You Lose! ❌",value=f"**You lost ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(loseGifs))
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'lose')
                
                if (sum(dealer) <= 21) and (sum(dealer) < sum(you)):
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':bet}})
                    
                    user = shopDB.find_one({"id":member.id})
                    if user["money"] >= 100000:
                        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
                        user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    dealem.add_field(name=f"✅Dealer got {sum(dealer)}! You Win! ✅",value=f"**You won ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(winGifs))
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'win')

                if (sum(dealer) == sum(you) and sum(dealer) <= 21):
                    dealem.add_field(name=f"🔄 Dealer got {sum(dealer)}! It's a Push! 🔄",value=f"**You keep your ${bet}**\nTotal Balance: ${usermoney}", inline=False)
                    dealem.set_image(url=random.choice(loseGifs))
                    await gamble_logs('blackjack',ctx.author,ctx.message.guild,bet,'push')


                clearComp = []
                await event.respond(content='',components=clearComp,embed=dealem,type=7)



            elif event.component.label == 'Cancel':
                clearComp = []
                await event.respond(content='',components=clearComp,type=7)
                return
                
        except:
            break

    clearcomp = []
    await message.edit(components=clearcomp)
    return

@client.command(aliases = ['accf', 'ACCF', 'ACcoinflip', 'ACCOINFLIP'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def accoinflip(ctx, bet=None):
    member=ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if bet == None:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = "Choose heads or tails and if you get it right your bet is doubled, if not you lose it!\nSyntax: **!accf amount**\nExample: **!accf 500**\nMax Bet Per Flip: $500",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    try:
        bet = int(bet)
    except:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = "Please enter a number!\n Example: **!accf 100**",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    if bet > 500:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = "Max Bet Per Flip: $500\nUse a lower bet so you don't lose everything at once! (You're Welcome)",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    await createshopuser(member,ctx.message.guild)

    user = shopDB.find_one({"id":member.id})
    usermoney = user["money"]

    if bet <= 0:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = f"**Please use a bet greater than 0**\n\n**Total Money: ${usermoney}**\nSyntax: **!acbj amount**\nExample: **!acbj 500**\nMax Bet Per Play: $500",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    

    if bet > usermoney:
        em = discord.Embed(title = f"ACcoinflip - {member.name}\n",description = f"You only have **${usermoney}!**\nTry again with a lower amount.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    homeem = discord.Embed(title = f"ACcoinflip  - {member.name}",description = f"**Please Select Heads or Tails!**\nBet: ${bet}\nTotal Money: ${usermoney}", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)

    coincomp = [
        [
            Button(style=ButtonStyle.gray,label='Heads'),
            Button(style=ButtonStyle.gray,label='Tails'),
            Button(style=ButtonStyle.blue,label='Flip',disabled=True)
        ]        
    ]


    message = await ctx.send(components=coincomp,embed = homeem)


    def checkauthor(user):
        return lambda res: res.author == user and res.message == message
    
    inp = 2
    while True:
        try:
            event = await client.wait_for("interaction",check = checkauthor(ctx.author),timeout=10.0)

            if event.component.label == 'Heads':
                upCoin = [
                    [
                        Button(style=ButtonStyle.green,label='Heads'),
                        Button(style=ButtonStyle.gray,label='Tails'),
                        Button(style=ButtonStyle.blue,label='Flip',disabled=False)
                    ]        
                ]
                inp = 1
                
                await event.respond(content='',components=upCoin,type=7)

            elif event.component.label == 'Tails':
                upCoin = [
                    [
                        Button(style=ButtonStyle.gray,label='Heads'),
                        Button(style=ButtonStyle.green,label='Tails'),
                        Button(style=ButtonStyle.blue,label='Flip',disabled=False)
                    ]        
                ]
                
                inp = 0

                await event.respond(content='',components=upCoin,type=7)

            elif event.component.label == 'Flip':
                rand = random.randint(0,1)
                
                if rand == inp:
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':bet}})

                    user = shopDB.find_one({"id":member.id})
                    if user["money"] >= 100000:
                        shopDB.update_one({"id":member.id}, {"$set":{"money":100000}})
                        user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    flipem = discord.Embed(title = f"ACcoinflip  - {member.name}",description = f"**✅ You Won ${bet}! ✅**\n**New Total Money: ${usermoney}**", color = discord.Color.teal())
                    flipem.set_thumbnail(url = member.avatar_url)
                    flipem.set_image(url=random.choice(winGifs))
                    await gamble_logs('CoinFlip',ctx.author,ctx.message.guild,bet,'win')

                    
                else:
                    shopDB.update_one({"id":member.id}, {"$inc":{'money':-1*bet}})
                    user = shopDB.find_one({"id":member.id})
                    usermoney = user["money"]

                    flipem = discord.Embed(title = f"ACcoinflip  - {member.name}",description = f"**❌ You Lost ${bet}! ❌**\n**New Total Money: ${usermoney}**", color = discord.Color.teal())
                    flipem.set_thumbnail(url = member.avatar_url)
                    flipem.set_image(url=random.choice(loseGifs))
                    await gamble_logs('CoinFlip',ctx.author,ctx.message.guild,bet,'lose')

                    
                resetComp = []
                    
                await event.respond(content='',components=resetComp,embed=flipem,type=7)
                return


        except:
            break

    clearcomp = []
    await message.edit(components=clearcomp)
    return

@client.command(aliases = ['acach'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def acachievements(ctx, member:discord.Member = None ):
    if member == None:
        member=ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    await createachuser(member)
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACachievements - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return

    
    em = discord.Embed(title = f"ACachievements - {member.name}\nLoading...",color = getColor("botColor"))
    em.set_thumbnail(url = member.avatar_url)
    message = await ctx.send(embed = em)

    acachComps = [
                [
                    Select(placeholder=f"Select Catergory",
                    options=[
                        SelectOption(label=f'Home',value='option1',emoji='🏠'),
                        SelectOption(label=f'Prestige Level',value='option2',emoji='⭐'),
                        SelectOption(label=f'Characters Unlocked',value='option3',emoji='💯'),
                        SelectOption(label=f'Hyper Legendaries ',value='option4',emoji='🌸'),
                        SelectOption(label=f'Trades',value='option5',emoji='🔄'),
                        SelectOption(label=f'Votes',value='option6',emoji='✅'),
                        SelectOption(label=f'Special',value='option7',emoji='❓')
                    ]
                )]
            ]

    #achProf = userDB.find_one({id:member.id})

    homeem = discord.Embed(title = f"ACachievements - {member.name}",description = f"This is a profile that will display different achievements you can unlock by using ACraffle.", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)
    user = userDB.find_one({'id':member.id})
    try:
        if user['lstype'] == "Select":
            loadingscreen = user['currentloadingscreen']
            homeem.set_image(url = loadingscreen)
        elif user['lstype'] == "Random":
            screenList = []
            screens = user['loadingscreens']
            it = 0
            for var in screens:
                it+=1
                screenList.append(int(var['number']))
            it = it-1
            randScreen = random.randint(0,it)
            screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
            homeem.set_image(url = screenFound['gif'])
    except:
        pass
    

    await message.edit(embed = homeem,components=acachComps)
        
    def checkauthor(user):
        return lambda res: res.author == user and res.message == message

    while True:
        try:
            acahEvent = await client.wait_for('interaction',check = checkauthor(ctx.author),timeout=15.0)

            if acahEvent.values[0] == 'option1':
                await acahEvent.respond(content='',embed=homeem,type=7)
                
            elif acahEvent.values[0] == 'option2':
                acahPres = presDB.find_one({'id':member.id})
                amntPres = acahPres['totPres']
                presEm = discord.Embed(title = f"ACachievements - {member.name}\nPresige Level: {amntPres}",description = f"*!acpreshelp* for prestige details.", color = discord.Color.teal())
                presEm.set_thumbnail(url = member.avatar_url)
                presList = [1,3,5,10,15,25,50,75,100]
                
                for itm in presList:
                    if amntPres >= itm:
                        presEm.add_field(name=f"✅",value=f"{itm}", inline=True)
                    else:
                        presEm.add_field(name=f"❌",value=f"{itm}", inline=True)

                await acahEvent.respond(content='',embed=presEm,type=7)


            elif acahEvent.values[0] == 'option3':
                userProf = userDB.find_one({'id':member.id})
                chUnl = userProf['charsunlocked']
                charEm = discord.Embed(title = f"ACachievements - {member.name}\nTotal Characters Unlocked: {chUnl}",description = f"*!acprofile* for more stats", color = discord.Color.teal())
                charEm.set_thumbnail(url = member.avatar_url)
                charsList = [10,50,100,250,500,650,800,900,1000]
                
                for itm in charsList:
                    if chUnl >= itm:
                        charEm.add_field(name=f"✅",value=f"{itm}", inline=True)
                    else:
                        charEm.add_field(name=f"❌",value=f"{itm}", inline=True)

                await acahEvent.respond(content='',embed=charEm,type=7)


            elif acahEvent.values[0] == 'option4':
                userProf = userDB.find_one({'id':member.id})
                hlUnl = userProf['hypersunlocked']
                hlEm = discord.Embed(title = f"ACachievements - {member.name}\nTotal Hyper Legendaries: {hlUnl}",description = f"*!acprofile* for more stats", color = discord.Color.teal())
                hlEm.set_thumbnail(url = member.avatar_url)
                hlList = [1,3,5,10,20,30,40,50,75]
                
                for itm in hlList:
                    if hlUnl >= itm:
                        hlEm.add_field(name=f"✅",value=f"{itm}", inline=True)
                    else:
                        hlEm.add_field(name=f"❌",value=f"{itm}", inline=True)

                await acahEvent.respond(content='',embed=hlEm,type=7)

            

            elif acahEvent.values[0] == 'option5':
                achUser = achDB.find_one({"id":member.id})
                amntTrades = achUser['trades']
                tradeem = discord.Embed(title = f"ACachievements - {member.name}\nTotal Trades: {amntTrades}",description = f"Don't try to spam trades!\nThere's a cooldown!", color = discord.Color.teal())
                tradeem.set_thumbnail(url = member.avatar_url)
                tradeList = [10,25,50,100,200,300,400,500,1000]
                
                for itm in tradeList:
                    if amntTrades >= itm:
                        tradeem.add_field(name=f"✅",value=f"{itm}", inline=True)
                    else:
                        tradeem.add_field(name=f"❌",value=f"{itm}", inline=True)

                await acahEvent.respond(content='',embed=tradeem,type=7)


            elif acahEvent.values[0] == 'option6':
                achUser = achDB.find_one({"id":member.id})
                amntVotes = achUser['votes']
                voteem = discord.Embed(title = f"ACachievements - {member.name}\nTotal Votes: {amntVotes}",description = f"Thanks for voting!", color = discord.Color.teal())
                voteem.set_thumbnail(url = member.avatar_url)
                votelist = [5,10,15,25,35,50,75,100,150]
                
                for itm in votelist:
                    if amntVotes >= itm:
                        voteem.add_field(name=f"✅",value=f"{itm}", inline=True)
                    else:
                        voteem.add_field(name=f"❌",value=f"{itm}", inline=True)

                await acahEvent.respond(content='',embed=voteem,type=7)

            elif acahEvent.values[0] == 'option7':
                miscList = [
                    "Set your character as Lard's favorite character",
                    "Lard likes your acprofile (char, color, bio, etc.)",
                    "Prestige a show more than 10 times",
                    "A Loading Screen you suggested gets added ⭐",
                    "Leave a 5-Star Review on the Top.GG ACraffle page ⭐",
                    "Top 5 in a League Season ⭐"
                ]
           

                achUser = achDB.find_one({"id":member.id})
                presUser = presDB.find_one({"id":member.id})

                miscEm = discord.Embed(title = f"ACachievements - {member.name}",description = f"Special Achievements\nIf the achievement has a ⭐ you have to show proof in the ACraffle discord", color = discord.Color.teal())
                miscEm.set_thumbnail(url = member.avatar_url)

                complete = False
                for itm in miscList:
                    if itm == miscList[0]:
                        try:
                            setEren = achUser['setEren']
                            complete = True
                        except:
                            complete = False

                    if itm == miscList[1]:
                        try:
                            hasFlex = achUser['lardapp']
                            complete = True
                        except:
                            complete = False

                    #needs to be finished
                    if itm == miscList[2]:
                        complete = False
                        try:
                            for x in presUser['shows']:
                                if x['tier'] >= 10:
                                    complete = True
                                    break
                                else:
                                    complete = False
                        except:
                            complete = False
                        

                    #needs to be finished
                    if itm == miscList[3]:
                        try:
                            lsAdd = achUser['lsadded']
                            complete = True
                        except:
                            complete = False

                    if itm == miscList[4]:
                        try:
                            lsAdd = achUser['reviewL']
                            complete = True
                        except:
                            complete = False

                    if itm == miscList[5]:
                        try:
                            rnk1 = achUser['rank1']
                            complete = True
                        except:
                            complete = False
                        
                
                    if complete == True:
                        miscEm.add_field(name=f"✅",value=f"{itm}", inline=False)
                    else:
                        miscEm.add_field(name=f"❌",value=f"{itm}", inline=False)

                await acahEvent.respond(content='',embed=miscEm,type=7)
            
        except:
            break

    await send_logs(ctx.author,ctx.message.guild,'acachievements')
    blankButs = []
    await message.edit(components=blankButs)
    return



@client.command()
async def newshowacan(ctx,showname = None):
    if showname == None:
        await ctx.send("newshowacan showname")
        return

    botstat = botstatsDB.find_one({"id":573})
    show2 = botstat["newshow1"]
    show3 = botstat["newshow2"]
    show4 = botstat["newshow3"]
    show5 = botstat["newshow4"]

    botstatsDB.update_one({"id":573}, {"$set":{"newshow1":showname}})
    botstatsDB.update_one({"id":573}, {"$set":{"newshow2":show2}})
    botstatsDB.update_one({"id":573}, {"$set":{"newshow3":show3}})
    botstatsDB.update_one({"id":573}, {"$set":{"newshow4":show4}})
    botstatsDB.update_one({"id":573}, {"$set":{"newshow5":show5}})
    await ctx.send("Done")
    
@client.command()
async def updatenewshow(ctx,numshow=None,showname = None):
    numshow = int(numshow)
    if numshow == 1:
        botstatsDB.update_one({"id":573}, {"$set":{"newshow1":showname}})
        await ctx.send("Done")
        return
    elif numshow == 2:
        botstatsDB.update_one({"id":573}, {"$set":{"newshow2":showname}})
        await ctx.send("Done")
        return
    elif numshow == 3:
        botstatsDB.update_one({"id":573}, {"$set":{"newshow3":showname}})
        await ctx.send("Done")
        return
    elif numshow == 4:
        botstatsDB.update_one({"id":573}, {"$set":{"newshow4":showname}})
        await ctx.send("Done")
        return
    elif numshow == 5:
        botstatsDB.update_one({"id":573}, {"$set":{"newshow5":showname}})
        await ctx.send("Done")
        return
    else:
        print(numshow)
        await ctx.send("updatenewshow number showname  or  num not found (1-5)")
        return

@client.command()
async def resetLeague(ctx,cf = None):
    if ctx.message.author.id == 401939531970117643:
        if cf == 'confirm':
            todayDisplay = datetime.datetime.utcnow()
            botstatsDB.update_one({"id":573}, {"$inc":{"season":1}})
            botstatsDB.update_one({"id":573}, {"$set":{"seasonmonth":todayDisplay.month}})
            totalSzn = sznDB.count_documents({})
            botStats = botstatsDB.find_one({"id":573})

            peepslist = sznDB.find().sort("xp", -1)
            
            i=1
            for peeps in peepslist:
                try:
                    sznWinDB.update_one({"id":peeps['id']}, {"$addToSet":{"prevSeasons":{"season":botStats['season'],"rank":i}}})
                    sznPer = math.ceil(100 * (i / totalSzn))
                    if sznPer >= 40 and sznPer < 50:
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":500}})
                    elif sznPer >= 30 and sznPer < 40:
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":1000}})
                    elif sznPer >= 20 and sznPer < 30:
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":2500}})
                    elif sznPer >= 10 and sznPer < 20: #Top 10
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":5000}})
                    elif sznPer >= 5 and sznPer < 10: #Top 10
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":10000}})
                    elif sznPer <= 1:
                        shopDB.update_one({"id":peeps['id']}, {"$inc":{"money":15000}})
                    i+=1
                    
                except:

                    pass
                    
                
            sznDB.delete_many({})
            await ctx.send('Done resetting season')
        else:
            await ctx.send('*resetLeague confirm* to confirm the reset')


@client.command(aliases = ["acl"])
@commands.cooldown(1, 2, commands.BucketType.user)
async def acleague(ctx,member:discord.Member=None):
    if member == None:
        member = ctx.author
    guild = ctx.message.guild
    botStats = botstatsDB.find_one({"id":573})
    if botStats['botOffline']==True or botOnline==False:
        em = discord.Embed(title = f"ACleague - {member.name}\nThe bot is rebooting...\nTry again in a few minutes.",color = getColor('botColor'))
        em.set_thumbnail(url = member.avatar_url)
        await ctx.send(embed = em)
        return
    await createuser(member, guild)
    await createshopuser(member,guild)
    await createsznuser(member)
    await createsznWinuser(member)

    acachComps = [
                [
                    Select(placeholder=f"Select Catergory",
                    options=[
                        SelectOption(label=f'Home',value='option1',emoji='🏠'),
                        SelectOption(label=f'Leagues',value='option2',emoji='📈'),
                        SelectOption(label=f'Top 10',value='option3',emoji='👑'),
                        SelectOption(label=f'Your Leaderboard',value='option4',emoji='🔥'),
                        SelectOption(label=f'Previous Seasons',value='option5',emoji='🕜')
                    ]
                )]
            ]

    sznUser = sznDB.find_one({'id':member.id})

    sznRank = sznDB.count_documents({"xp": { "$gt" : sznUser['xp']}}) + 1

    todayDisplay = datetime.datetime.utcnow()
    datetime_object = datetime.datetime.strptime(str(todayDisplay.month), "%m")
    month_name = datetime_object.strftime("%b")

    nmonth = todayDisplay.month + 1
    d0 = date(todayDisplay.year, todayDisplay.month, todayDisplay.day)
    if todayDisplay.month != '12':
        d1 = date(todayDisplay.year, nmonth, 1)
    else:
        d1 = date(todayDisplay.year+1, nmonth, 1)

    delta = d1 - d0



    totSzn = sznDB.count_documents({})
    homeem = discord.Embed(title = f"ACleague - {member.name}",description = f"**Season {botStats['season']} - {month_name} {todayDisplay.year}**\n(Ends in {delta.days} days)\n\n**Rank: {sznRank}/{totSzn}\nSeason Points: {sznUser['xp']}**", color = discord.Color.teal())
    homeem.set_thumbnail(url = member.avatar_url)
    homeem.set_footer(text='Earn Season Points though raffles and prestiging shows!')

    user = userDB.find_one({'id':member.id})
    try:
        if user['lstype'] == "Select":
            loadingscreen = user['currentloadingscreen']
            homeem.set_image(url = loadingscreen)
        elif user['lstype'] == "Random":
            screenList = []
            screens = user['loadingscreens']
            it = 0
            for var in screens:
                it+=1
                screenList.append(int(var['number']))
            it = it-1
            randScreen = random.randint(0,it)
            screenFound = loadingScreenDB.find_one({'number':screenList[randScreen]})
            homeem.set_image(url = screenFound['gif'])
    except:
        pass

    message = await ctx.send(embed = homeem,components=acachComps)
        
    def checkauthor(user):
        return lambda res: res.author == user and res.message == message

    lbem = discord.Embed(title = f"ACleague - {member.name}",description = f"**Season {botStats['season']} - {month_name} {todayDisplay.year}**", color = discord.Color.teal())
    lbem.set_thumbnail(url = member.avatar_url)
    lbem.set_footer(text='Earn Season Points though raffles and prestiging shows!')
    
    rankings = sznDB.find().limit(10).sort("xp", -1)
    i=1
    
    for x in rankings:
        lbem.add_field(name=f"{i}. {x['name']}",value=f"Season Points: {x['xp']}",inline=False)
        i+=1


    ylbem = discord.Embed(title = f"ACleague - {member.name}",description = f"**Season {botStats['season']} - {month_name} {todayDisplay.year}**", color = discord.Color.teal())
    ylbem.set_thumbnail(url = member.avatar_url)
    ylbem.set_footer(text='Earn Season Points though raffles and prestiging shows!')
    
    rankYou = sznDB.find_one({'id':member.id})
    ranks2 = sznDB.find({'id':{'$not':{'$eq':member.id}},"xp":{"$lte": sznUser["xp"]}}).limit(4).sort("xp", -1)

    j=0
    ylbem.add_field(name=f"{sznRank+j}. {rankYou['name']}",value=f"Season Points: {rankYou['xp']}",inline=False)
    for y in ranks2:
        j+=1
        ylbem.add_field(name=f"{sznRank+j}. {y['name']}",value=f"Season Points: {y['xp']}",inline=False)


    sznPer = math.ceil(100 * (sznRank / totSzn))
    
    if sznPer <= 10:
        rounded = round(sznPer/5)*5
    else:
        sznPer = sznPer - (sznPer % 10)
        rounded = round(sznPer/10)*10
        
    tierem = discord.Embed(title = f"ACleague - {member.name}",description = f"**Season {botStats['season']} - {month_name} {todayDisplay.year}**", color = discord.Color.teal())
    tierem.set_thumbnail(url = member.avatar_url)
    tierem.set_footer(text='Earn Season Points though raffles and prestiging shows!')
    tierem.add_field(name=f'**League Season**', value=f'Rank: {sznRank}/{totSzn}\nLeague: {getSznTier(sznPer)} Top {rounded}%', inline=False)
    tierem.add_field(name=f'**All Leagues**\nMoney for finishing in each League.', value='Top 90% - ⬜️\nTop 80% - ⬛️\nTop 70% - 🟫\nTop 60% - 🟧\nTop 50% - 🟥\nTop 40% - 🟩 ($500)\nTop 30% - 🟦 ($1,000)\nTop 20% - 🟪 ($2,500)\nTop 10% - 🟨 ($5,000)\nTop 5% - ⭐️ ($10,000)\nTop 1% - 👑 ($15,000)', inline=False)

    while True:
        try:
            acahEvent = await client.wait_for('interaction',check = checkauthor(ctx.author),timeout=15.0)

            if acahEvent.values[0] == 'option1':
                await acahEvent.respond(content='',embed=homeem,type=7)
            
            if acahEvent.values[0] == 'option2':
                await acahEvent.respond(content='',embed=tierem,type=7)
                
            elif acahEvent.values[0] == 'option3':
                await acahEvent.respond(content='',embed=lbem,type=7)

            elif acahEvent.values[0] == 'option4':
                await acahEvent.respond(content='',embed=ylbem,type=7)
            
            elif acahEvent.values[0] == 'option5':
                newem = discord.Embed(title = f"ACleague - {member.name}",description = f"**Season {botStats['season']} - {month_name} {todayDisplay.year}**", color = discord.Color.teal())
                newem.set_thumbnail(url = member.avatar_url)
                newem.set_footer(text='Earn Season Points though raffles and prestiging shows!')

                try:
                    prevSzn = sznWinDB.find_one({'id':member.id})
                    sznlist = prevSzn['prevSeasons']

                    for sz in sznlist:
                        newem.add_field(name=f"Season {sz['season']}",value=f"Rank: {sz['rank']}",inline=True)
                except:
                    pass


                await acahEvent.respond(content='',embed=newem,type=7)

                
        except:
            break

    blankButs = []
    await message.edit(components=blankButs)
    await send_logs(member,ctx.message.guild,"acleague")
    return

@client.command(aliases = ["acan","ACannouncements","ACANNOUNCEMENTS"])
async def acannouncements(ctx):
        member = ctx.author
        guild=ctx.message.guild
        botstat = botstatsDB.find_one({"id":573})
        show1 = botstat["newshow1"]
        show2 = botstat["newshow2"]
        show3 = botstat["newshow3"]
        show4 = botstat["newshow4"]
        show5 = botstat["newshow5"]

        em = discord.Embed(title = f"ACraffle Announcements - Version {versionNumber}\nFor help and other commands use ***!achelp***\nNew? Use ***!actutorial***",color = discord.Color.teal())
        em.add_field(name= f'**Newest Shows**',value=f"{show1}\n{show2}\n{show3}\n{show4}\n{show5}",inline=False)
        em.add_field(name= f'**Gambling**',value=f"Win (probably lose) money!\n- **!acblackjack (!acbj)**\n- **!accoinflip (!accf)**",inline=False)
        em.add_field(name= f'**League Seasons**',value=f"See where you rank in the current season (Seasons are 1 month long)\nWager your points against another user!\n- **!acleague (!acl)**\n- **!acwager (!acw)**",inline=False)
        em.add_field(name= f'**Achievements**',value=f"See a list of unlockable achievements!\n- **!acachievements (!acach)**",inline=False)
        await ctx.send(embed=em)
        await send_logs(member,guild,"acannouncements")
        return


@client.command(aliases = ["acv","ACV","ACVOTE",'Acvote'])
async def acvote(ctx):
    member = ctx.author
    guild=ctx.message.guild
    em = discord.Embed(title = f"ACvote - {member.name}",description = f"Click the link below to vote for ACraffle!\nVoting gives you **One Vote Credit** which is the equivalent to an **!acrp**.\nYou can access your vote credits by doing **!acrv**",color = discord.Color.teal())
    em.add_field(name="\u200B",value='[[Vote Link]](https://top.gg/bot/864733251166797835/vote)',inline=False)
    em.set_thumbnail(url = member.avatar_url)
    em.set_image(url='https://pa1.narvii.com/6809/ab0f90cc948019786f61395656e31cdc924e8394_hq.gif')
    await send_logs(member,guild,"acvote")
    await ctx.send(embed = em)

@client.command(aliases = ['ach','ACHELP','ACH','AChelp'])
async def achelp(ctx):
    cmdPrefix = "!"
    member = ctx.author
    guild=ctx.message.guild
    em = discord.Embed(title = f"AChelp - {member.name}",description = f"To get started look at **!actutorial (!actut)**\nFor recent changes use **{cmdPrefix}acan**\nTo see all included shows do **!acshows**",color = discord.Color.teal())
    em.add_field(name = f"**Unlocking\nCharacters**", value = f"{cmdPrefix}acraffle\n{cmdPrefix}acraffleplus\n{cmdPrefix}acrafflevote\n{cmdPrefix}actrade\n{cmdPrefix}acupgrade\n{cmdPrefix}achyperlegendary\n{cmdPrefix}acblock\n{cmdPrefix}acloadingscreen (!acls)")#add acupgrade back here when updated
    em.add_field(name="**Viewing\nCharacters**", value =f"\n{cmdPrefix}acbank\n{cmdPrefix}acbankshow\n{cmdPrefix}acbankrarity\n{cmdPrefix}acpreview")
    em.add_field(name='**Profile**',value =f"{cmdPrefix}acprofile\n{cmdPrefix}acprofilecolor\n{cmdPrefix}acsetcharacter\n{cmdPrefix}acsetfavorite\n{cmdPrefix}acsetmal\n{cmdPrefix}acsetanilist\n{cmdPrefix}acsetbio\n{cmdPrefix}acpremove")#\n{cmdPrefix}acleaderboard")
    em.add_field(name='**Economy**',value =f"{cmdPrefix}accharactershop (!accs)\n{cmdPrefix}acresetshop\n{cmdPrefix}acblackjack (!acbj)\n{cmdPrefix}accoinflip (!accf)",inline=True)
    em.add_field(name='**Achievements and\nPrestige**',value =f"{cmdPrefix}acachievements (!acach)\n{cmdPrefix}acprestige\n{cmdPrefix}acprestigeprofile (!acpp)",inline=True)
    em.add_field(name='**League**',value =f"{cmdPrefix}acleague\n{cmdPrefix}acwager",inline=True)
    em.add_field(name="\u200B",value='[[ACraffle Discord Server]](https://discord.gg/DjSCcaUpTg)   [[Bot Invite]](https://discord.com/api/oauth2/authorize?client_id=864733251166797835&permissions=286784&scope=bot)',inline=False)
    await ctx.send(embed = em)
    await send_logs(member,guild,"achelp")
    return

# @client.command(aliases = ["acprestigehelp"])
# async def acpreshelp(ctx):
#     member = ctx.author
#     guild=ctx.message.guild
#     em = discord.Embed(title = f"ACpreshelp - {member.name}",color = discord.Color.teal())
#     em.add_field(name = f"**How to Prestige a show:**", value = f"If you have all the characters unlocked for a certain show you can do **!acpres *show***. **WARNING**: You lose all the characters in that show except the hyper legendary. If you want to recollect or are tired of getting duplicates.",inline=False)
#     em.add_field(name = f"**What Happens Next:**", value = f"After you prestige you will unlock the prestige rank on the acprofile. This rank is based on the total number of prestiges you have across all shows. You will also get a new bank color for that show, changing with each prestige tier.",inline=False)
#     em.add_field(name = f"**ACprestigeprofile**", value = f"The ACprestigeprofile (!acpp) allows you to see the date and level of your prestige. Another competitve feature is that !acpp will show the highest prestiged user for**everyone**. For example if you have Demon Slayer at Prestige 3 and no one else does, whenever anyone does !acpp demonslayer, you will appear.",inline=False)
#     em.add_field(name = f"**Prestige Bonus**", value = f"Prestige Bonus replaces duplicate money. When you roll a character from a prestiged show you will get ($125 * prestige level). For example if you roll a Demon Slayer character and your demon slayer is prestige 2 you will get ($125 * 2) = $250 even if it's a common.",inline=False)
#     await ctx.send(embed = em)
#     await send_logs(member,guild,"acpreshelp")
#     return


@client.command(aliases = ['actut','Actutorial','ACTUTORIAL','Actut','ACTUT'])
async def actutorial(ctx):
    member = ctx.author
    guild = ctx.message.guild
    await ctx.send('https://www.youtube.com/watch?v=hTzOGHAkqMg')
    await send_logs(member,guild,"actutorial")
    

@client.event
async def on_message(msg):
    if msg.channel.id == 892219168156430336:
        
        data = msg.content.split(" ")

        user = re.sub("\D", "", data[0])
        member = client.get_user(int(user))
        await createvoter(member)

        voteDB.update_one({"id":member.id}, {"$inc":{"credits":1}})
        achDB.update_one({"id":member.id}, {"$inc":{"votes":1}})

    await client.process_commands(msg)


logChannelID = 865757247933251584
banklogChannelID = 873120153498423366
cooldownChannelID = 876653890605563904
previewChannelID = 876654247423385630
newUserChannelID = 876658814269661185
shopChannelID = 879180765726912593
profileChannelID = 881954966103801856
loadingCannelID = 884247812936699905
presChannelID = 919091316401528834
wagerChannelID = 949486966930559066

async def send_logs(member, server, msg):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}**')
    except:
        pass
    return

async def wager_logs(member, server, mem, amount):
    channel = client.get_channel(wagerChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Wager against: **{mem}** - {amount} points')
    except:
        pass
    return

async def gamble_logs(game, member, server, amount,win):
    channel = client.get_channel(wagerChannelID)
    try:
        await channel.send(f'{game} - User: **{member.name}** - Server: **{server.name}** - ${amount} - {win}')
    except:
        pass
    return

async def send_logs_loading(member, server, message,character):
    channel = client.get_channel(loadingCannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Action: **{message}** - Number: **{character}**')
    except:
        pass
    return

async def send_logs_shop(member, server, msg):
    channel = client.get_channel(shopChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}**')
    except:
        pass
    return

async def send_logs_shopbuy(member, server, rarity,character):
    channel = client.get_channel(shopChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **acbuy** - Rarity: **{rarity}** - Character: **{character}**')
    except:
        pass
    return

async def send_logs_pres(member, server, show, tier):
    channel = client.get_channel(presChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **prestige** - Show: **{show}** - Tier: **{tier}**')
    except:
        pass
    return

async def send_logs_presprofile(member, server, show):
    channel = client.get_channel(presChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **prestige profile** - Show: **{show}**')
    except:
        pass
    return

async def send_logs_newuser(member, server):
    channel = client.get_channel(newUserChannelID)
    try:
        await channel.send(f'**New User!** - User: **{member.name}** - Server: **{server.name}**')
    except:
        pass
    return

async def send_logs_preview(member, server, character):
    channel = client.get_channel(previewChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **Preview** - Character: **{character}**')
    except:
        pass
    return

async def send_logs_profile(commandUser, member, server, msg):
    channel = client.get_channel(profileChannelID)
    try:
        await channel.send(f'User: **{commandUser.name}** - Profile: **{member.name}** - Server: **{server.name}** - Command: **{msg}**')
    except:
        pass
    return

async def send_logs_profile_change(member, server, msg, character):
    channel = client.get_channel(profileChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Character: **{character}**')
    except:
        pass
    return

async def send_logs_profile_color(member, server, msg,color):
    channel = client.get_channel(profileChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Color: **{color}**')
    except:
        pass
    return

async def send_logs_profile_base(member, server, msg):
    channel = client.get_channel(profileChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}**')
    except:
        pass
    return

async def send_logs_search(commandUser, server, character):
    channel = client.get_channel(previewChannelID)
    try:
        await channel.send(f'User: **{commandUser.name}** - Server: **{server.name}** - Search - Character: **{character}**')
    except:
        pass
    return

async def send_logs_error(member, msg):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Message: **{msg}**')
    except:
        pass
    return

async def send_logs_acraffle(member, server, msg, character):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Character: **{character}**')
    except:
        pass
    return

async def send_logs_acraffle_more(member, server, msg, character,dupe,rarity):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Character: **{character}** - **{rarity}** - **{dupe}**')
    except:
        pass
    return

async def send_logs_acrank(member, server, msg, character):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Rank: **{character}**')
    except:
        pass
    return

async def send_logs_acbs(commanduser,member, server, msg, show):
    channel = client.get_channel(banklogChannelID)
    try:
        await channel.send(f'User: **{commanduser.name}** - Viewed: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - show: **{show}**')
    except:
        pass
    return

async def send_logs_acbr(commanduser,member, server, msg, rarity):
    channel = client.get_channel(banklogChannelID)
    try:
        await channel.send(f'User: **{commanduser.name}** - Viewed: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - Rarity: **{rarity}**')
    except:
        pass
    return

async def send_logs_actrade(member, server, msg, personTraded, characterGave, characterRecieve):
    channel = client.get_channel(logChannelID)
    try:
        await channel.send(f'User: **{member.name}** - Server: **{server.name}** - Command: **{msg}** - User Traded: **{personTraded.name}** - Character Gave: **{characterGave}** - Character Receievd: **{characterRecieve}**')
    except:
        pass
    return

async def send_logs_cooldown(commanduser,server):
    channel = client.get_channel(cooldownChannelID)
    try:
        await channel.send(f'User: **{commanduser.name}** - Server: **{server.name}** - Cooldown')
    except:
        pass
    return


dbl_token = os.getenv('TOPGGTOKEN') # set this to your bot's Top.gg token
client.topggpy = topgg.DBLClient(client, dbl_token, autopost=True, post_shard_count=True)


 
client.run(os.getenv('BOTTOKEN'))
