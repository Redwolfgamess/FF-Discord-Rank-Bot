import discord
from discord import app_commands
from discord.ui import Button, View
from typing import Optional

from constants import INSTRUMENT_CHOICES, DECAY_RATE, INSTRUMENT_THRESHOLDS, RANK_EMOJI, INSTRUMENTS, GUILD_ID
from config import  bot_token, bot

from discord_utils import username_autocomplete, song_name_autocomplete, pending_scores
from ranking_utils import determine_rank, calculate_normalized_score, calculate_final_rank, reverse_normalized_score, get_user_instrument_data, get_song_metadata, calculate_notes
from json_utils import save_data, load_player_data, load_song_info, save_song_info
from image_processing import extract_data_async

# Calculate average accuracy across all songs, categorise /leaderboard with this
# Include  calculated accuracy on the /tournament_rank command
# Fix the assigning average role 
TEST CHANGE 

CHANGE BACK

@bot.event
async def on_ready():
    try:
        print(f"Logged in as {bot.user}")

        guild = discord.Object(id=GUILD_ID)

        # Sync only the intended commands
        bot.tree.copy_global_to(guild=guild)  # Only if you want global commands available in the guild
        synced = await bot.tree.sync(guild=guild)

        print(f"Synced {len(synced)} commands to guild {GUILD_ID}")

    except Exception as e:
        print(f"Sync failed: {e}")


