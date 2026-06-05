import discord
from discord.ext import commands
import re
import os

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# --- Bot setup ---
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ✅ Only censor if the actual username matches "minimoog2959"
    if message.author.name == "minimoog2959":
        # Block GIFs (attachments ending in .gif)
        has_gif = any(attachment.filename.lower().endswith(".gif") for attachment in message.attachments)

        # Block images (attachments ending in common image formats)
        has_image = any(attachment.filename.lower().endswith(ext) for attachment in message.attachments
                        for ext in [".png", ".jpg", ".jpeg", ".webp"])

        # Block emojis (Unicode emoji ranges or custom Discord emoji <:name:id>)
        has_emoji = re.search(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F]", message.content) \
                    or re.search(r"<:.+?:\d+>", message.content)

        # Block stickers
        has_sticker = len(message.stickers) > 0

        if has_gif or has_image or has_emoji or has_sticker:
            try:
                await message.delete()
                await message.channel.send(
                    "*A strong gust of wind suddenly sweeps dust into your eyes; you reflexively blink it away while wondering what had happened."
                )
            except Exception as e:
                print(f"Failed to delete message: {e}")

    # Allow commands to still work
    await bot.process_commands(message)


# --- Example command to test bot is alive ---
@bot.command()
async def ping(ctx):
    await ctx.send("Bot is running and censoring GIFs, images, emojis, and stickers from minimoog2959!")


# --- Run the bot ---
bot.run(os.getenv("BOT_TOKEN"))
