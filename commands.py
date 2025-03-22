import random
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
@app_commands.describe(song_name="This is case-sensitive! Please enter correctly and contact @rank manager if a mistake is made.")
async def add(interaction: discord.Interaction, song_name: str):
    try:
        print("Add command executed")

        # Load the existing database
        data = load_song_info()

        # Check if the song already exists across all instruments
        song_exists = any(song_name in data.get(instrument, {}) for instrument in INSTRUMENTS)

        if song_exists:
            await interaction.response.send_message(f"Song '{song_name}' already exists in the database.", ephemeral=True)
            return

        # Add the song to all instruments
        for instrument in INSTRUMENTS:
            if instrument not in data:
                data[instrument] = {}

            data[instrument][song_name] = {"difficulty": "X"}

        # Save the updated database
        save_song_info(data)

        await interaction.response.send_message(f"Song '{song_name}' added to all instruments.")
    
    except Exception as e:
        print(f"Error in add_song command: {e}")
        await interaction.response.send_message("An error occurred while processing your command.", ephemeral=True)


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
        
@bot.tree.command(name="role_rank", description="View the named rank and top 5 scores breakdown for a user on an instrument.")
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
            difficulty = song_metadata.get("difficulty", "Unknown")  # Extract difficulty
            perfect, good = calculate_notes(score, song_metadata)
            song_details += f"**{i}.** {song_name} — **{score} pts**\n **Difficulty:** {difficulty} | **Perfect:** {perfect} | **Good:** {good}\n\n"


        embed = discord.Embed(
            title=f"🏆 Role Rank for {username}",
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

@bot.tree.command(name="accuracy_leaderboard", description="Display top player scores, optionally filtered by instrument.")
async def leaderboard(interaction: discord.Interaction, instrument: str = None):
    await interaction.response.defer()
    
    try:
        data = load_player_data()
        if not data:
            await interaction.followup.send("No player data available.", ephemeral=True)
            return

        song_info = load_song_info()  # Load song metadata
        players = []
        
        for player_id, player_data in data.items():
            username = player_data.get("username", f"User {player_id}")
            highest_score = None
            best_song = None
            best_perfect = 0
            best_good = 0

            for key, instrument_data in player_data.items():
                if not isinstance(instrument_data, dict) or "songs" not in instrument_data:
                    continue
                
                if instrument and key.lower() != instrument.lower():
                    continue
                
                for song_name, score in instrument_data["songs"].items():
                    song_metadata = get_song_metadata(song_name, key, song_info)
                    if not song_metadata:
                        continue
                    
                    perfect, good = calculate_notes(score, song_metadata)  # Correct note calculation
                    
                    if highest_score is None or score > highest_score:
                        highest_score = score
                        best_song = song_name
                        best_perfect = perfect
                        best_good = good
            
            if highest_score is not None:
                players.append((username, highest_score, best_song, best_perfect, best_good))

        if not players:
            await interaction.followup.send("No scores found.", ephemeral=True)
            return

        players_sorted = sorted(players, key=lambda x: x[1], reverse=True)
        leaderboard_text = "\n".join([
            f"**{username}**: {score:.2f} ({song})\n**Perfect:** {perfect} | **Good:** {good}"
            for username, score, song, perfect, good in players_sorted
        ])
        
        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=f"Top player scores{' for ' + instrument if instrument else ''}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Top Players", value=leaderboard_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    except discord.errors.NotFound:
        await interaction.response.send_message("⚠️ Webhook expired, please try again.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error fetching leaderboard: {e}", ephemeral=True)



@bot.tree.command(name="leaderboard", description="Display top player scores, optionally filtered by instrument.")
async def leaderboard(interaction: discord.Interaction, instrument: str = None):
    await interaction.response.defer()
    
    try:
        data = load_player_data()
        if not data:
            await interaction.followup.send("No player data available.", ephemeral=True)
            return

        players = []
        for player_id, player_data in data.items():
            username = player_data.get("username", f"User {player_id}")
            highest_score = None
            best_song = None
            best_perfect = 0
            best_good = 0

            for key, instrument_data in player_data.items():
                if not isinstance(instrument_data, dict) or "songs" not in instrument_data:
                    continue
                
                if instrument and key.lower() != instrument.lower():
                    continue
                
                for song_name, score in instrument_data["songs"].items():
                    song_metadata = get_song_metadata(song_name, key, load_song_info())
                    if not song_metadata:
                        continue
                    perfect, good = calculate_notes(score, song_metadata)
                    
                    if highest_score is None or score > highest_score:
                        highest_score = score
                        best_song = song_name
                        best_perfect = perfect
                        best_good = good
            
            if highest_score is not None:
                players.append((username, highest_score, best_song, best_perfect, best_good))

        if not players:
            await interaction.followup.send("No scores found.", ephemeral=True)
            return

        players_sorted = sorted(players, key=lambda x: x[1], reverse=True)
        leaderboard_text = "\n".join([
            f"**{username}**: {score:.2f} ({song})\n**Perfect:** {perfect} | **Good:** {good}"
            for username, score, song, perfect, good in players_sorted
        ])
        
        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=f"Top player scores{' for ' + instrument if instrument else ''}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Top Players", value=leaderboard_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    except discord.errors.NotFound:
        await interaction.response.send_message("⚠️ Webhook expired, please try again.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error fetching leaderboard: {e}", ephemeral=True)


class SongsPaginationView(View):
    def __init__(self, username, instrument, top_songs):
        super().__init__(timeout=120)
        self.username = username
        self.instrument = instrument
        self.top_songs = top_songs
        self.page = 0
        self.per_page = 10  # Show 10 songs per page

        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.top_songs) - 1) // self.per_page

    def generate_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        displayed_songs = self.top_songs[start:end]

        embed = discord.Embed(
            title=f"🎵 Top Performances for {self.username}",
            description=f"**Instrument:** {self.instrument.capitalize()}",
            color=discord.Color.blue()
        )

        for rank, (song_name, score, weight, difficulty, perfect, good) in enumerate(displayed_songs, start=start + 1):
            embed.add_field(
                name=f"**{rank}.** {song_name}   -   Difficulty: {difficulty} ⭐ ",
                value=f"**{score:.2f} pts** (*{weight:.2f}% weight*)\n"
                      f"🎯 **Perfect:** {perfect} | **Good:** {good}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.page + 1} of {(len(self.top_songs) - 1) // self.per_page + 1}")
        return embed

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        self.page -= 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.top_songs) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.page += 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.top_songs) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