@bot.tree.command(name="add_song", description="Add a new song to all instruments.")
@app_commands.describe(song_name="This is cap sensitive! Please enter correctly and contact @rank manager if a mistake is made.")
async def add(interaction: discord.Interaction, song_name: str):
    try:
        print("Add command executed")

        # Load the existing database
        data = load_song_info()

        # Add the song to all instruments if not already present
        for instrument in INSTRUMENTS:
            if instrument not in data:
                data[instrument] = {}

            if song_name not in data[instrument]:
                data[instrument][song_name] = {"difficulty": "X"}

        # Save the updated database
        save_song_info(data)

        await interaction.response.send_message(f"Song '{song_name}' added to all instruments.")
    except Exception as e:
        print(f"Error in add_song command: {e}")
        await interaction.response.send_message("An error occurred while processing your command.")


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
        embed = discord.Embed(title="⛔ Error", description=f"`{song_name}` was not found for `{instrument}`. You can add the song with /add_song", color=discord.Color.red())
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
    embed = discord.Embed(
        title="🎵 Enter Performance Details", 
        description="Enter your performance details as `perfect, good, missed, striked` (comma-separated values):\n\n"
                    "**Note:** You can only submit scores with 0 missed and 0 striked.",
        color=discord.Color.blue()
    )
    await interaction.followup.send(embed=embed)

    try:
        response = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=120.0)
        perfect, good, missed, striked = map(float, response.content.split(","))
        
        # Enforce 0 missed and 0 striked
        if missed != 0 or striked != 0:
            embed = discord.Embed(title="⛔ Error", description="Your submission must have 0 missed and 0 striked.", color=discord.Color.red())
            await interaction.followup.send(embed=embed)
            return
    except Exception:
        embed = discord.Embed(title="⛔ Error", description="Invalid input or timeout.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return


    total_notes = int(perfect + good + missed + striked)
    song_info[instrument_data][correct_song_name]["total_notes"] = total_notes
    save_song_info(song_info)

    # Request image proof
    embed = discord.Embed(title="📷 Upload Image Proof", description="Please upload an image as proof of your score. ", color=discord.Color.blue())
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

    # Perform OCR extraction
    extracted_perfect, extracted_good, extracted_missed, extracted_striked = await extract_data_async(image_url, perfect, good, missed, striked)

    if (extracted_perfect, extracted_good, extracted_missed, extracted_striked) == (perfect, good, missed, striked):
        await interaction.followup.send("Image verified successfully!")
    else:
        await interaction.followup.send("Image verification failed.")
        await pending_scores(embed, guild, player_id, submitter_username, instrument, song_name, perfect, good, missed, striked)
        
@bot.tree.command(name="tournament_rank", description="View the named rank and top 5 scores breakdown for a user on an instrument.")
@app_commands.autocomplete(username=username_autocomplete)
@app_commands.choices(instrument=INSTRUMENT_CHOICES)  # Restrict instrument input to specific choices
async def namedrank(interaction: discord.Interaction, username: str, instrument: str):
    try:
        data = load_player_data()
        song_info = load_song_info() 

        user_data = get_user_instrument_data(username, instrument, data)
        if not user_data or "songs" not in user_data:
            await interaction.response.send_message(f"No song data found for {username} on {instrument}.", ephemeral=True)
            return

        named_rank = user_data.get("named_rank", "Bronze").lower()
        top_5_scores = sorted(user_data["songs"].items(), key=lambda x: x[1], reverse=True)[:5]
        average_top_5 = sum(score for _, score in top_5_scores) / len(top_5_scores) if top_5_scores else 0

        rank_thresholds = INSTRUMENT_THRESHOLDS.get(instrument.lower(), {})
        threshold_text = "\n".join([f"{RANK_EMOJI.get(rank.lower(), '')} **{rank}**: {score}" for rank, score in rank_thresholds.items()])

        next_rank, next_rank_diff = None, None
        for rank, score in rank_thresholds.items():
            if average_top_5 < score:
                next_rank, next_rank_diff = rank.lower(), score - average_top_5
                break

        named_rank_emoji = RANK_EMOJI.get(named_rank, "")
        next_rank_emoji = RANK_EMOJI.get(next_rank, "") if next_rank else ""
        next_rank_message = (
            f"You need **{next_rank_diff:.2f}** more points to reach {next_rank_emoji} **{next_rank.capitalize()}**!"
            if next_rank else "You've reached the highest rank!"
        )

        # Normalize song_info keys for case-insensitive matching
        normalized_song_info = {
            k.lower(): {song.lower().strip(): v for song, v in v.items()} for k, v in song_info.items()
        }

        song_details = ""
        for i, (song_name, score) in enumerate(top_5_scores, start=1):
            song_metadata = get_song_metadata(song_name, instrument, normalized_song_info)
            perfect, good = calculate_notes(score, song_metadata)
            song_details += f"**{i}.** {song_name} — **{score} pts**\n **Perfect:** {perfect} | **Good:** {good}\n\n"

        embed = discord.Embed(
            title=f"🏆 Tournament Rank for {username}",
            description=f"🎵 **Instrument:** {instrument.capitalize()}",
            color=discord.Color.gold()
        )
        embed.add_field(name="🏅 Named Rank", value=f"{named_rank_emoji} **{named_rank.capitalize()}**\n•", inline=False)
        embed.add_field(name="📊 Average Top 5 Score", value=f"**{average_top_5:.2f}**\n•", inline=True)
        embed.add_field(name="🎯 Rank Progress", value=next_rank_message + "\n•", inline=False)
        embed.add_field(name="📈 Rank Thresholds", value=(threshold_text if threshold_text else "No thresholds available.") + "\n•", inline=False)
        embed.add_field(name="🎶 Top 5 Scores", value=(song_details if song_details else "No scores recorded."), inline=False)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error retrieving named rank: {e}", ephemeral=True)

@bot.tree.command(name="leaderboard_accuracy", description="View the average accuracy of players on an instrument.")
@app_commands.choices(instrument=INSTRUMENT_CHOICES)  # Restrict instrument input to specific choices
async def leaderboard_accuracy(interaction: discord.Interaction, instrument: str):
    try:
        data = load_player_data()
        if not data:
            await interaction.response.send_message("No player data available.", ephemeral=True)
            return

        accuracy_list = []
        for username, user_data in data.items():
            user_instrument_data = get_user_instrument_data(username, instrument, data)
            if not user_instrument_data or "songs" not in user_instrument_data:
                continue

            total_accuracy = 0
            total_songs = 0
            for song_name, score in user_instrument_data["songs"].items():
                song_metadata = get_song_metadata(song_name, instrument, load_song_info())
                if not song_metadata:
                    continue
                perfect, good = calculate_notes(score, song_metadata)
                accuracy = (perfect + (good * 0.5)) / song_metadata["total_notes"] * 100  # Weighted accuracy formula
                total_accuracy += accuracy
                total_songs += 1

            if total_songs > 0:
                accuracy_list.append((username, total_accuracy / total_songs))

        if not accuracy_list:
            await interaction.response.send_message(f"No accuracy data found for {instrument}.", ephemeral=True)
            return

        sorted_accuracy = sorted(accuracy_list, key=lambda x: x[1], reverse=True)[:10]  # Top 10 players

        leaderboard_text = "\n".join([f"**{i+1}. {user}** — {acc:.2f}%" for i, (user, acc) in enumerate(sorted_accuracy)])

        embed = discord.Embed(
            title=f"🎯 Accuracy Leaderboard - {instrument.capitalize()}",
            description=leaderboard_text,
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error retrieving leaderboard: {e}", ephemeral=True)


@bot.tree.command(name="leaderboard", description="View the top 25 leaderboard for an instrument")
@app_commands.describe(instrument="The instrument to filter (optional)")
@app_commands.choices(instrument=INSTRUMENT_CHOICES) 
async def leaderboard(interaction: discord.Interaction, instrument: str = None):
    await interaction.response.defer()

    data = load_player_data()

    leaderboard = []
    for player_id, player_data in data.items():
        username = player_data.get("username", "Unknown")
        for instr, info in player_data.items():
            if instr == "username":
                continue
            if instrument and instr.lower() != instrument.lower():
                continue
            final_rank_score = info.get("final_rank_score", 0)
            leaderboard.append((username, instr, final_rank_score))

    leaderboard = sorted(leaderboard, key=lambda x: x[2], reverse=True)

    if not leaderboard:
        await interaction.followup.send(
            f"No leaderboard data found for instrument '{instrument}'." if instrument else "No leaderboard data found."
        )
        return
    response = f"**Top 25 Leaderboard{' for ' + instrument.capitalize() if instrument else ''}:**\n"
    for i, (username, instr, score) in enumerate(leaderboard[:25], start=1):
        rank = determine_rank(score)
        response += "```\n"
        response += f"#{i}: {username} ({instr.capitalize()}) - {score:.2f}, Rank: {rank}\n"
        response += "```"
    await interaction.followup.send(response)

@bot.tree.command(name="songs", description="Show top 25 performances for a specific user on a specific instrument.")
@app_commands.autocomplete(username=username_autocomplete)
@app_commands.choices(instrument=INSTRUMENT_CHOICES)
async def songs(interaction: discord.Interaction, username: str, instrument: str):
    try:
        data = load_player_data()
        song_info = load_song_info()

        # Normalize song_info keys for case-insensitive matching
        normalized_song_info = {
            k.lower(): {song.lower().strip(): v for song, v in v.items()} for k, v in song_info.items()
        }

        instrument_data = get_user_instrument_data(username, instrument, data)
        if not instrument_data or "songs" not in instrument_data:
            await interaction.response.send_message(f"No song data found for {username} on {instrument}.", ephemeral=True)
            return

        songs = instrument_data["songs"]
        if not songs:
            await interaction.response.send_message(f"No songs submitted for {instrument} by {username}.", ephemeral=True)
            return

        # Sort songs by scores in descending order
        top_songs = sorted(songs.items(), key=lambda x: x[1], reverse=True)[:25]

        scores_list = []  # Store scores for final rank calculation
        song_details = ""

        for rank, (song_name, score) in enumerate(top_songs, start=1):
            score = int(score)
            weight = 100 * (DECAY_RATE ** (rank - 1))
            scores_list.append(score)  # Collect scores for final rank calculation

            # Get song metadata
            song_metadata = get_song_metadata(song_name, instrument, normalized_song_info)
            perfect, good = calculate_notes(score, song_metadata)

            if song_metadata:
                song_details += f"**{rank}.** {song_name} — **{score} pts** (*{weight:.2f}% weight*)\n **Perfect:** {perfect} | **Good:** {good}\n\n"
            else:
                song_details += f"**{rank}.** {song_name} — **{score} pts** (*{weight:.2f}% weight*)\n⚠️ Missing song metadata\n\n"

        # Calculate the final rank using the function
        final_rank = calculate_final_rank(scores_list)

        # Create an embed for better formatting
        embed = discord.Embed(
            title=f"🎵 Top Performances for {username}",
            description=f"**Instrument:** {instrument.capitalize()}\n🏅 **Final Rank Score:** {final_rank:.2f}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🏆 Best Scores:", value=song_details, inline=False)

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error retrieving song data: {e}", ephemeral=True)

      
class PaginationView(View):
    def __init__(self, missing_songs, total_songs_with_difficulty, songs_with_total_notes, page=0):
        super().__init__(timeout=120)
        self.missing_songs = missing_songs
        self.page = page
        self.total_songs_with_difficulty = total_songs_with_difficulty
        self.songs_with_total_notes = songs_with_total_notes
        self.per_page = 10  # Songs per page

        # Disable previous button if on first page
        self.previous_button.disabled = self.page == 0

        # Disable next button if on last page
        self.next_button.disabled = self.page >= (len(missing_songs) - 1) // self.per_page

    def generate_embed(self):
        percentage = (self.songs_with_total_notes / self.total_songs_with_difficulty) * 100 if self.total_songs_with_difficulty else 0

        # Get 10 songs for the current page
        start = self.page * self.per_page
        end = start + self.per_page
        displayed_songs = self.missing_songs[start:end]

        missing_songs_text = "\n".join([f"🎵 {song} ({instrument})" for instrument, song in displayed_songs]) if displayed_songs else "✅ All songs have total notes!"

        embed = discord.Embed(
            title="📊 Total Notes Coverage",
            description=f"**Total Songs with Difficulty Set:** {self.total_songs_with_difficulty}\n"
                        f"**Songs with Total Notes:** {self.songs_with_total_notes}\n"
                        f"**Coverage Percentage:** {percentage:.2f}%\n\n"
                        f"**Missing Total Notes:**\n{missing_songs_text}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page + 1} of {(len(self.missing_songs) - 1) // self.per_page + 1}")
        return embed

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        self.page -= 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.missing_songs) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.page += 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.missing_songs) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

