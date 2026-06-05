import discord
from discord.ext import commands
import re

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ Put your banned words here
banned_words = [
    "nigger",  # replace with your actual words
    "fuck",
    "sex"
    "daddy"
    "diddy"
    "epstein"
]

# Regex to catch banned words inside other words, case-insensitive
banned_regex = re.compile("|".join(banned_words), re.IGNORECASE)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if message contains banned words OR non-English characters
    if banned_regex.search(message.content) or re.search(r"[^\u0000-\u007F]", message.content):
        try:
            await message.delete()
            await message.channel.send(
                "*A strong gust of wind suddenly sweeps dust into your eyes; you reflexively blink it away while wondering what had happened."
            )
        except Exception as e:
            print(f"Failed to delete message: {e}")

    # Allow commands to still work
    await bot.process_commands(message)

bot.run("MTUwOTEyNDc5NzIzNjI1MjY5Mg.Ghtwwc.NCVdYtXc2McKoU3PgBcZLh6dgYriUROyfYzWNY")