@bot.tree.command(name="songs", description="Show top 25 performances for a specific user on a specific instrument.")
@app_commands.autocomplete(username=username_autocomplete)
@app_commands.choices(instrument=INSTRUMENT_CHOICES)
async def songs(interaction: discord.Interaction, username: str, instrument: str):
    try:
        data = load_player_data()
        song_info = load_song_info()

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

        top_songs = sorted(songs.items(), key=lambda x: x[1], reverse=True)[:25]

        scores_list = []  
        formatted_songs = []  

        for rank, (song_name, score) in enumerate(top_songs, start=1):
            weight = 100 * (DECAY_RATE ** (rank - 1))
            scores_list.append(score)  

            song_metadata = get_song_metadata(song_name, instrument, normalized_song_info)
            perfect, good = calculate_notes(score, song_metadata)

            difficulty = song_metadata.get("difficulty", "Unknown") if song_metadata else "Unknown"

            formatted_songs.append((song_name, score, weight, difficulty, perfect, good))

        final_rank = calculate_final_rank(scores_list)

        view = SongsPaginationView(username, instrument, formatted_songs)
        await interaction.response.send_message(embed=view.generate_embed(), view=view)

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

@bot.tree.command(name="create_tournament", description="Create tournament divisions based on players' highest scores. (For all players)")
async def create_tournament(interaction: discord.Interaction):
    await interaction.response.defer()  # Ensure the interaction is acknowledged

    try:
        data = load_player_data()
        if not data:
            await interaction.followup.send("No player data available for tournament creation.", ephemeral=True)
            return

        players = []
        for player_id, player_data in data.items():
            player_highest = None
            username = player_data.get("username", f"User {player_id}")
            for key, instrument_data in player_data.items():
                if not isinstance(instrument_data, dict) or "songs" not in instrument_data:
                    continue
                songs = instrument_data["songs"]
                if songs:
                    max_score = max(songs.values())
                    if player_highest is None or max_score > player_highest:
                        player_highest = max_score
            if player_highest is not None:
                players.append((player_id, username, player_highest))
        
        if not players:
            await interaction.followup.send("No players with scores found.", ephemeral=True)
            return

        scores = [score for (_, _, score) in players]
        scores_sorted = sorted(scores)
        N = len(scores_sorted)
        q1 = scores_sorted[int(0.25 * (N - 1))]
        q2 = scores_sorted[int(0.50 * (N - 1))]
        q3 = scores_sorted[int(0.75 * (N - 1))]

        divisions = {"Division 1": [], "Division 2": [], "Division 3": [], "Division 4": []}
        for player_id, username, score in players:
            if score >= q3:
                divisions["Division 1"].append((username, score))
            elif score >= q2:
                divisions["Division 2"].append((username, score))
            elif score >= q1:
                divisions["Division 3"].append((username, score))
            else:
                divisions["Division 4"].append((username, score))

        embed = discord.Embed(
            title="🏆 Tournament Divisions",
            description="Players have been separated into divisions based on their highest scores.",
            color=discord.Color.purple()
        )
        embed.add_field(name="Division Thresholds", value=f"**Q1:** {q1:.2f}\n**Q2:** {q2:.2f}\n**Q3:** {q3:.2f}", inline=False)
        for division, players_list in divisions.items():
            if players_list:
                players_sorted = sorted(players_list, key=lambda x: x[1], reverse=True)
                division_text = "\n".join([f"**{username}**: {score:.2f}" for username, score in players_sorted])
            else:
                division_text = "No players in this division."
            embed.add_field(name=division, value=division_text, inline=False)

        await interaction.followup.send(embed=embed)

    except discord.errors.NotFound:
        # Webhook expired, try sending a normal response instead
        await interaction.response.send_message("⚠️ Webhook expired, please try again.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error creating tournament divisions: {e}", ephemeral=True) 