@bot.tree.command(name="check_total_notes", description="Check how many songs with a set difficulty also have total notes stored.")
async def check_total_notes(interaction: discord.Interaction):
    await interaction.response.defer()

    song_info = load_song_info()
    total_songs_with_difficulty = 0
    songs_with_total_notes = 0
    missing_songs = []

    for instrument, songs in song_info.items():
        for song_name, data in songs.items():
            difficulty = data.get("difficulty", "X")
            total_notes = data.get("total_notes")

            if isinstance(difficulty, (int, float)) and difficulty != "X":
                total_songs_with_difficulty += 1
                if isinstance(total_notes, int):
                    songs_with_total_notes += 1
                else:
                    missing_songs.append((instrument, song_name))

    view = PaginationView(missing_songs, total_songs_with_difficulty, songs_with_total_notes)
    await interaction.followup.send(embed=view.generate_embed(), view=view)

# @bot.tree.command(name="help", description="Show the bot's help message.")
# async def help_command(interaction: discord.Interaction):
#     help_message = """
#         **Bot Commands:**
#         - `/submit <instrument> <song name>`: Submit a new score for a specific song and instrument. You'll be prompted for details.
#         - `/rank <username> <instrument>`: Retrieve the final rank score and rank for a user on a specific instrument.
#         - `/tournament_rank <username> <instrument>`: View the named rank and top 5 scores breakdown for a user on an instrument.
#         - `/leaderboard <optionally, instrument>`: Display the top 25 players for a specific instrument. 
#         - `/songs <username> <instrument>`: Show top 25 performances for a specific user on a specific instrument.
#         - `/help`: Show this help message.

#         **Note:** Replace placeholders (e.g., `<username>`, `<instrument>`) with actual values when using the commands.

#         Instruments include:
#         - Lead
#         - Vocals
#         - Drums
#         - Bass
#         - Pro Lead
#         - Pro Bass
#         """
    
#     await interaction.response.send_message(help_message, ephemeral=True)

bot.run(bot_token)
