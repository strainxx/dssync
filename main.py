import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject
from config import TG_TOKEN, MONGO_TOKEN, DS_TOKEN, CHANNEL_ID
from pymongo import MongoClient
import discord
from discord.ext import commands

intents = discord.Intents.all()

ds_bot = commands.Bot("tg?", intents=intents)

client = MongoClient(MONGO_TOKEN)
database = client["DB"]
collection = database["tg"]


logging.basicConfig(level=logging.INFO)

bot = Bot(token=TG_TOKEN)

channel: discord.abc.GuildChannel = None #type: ignore

dp = Dispatcher()
last_user_data: dict = {}
ratelimited = False
# DISCORD:
@ds_bot.event
async def on_ready():
    print(f'We have logged in as {ds_bot.user.display_name}') # type: ignore
    await ds_bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Rate Limit status: {"✅" if ratelimited else "❌"}"))

@ds_bot.command()
async def upd(ctx: commands.Context):
    global channel
    channel = await ds_bot.fetch_channel(CHANNEL_ID) # type: ignore

@ds_bot.event
async def on_message(message: discord.Message):
    try:
        isReply = await message.channel.fetch_message(message.reference.message_id) #type: ignore
    except:
        isReply = None
    for user_entry in collection.find({"notify": True}):
        if message.content != "":
            await bot.send_message(user_entry["id"], f"*{message.guild.name} #{message.channel.name}*\n\
{message.author.display_name}{f" -> {isReply.author.display_name}" if isReply != None else ""}:\
                                    \n{message.content}", parse_mode="Markdown") #type: ignore
        else:
            for att in message.attachments:
                await bot.send_photo(user_entry["id"], att.url, caption=f"*{message.guild.name} #{message.channel.name}*\n\
{message.author.display_name}{f" -> {isReply.author.display_name}" if isReply != None else ""}:"
                                     , parse_mode="Markdown") #type: ignore

@ds_bot.event
async def on_command_error(ctx: commands.Context, error):
    global ratelimited
    if isinstance(error, discord.HTTPException) or isinstance(error, discord.RateLimited):
        await ctx.send("_We are rate limited!_")
        await ctx.send(f"**{list(last_user_data.items())[0][0]}**:\n{list(last_user_data.items())[0][1]}")
        ratelimited = True
        await ds_bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Rate Limit status: {"✅" if ratelimited else "❌"}"))
# TELEGRAM:
@dp.message(Command("name"))
async def set_name(message: types.Message, command: CommandObject):
    newname = command.args
    user = {
        "id": message.from_user.id, # type: ignore
        "name": newname
    }
    collection.update_one({"id": message.from_user.id}, {'$set': user}) # type: ignore
        
    await message.answer(f"Done! Your name now: {newname}")

@dp.message(Command("pic"))
async def set_pfp(message: types.Message, command: CommandObject):
    newpfp = command.args
    user = {
        "pic": newpfp
    }
    collection.update_one({"id": message.from_user.id}, {'$set': user}) # type: ignore
        
    await message.answer(f"Done! Your pfp now: {newpfp}")

@dp.message(Command("me"))
async def get_me(message: types.Message):
    user_entry: dict = collection.find_one({"id": message.from_user.id}) # type: ignore
    await message.answer(f"Your name: {user_entry["name"]}\nNotifications: {"✅" if user_entry["notify"] else "❌"}")

@dp.message(Command("help"))
async def send_help(message: types.Message):
    await message.answer(f"🌙 Account:\nChange name: /name Name123\nChange pfp: /pic https://example.com/picture.png\nAccount info: /me\n\
Turn off/on notifications: /notify on/off\n\
⭐ Other:\nЦитата дня: /start")



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hi! MongoDB govno, JSON snimae luchshe.\nHelp: /help")
    user = {
        "id": message.from_user.id, # type: ignore
        "name": message.from_user.full_name, # type: ignore
        "notify": True,
    }
    if collection.find_one({"id": message.from_user.id}): # type: ignore
        collection.update_one({"id": message.from_user.id}, {'$set': user}) # type: ignore
    else:
        collection.insert_one(user)

@dp.message(Command("notify"))
async def change_notify(message: types.Message, command: CommandObject):
    await message.reply(f"Turning {command.args} notifications..")
    await message.reply_dice(emoji="⚽")
    await asyncio.sleep(4)
    await message.reply("ГООООЛ")
    collection.update_one({"id": message.from_user.id}, {'$set': {"notify": True if command.args == "on" else False}})

@dp.message()
async def handle_message(message: types.Message):
    global last_user_data

    uname = collection.find_one({"id": message.from_user.id})["name"] # type: ignore
    r_name = f"{uname} [Telegram]"
    pic = collection.find_one({"id": message.from_user.id}).get("pic")
    last_user_data = {r_name, message.text} # type: ignore
    # global channel
    if not ratelimited:
        channel = await ds_bot.fetch_channel(CHANNEL_ID)
        
        # user_profile_photo: types.UserProfilePhotos = await bot.get_user_profile_photos(message.from_user.id)
        if message.text != "":
            whook = await channel.create_webhook(name=r_name) # type: ignore
            await whook.send(content=message.md_text, avatar_url=pic)
            await whook.delete()
        else:
            for photo in message.photo:
                ph = await bot.download(photo, destination="temp.png")
                whook = await channel.create_webhook(name=r_name) # type: ignore
                await whook.send(file=discord.File("temp.png"), avatar_url=pic)
                await whook.delete()
    else:
        channel = await ds_bot.fetch_channel(CHANNEL_ID)
        await channel.send(f"**{list(last_user_data.items())[0][0]}**:\n{list(last_user_data.items())[0][1]}")
# Start all this shit
async def main():
    await asyncio.gather(dp.start_polling(bot), ds_bot.start(DS_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
