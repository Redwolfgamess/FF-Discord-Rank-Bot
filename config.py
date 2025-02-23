import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Access the bot token
bot_token = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)