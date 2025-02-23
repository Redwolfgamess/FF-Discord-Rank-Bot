import discord
import asyncio
import signal

from config import bot, bot_token
from constants import STATUS_CHANNEL_NAMES

status_message = None

@bot.event
async def on_ready():
    global status_message
    print(f'Logged in as {bot.user}')
    print("Bot is ready, checking guilds...")

    # Iterate through guilds the bot is in
    for guild in bot.guilds:
        print(f"Checking guild: {guild.name} (ID: {guild.id})")

        # Find the status channel by any of the possible names
        try:
            channel = discord.utils.find(
                lambda c: c.name in STATUS_CHANNEL_NAMES, guild.text_channels
            )
            if channel:
                print(f"Found channel: {channel.name} (ID: {channel.id}) in guild: {guild.name}")
            else:
                print(f"Channel '{STATUS_CHANNEL_NAMES[0]}' not found in guild '{guild.name}', creating it.")
                # Create the channel if it doesn't exist
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True),
                }
                channel = await guild.create_text_channel(STATUS_CHANNEL_NAMES[0], overwrites=overwrites)
                print(f"Created channel '{STATUS_CHANNEL_NAMES[0]}' in guild '{guild.name}'.")

            # Rename the channel to indicate the bot is online
            await channel.edit(name="🟢bot-status")
            print(f"Channel renamed to 🟢bot-status in guild '{guild.name}'.")

            # Delete all previous messages in the channel
            async for message in channel.history(limit=None):
                await message.delete()

            # Send the "Rank tracker is online" message
            status_message = await channel.send("Rank tracker is online 🟢")
            print(f"Status message sent in channel: {channel.name}")
        except Exception as e:
            print(f"Error processing guild '{guild.name}': {e}")

@bot.event
async def on_resume():
    global status_message
    print("Bot reconnected")
    if status_message:
        try:
            await status_message.edit(content="Rank tracker is online 🟢")
            print("Status message updated to online.")
        except Exception as e:
            print(f"Error updating status message: {e}")

async def close_bot():
    global status_message
    print("Shutting down bot...")

    for guild in bot.guilds:
        try:
            # Find the channel by any of the possible names
            channel = discord.utils.find(
                lambda c: c.name in STATUS_CHANNEL_NAMES, guild.text_channels
            )
            if channel:
                # Rename the channel to indicate the bot is offline
                await channel.edit(name="🔴bot-status")
                print(f"Channel renamed to 🔴bot-status in guild '{guild.name}'.")

                # Update status message to offline
                if status_message:
                    await status_message.edit(content="Rank tracker is offline 🔴")
                    print("Status message updated to offline.")
            else:
                print(f"No status channel found in guild '{guild.name}'.")
        except Exception as e:
            print(f"Error processing guild '{guild.name}': {e}")

    await bot.close()

def shutdown_signal_handler(signal, frame):
    print("Received shutdown signal. Shutting down gracefully...")
    asyncio.create_task(close_bot())

# Set up signal handling for termination (Ctrl+C or closing the terminal)
signal.signal(signal.SIGINT, shutdown_signal_handler)
signal.signal(signal.SIGTERM, shutdown_signal_handler)

async def main():
    await bot.start(bot_token)

if __name__ == "__main__":
    asyncio.run(main())
