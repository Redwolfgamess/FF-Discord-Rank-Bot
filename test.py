import discord
from discord import app_commands
from discord.ui import Button, View

from typing import Optional


from constants import INSTRUMENT_CHOICES, DECAY_RATE, INSTRUMENT_THRESHOLDS, RANK_EMOJI, INSTRUMENTS
from config import  bot_token, bot

from discord_utils import username_autocomplete, song_name_autocomplete, pending_scores
from NEW_ranking_utils import calculate_normalized_score
from json_utils import save_data, load_player_data, load_song_info, save_song_info
from image_processing import extract_data_async


@bot.event
async def on_ready():
    try:
        print(f"Logged in as {bot.user}")

        guild_id = 1315452784837132308
        guild = discord.Object(id=guild_id)

        # Sync only the intended commands
        bot.tree.copy_global_to(guild=guild)  # Only if you want global commands available in the guild
        synced = await bot.tree.sync(guild=guild)

        print(f"Synced {len(synced)} commands to guild {guild_id}")

    except Exception as e:
        print(f"Sync failed: {e}")

@bot.tree.command(name="submit", description="Submit a new score for a specific song and instrument.")
@app_commands.describe(
    instrument="Select the instrument",
    song_name="Select a song",
    username="(Optional) Submit for another user (Rank Manager only)"
)
@app_commands.choices(instrument=INSTRUMENT_CHOICES)
@app_commands.autocomplete(song_name=song_name_autocomplete)
@app_commands.autocomplete(username=username_autocomplete)
async def submit(interaction: discord.Interaction, instrument: str, song_name: str, username: Optional[str] = None):
    await interaction.response.defer()  # Defer response to avoid timeouts

    guild = interaction.guild
    player_id = str(interaction.user.id)
    submitter_username = interaction.user.name

    # Validate permissions for submitting for another user
    if username:
        rank_manager_role = discord.utils.get(guild.roles, name="Rank Manager")
        if rank_manager_role not in interaction.user.roles:
            embed = discord.Embed(title="⛔ Error", description="You do not have permission to submit scores for other users.", color=discord.Color.red())
            await interaction.followup.send(embed=embed)
            return
        member = discord.utils.get(guild.members, name=username)
        if not member:
            embed = discord.Embed(title="⛔ Error", description=f"Could not find a user with the username `{username}`.", color=discord.Color.red())
            await interaction.followup.send(embed=embed)
            return
        player_id = str(member.id)
        submitter_username = username

    instrument_lower = instrument.lower()
    song_name_lower = song_name.lower()

    # Load song info
    song_info = load_song_info()

    # Validate instrument
    if instrument_lower not in (key.lower() for key in song_info.keys()):
        embed = discord.Embed(title="⛔ Error", description=f"The instrument `{instrument}` is not recognized.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    instrument_data = next((key for key in song_info if key.lower() == instrument_lower), None)
    song_data = next((key for key in song_info[instrument_data] if key.lower() == song_name_lower), None)

    if song_data is None:
        embed = discord.Embed(title="⛔ Error", description=f"`{song_name}` was not found for `{instrument}`.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    correct_song_name = song_data
    difficulty = song_info[instrument_data][correct_song_name].get("difficulty", "X")

    if difficulty == "X":
        embed = discord.Embed(title="📏 Enter Difficulty", description="Please enter the difficulty (1-7): (Help at https://www.gamespot.com/gallery/every-fortnite-festival-song-sorted-by-difficulty/2900-5620/#4)", color=discord.Color.blue())
        await interaction.followup.send(embed=embed)
        try:
            response = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=120.0)
            difficulty = float(response.content.strip())
            song_info[instrument_data][correct_song_name]["difficulty"] = difficulty
            save_song_info(song_info)
        except Exception:
            embed = discord.Embed(title="⛔ Error", description="Difficulty input timed out or was invalid.", color=discord.Color.red())
            await interaction.followup.send(embed=embed)
            return
    else:
        difficulty = float(difficulty)

    # Request performance details from the user
    embed = discord.Embed(title="🎵 Enter Performance Details", description="Enter your performance details as `perfect, good, missed, striked` (comma-separated values):", color=discord.Color.blue())
    await interaction.followup.send(embed=embed)

    try:
        response = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=120.0)
        perfect, good, missed, striked = map(float, response.content.split(","))
    except Exception:
        embed = discord.Embed(title="⛔ Error", description="Invalid input or timeout.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    total_notes = int(perfect + good + missed + striked)
    song_info[instrument_data][correct_song_name]["total_notes"] = total_notes
    save_song_info(song_info)

    # Request image proof
    embed = discord.Embed(title="📷 Upload Image Proof", description="Please upload an image as proof of your score.", color=discord.Color.blue())
    await interaction.followup.send(embed=embed)

    try:
        image_message = await bot.wait_for(
            "message",
            check=lambda m: m.author == interaction.user and m.attachments,
            timeout=120.0
        )
        image_url = image_message.attachments[0].url  # Save the image URL
    except Exception:
        embed = discord.Embed(title="⛔ Error", description="Image upload timed out or invalid.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    # Load previous scores
    user_scores = load_player_data()

    # Ensure structure exists in data to prevent key errors
    previous_score = (
        user_scores.get(player_id, {})
        .get(instrument_lower, {})
        .get("songs", {})
        .get(correct_song_name, 0)
    )

    # Calculate new normalized score
    normalized_score = calculate_normalized_score(perfect, good, missed, striked, difficulty)

    if not isinstance(normalized_score, (int, float)) or normalized_score < 0:
        embed = discord.Embed(title="⛔ Error", description="Invalid score calculation. Please try again.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    # Determine result message
    if previous_score == 0:
        title = "🎵 New Song Submitted!"
        description = f"**{submitter_username}** has submitted a score for `{correct_song_name}` on `{instrument}`!"
        color = discord.Color.green()
    elif normalized_score > previous_score:
        title = "🎉 New High Score!"
        description = f"**{submitter_username}** has beaten their previous score for `{correct_song_name}` on `{instrument}`!"
        color = discord.Color.gold()
    else:
        title = "✅ Score Submitted!"
        description = f"Score submitted for `{correct_song_name}` on `{instrument}`."
        color = discord.Color.blue()

    # Save the new score
    await save_data(player_id, submitter_username, instrument_lower, correct_song_name, normalized_score)

    # Create embed for final confirmation
    embed = discord.Embed(title=title, description=description, color=color)
    embed.add_field(name="📊 New Score", value=f"`{normalized_score:.2f}`", inline=True)
    embed.add_field(name="📉 Previous Score", value=f"`{previous_score:.2f}`", inline=True)
    embed.set_image(url=image_url)  # Display proof image

    await interaction.followup.send(embed=embed)

    # Perform OCR extraction once
    extracted_perfect, extracted_good, extracted_missed, extracted_striked = await extract_data_async(image_url, perfect, good, missed, striked)

    if (extracted_perfect, extracted_good, extracted_missed, extracted_striked) == (perfect, good, missed, striked):
        await interaction.followup.send("Image verified successfully!")
    else:
        await interaction.followup.send("Image verification failed.")

    if (perfect, good, missed, striked) != (extracted_perfect, extracted_good, extracted_missed, extracted_striked):
        pending_scores(embed, guild, perfect, good, missed, striked)

bot.run(bot_token)