@bot.tree.command(name="create_tournament_event", description="Create tournament divisions based on players' highest scores.")
async def create_tournament(interaction: discord.Interaction, event_id: str):
    # Role restriction
    required_role_id = 1334940931861778453
    if required_role_id not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()  # Defer the response to prevent timeout

    try:
        # Convert event_id to an integer
        event_id = int(event_id)

        # Get the event object using the event_id
        guild = interaction.guild
        event = discord.utils.get(guild.scheduled_events, id=event_id)  # No await

        if not event:
            await interaction.followup.send(f"⚠️ No event found with ID {event_id}.", ephemeral=True)
            return

        # Fetch users who are marked as "Interested" in the event
        interested_users = [user async for user in event.users()]  # Ensure this works

        if not interested_users:
            await interaction.followup.send("⚠️ No users are marked as interested in this event.", ephemeral=True)
            return

        # Tournament role ID to assign
        tournament_role_id = 1350650150363856896
        tournament_role = guild.get_role(tournament_role_id)

        if not tournament_role:
            await interaction.followup.send("⚠️ Tournament role not found.", ephemeral=True)
            return

        # Filter users who are in the player data
        data = load_player_data()
        if not data:
            await interaction.followup.send("No player data available for tournament creation.", ephemeral=True)
            return

        players = []
        for user in interested_users:
            player_id = str(user.id)  # Ensure the ID matches the format in stored data
            if player_id not in data:
                continue  # Skip users who aren't in the tournament data

            player_highest = None
            username = data[player_id].get("username", user.name)
            for key, instrument_data in data[player_id].items():
                if not isinstance(instrument_data, dict) or "songs" not in instrument_data:
                    continue
                songs = instrument_data["songs"]
                if songs:
                    max_score = max(songs.values())
                    if player_highest is None or max_score > player_highest:
                        player_highest = max_score
            if player_highest is not None:
                players.append((user, username, player_highest))

        if not players:
            await interaction.followup.send("No players with scores found among the event participants.", ephemeral=True)
            return

        # Assign role to all interested users
        for user, _, _ in players:
            member = guild.get_member(user.id)  # Fetch the Member object from the User object
            if member:
                try:
                    await member.add_roles(tournament_role)
                except discord.Forbidden:
                    await interaction.followup.send(f"⚠️ I don't have permission to assign roles to {user.mention}.", ephemeral=True)
                except discord.HTTPException:
                    await interaction.followup.send(f"⚠️ Failed to assign the tournament role to {user.mention}.", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ Could not find member for user {user.mention}.", ephemeral=True)

        # Shuffle players to randomly create the first bracket
        random.shuffle(players)

        # Create divisions dynamically ensuring at least 8 players per division
        divisions = {}
        current_division = 1
        division_players = []
        for user, username, score in players:
            division_players.append((username, score))
            if len(division_players) >= 8:  # Ensure at least 8 players in a division
                divisions[f"Division {current_division}"] = division_players
                current_division += 1
                division_players = []  # Reset for the next division

        # If there are leftover players that don't fit into a division of 8
        if division_players:
            divisions[f"Division {current_division}"] = division_players

        # Create random brackets for each division
        brackets = {}
        for division, players_list in divisions.items():
            random.shuffle(players_list)  # Shuffle players in the division
            division_brackets = []
            if len(players_list) % 2 == 1:  # If there's an odd number of players
                # Give one player a bye (no match)
                bye_player = players_list[-1]  # Last player in the list gets a bye
                division_brackets.append((f"{bye_player[0]} (Bye)", "No Match"))  # Add the bye player to the bracket
                players_list = players_list[:-1]  # Remove the bye player from the list
            
            # Create pairs for the bracket (ensuring even number of players)
            for i in range(0, len(players_list), 2):
                division_brackets.append((players_list[i], players_list[i + 1]))
            brackets[division] = division_brackets

        # Create embed with division and bracket results
        embed = discord.Embed(
            title=f"🏆 Tournament Divisions & Brackets - {event.name}",
            description="Players have been separated into divisions and randomized brackets have been created.",
            color=discord.Color.purple()
        )

        # Add division results and brackets to the embed
        for division, players_list in divisions.items():
            if players_list:
                players_sorted = sorted(players_list, key=lambda x: x[1], reverse=True)
                division_text = "\n".join([f"**{username}**: {score:.2f}" for username, score in players_sorted])
            else:
                division_text = "No players in this division."

            # Add division players
            embed.add_field(name=f"{division} Players", value=division_text, inline=False)

            # Add bracket pairs
            division_brackets = brackets[division]
            bracket_text = "\n".join([
                f"**Match {index+1}:** {player1[0]} vs {player2[0]}" if player2 != "No Match" 
                else f"**Match {index+1}:** {player1[0]} (Bye)" 
                for index, (player1, player2) in enumerate(division_brackets)
            ])

            embed.add_field(name=f"{division} Brackets", value=bracket_text, inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Error creating tournament divisions: {e}", ephemeral=True)


@bot.tree.command(name="remove_tournament_role", description="Remove the tournament role from all players.")
async def remove_tournament_role(interaction: discord.Interaction):
    # Role restriction
    required_role_id = 1334940931861778453
    if required_role_id not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        guild = interaction.guild
        tournament_role_id = 1350650150363856896
        tournament_role = guild.get_role(tournament_role_id)

        if not tournament_role:
            await interaction.followup.send("⚠️ Tournament role not found.", ephemeral=True)
            return

        # Find members with the role
        members_with_role = [member async for member in guild.fetch_members() if tournament_role in member.roles]

        if not members_with_role:
            await interaction.followup.send("⚠️ No members have the tournament role.", ephemeral=True)
            return

        # Remove the role from all members
        for member in members_with_role:
            try:
                await member.remove_roles(tournament_role)
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ I don't have permission to remove roles from {member.mention}.", ephemeral=True)
            except discord.HTTPException:
                await interaction.followup.send(f"⚠️ Failed to remove the tournament role from {member.mention}.", ephemeral=True)

        await interaction.followup.send("✅ The tournament role has been removed from all players.")

    except Exception as e:
        await interaction.followup.send(f"⚠️ Error removing tournament role: {e}", ephemeral=True)


# @bot.tree.command(name="check_total_notes", description="Check how many songs with a set difficulty also have total notes stored.")
# async def check_total_notes(interaction: discord.Interaction):
#     await interaction.response.defer()

#     song_info = load_song_info()
#     total_songs_with_difficulty = 0
#     songs_with_total_notes = 0
#     missing_songs = []

#     for instrument, songs in song_info.items():
#         for song_name, data in songs.items():
#             difficulty = data.get("difficulty", "X")
#             total_notes = data.get("total_notes")

#             if isinstance(difficulty, (int, float)) and difficulty != "X":
#                 total_songs_with_difficulty += 1
#                 if isinstance(total_notes, int):
#                     songs_with_total_notes += 1
#                 else:
#                     missing_songs.append((instrument, song_name))

#     view = PaginationView(missing_songs, total_songs_with_difficulty, songs_with_total_notes)
#     await interaction.followup.send(embed=view.generate_embed(), view=view)

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
