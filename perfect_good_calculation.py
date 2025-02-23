# # Example usage:
# S = 850000  # Example normalized score - Get From player_data.json
# D = 5       # Difficulty level - Get from song_info.json
# M = 0      # Missed notes - Assume is 0
# R = 0       # Striked notes - Assume is 0
# total_notes = 500 - Get from song_info.json
# W_p = 1.0  # Weight for perfect notes - Variable imported from constants WEIGHTS = {
#     "perfect": 1.0,
#     "good": 0.5,
#     "missed": -0.5, 
#     "striked": -0.75
# }
# W_g = 0.5   # Weight for good notes
# W_m = -0.5  # Weight for missed notes
# W_s = -0.75  # Weight for striked notes

# P, G = calculate_perfect_good(S, D, M, R, total_notes, W_p, W_g, W_m, W_s)

import discord
from discord.ext import commands
import json
import os
from config import  bot_token, bot

# Define weight constants
WEIGHTS = {
    "perfect": 1.0,
    "good": 0.5,
    "missed": -0.5,
    "striked": -0.75
}

def load_player_data():
    try:
        if os.path.exists("player_data_test.json") and os.path.getsize("player_data_test.json") > 0:
            with open("player_data_test.json", "r") as file:
                return json.load(file)
        else:
            return {}
    except json.JSONDecodeError:
        return {}

def load_song_info():
    try:
        if os.path.exists("song_info.json") and os.path.getsize("song_info.json") > 0:
            with open("song_info.json", "r") as file:
                return json.load(file)
        else:
            return {}
    except json.JSONDecodeError:
        return {}

def save_player_data(player_data):
    # Specify the file path where you want to save the player data
    file_path = 'player_data_test.json'

    try:
        # Open the file in write mode and save the player data as JSON
        with open(file_path, 'w') as json_file:
            json.dump(player_data, json_file, indent=4)
        print(f"Player data saved to '{file_path}'")
    except Exception as e:
        print(f"Failed to save player data: {str(e)}")

def calculate_perfect_good(S, D, M, R, total_notes, W_p, W_g, W_m, W_s):
    if W_g == W_p:
        raise ValueError("W_g and W_p cannot be the same, division by zero error!")

    numerator = (S / D) - (M * W_m) - (R * W_s) - ((total_notes - (M + R)) * W_p)
    denominator = W_g - W_p
    G = numerator / denominator
    P = total_notes - (M + R) - G

    return int(P), int(G)

# Create bot instance
bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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

def calculate_normalized_score(perfect, good, missed, striked, difficulty):
    total_notes = perfect + good + missed + striked
    
    if total_notes == 0:
        return 0  # Avoid division by zero
    
    # Calculate the perfect-to-good ratio, emphasizing perfect accuracy
    accuracy_score = (perfect / total_notes) * 100  # Convert to percentage
    
    # Apply a small scaling factor based on total notes (logarithmic for diminishing returns)
    scaling_factor = 1 + (total_notes ** 0.1) * 0.02  # Keeps scaling mild
    
    # Final normalized score
    normalized_score = accuracy_score * scaling_factor * difficulty
    
    return round(normalized_score, 2)  # Round for readability

@bot.tree.command(name="perfect_good_calculation")
async def perfect_good_calculation(interaction):
    # Load data
    player_data = load_player_data()
    song_info = load_song_info()

    # List to store results to be saved
    error_messages = []

    # Check if player_data is being loaded correctly
    print(f"🔹 Loaded player data: {player_data}")
    print(f"🔹 Loaded song info keys: {list(song_info.keys())}")  # Print all available instruments in song_info

    # Normalize instrument names in song_info for case-insensitive matching
    normalized_song_info = {
        k.lower(): {song.lower().strip(): v for song, v in v.items()} for k, v in song_info.items()
    }

    # Loop through all players in player_data
    for user_id, user_data in player_data.items():
        username = user_data.get("username", "Unknown User")
        print(f"🔹 Processing player: {username} (User ID: {user_id})")

        # Normalize instrument names in player data for consistent lookup
        normalized_player_data = {k.lower(): v for k, v in user_data.items() if isinstance(v, dict)}

        # Loop through all instruments for this player
        for player_instrument, instrument_data in normalized_player_data.items():
            instrument_key = player_instrument.lower()  # Normalize player instrument name

            if "songs" in instrument_data:
                song_found = False  # Ensure it's defined

                # Debug log for songs the player has played
                print(f"🎵 {username} played songs in {player_instrument}: {list(instrument_data['songs'].keys())}")

                # Ensure the instrument exists in song_info
                if instrument_key not in normalized_song_info:
                    print(f"❌ Instrument '{player_instrument}' not found in song_info.")
                    continue  # Skip if the instrument is missing

                # Get the available songs for this instrument
                available_songs = normalized_song_info[instrument_key]
                print(f"✅ Available songs for {player_instrument}: {list(available_songs.keys())}")  # Debugging

                # Prepare a dictionary for the instrument to store song scores
                instrument_scores = {}

                # Loop through all songs the player has played
                for song_name, normalized_score in instrument_data["songs"].items():
                    song_key = song_name.lower().strip()  # Normalize player song name

                    if song_key in available_songs:
                        song_data = available_songs[song_key]
                        song_found = True  # Found the song for the instrument

                        print(f"✅ Found song '{song_name}' for player {username} in {player_instrument}")

                        # Check if 'difficulty' and 'total_notes' exist in the song data
                        if "difficulty" not in song_data or "total_notes" not in song_data:
                            print(f"⚠️ Missing difficulty/total_notes for '{song_name}' in {player_instrument}. Full data: {song_data}")
                            error_messages.append(f"Skipping song {song_name} due to missing data (difficulty/total_notes).")
                            continue  # Skip this song if the required data is missing

                        difficulty = song_data["difficulty"]
                        total_notes = song_data["total_notes"]

                        # Assume missed and striked notes are 0
                        missed_notes = 0
                        striked_notes = 0

                        # Calculate Perfect and Good notes
                        try:
                            P, G = calculate_perfect_good(
                                S=normalized_score, 
                                D=difficulty, 
                                M=missed_notes, 
                                R=striked_notes, 
                                total_notes=total_notes, 
                                W_p=WEIGHTS["perfect"], 
                                W_g=WEIGHTS["good"], 
                                W_m=WEIGHTS["missed"], 
                                W_s=WEIGHTS["striked"]
                            )

                            # Store the new score in the player's instrument
                            instrument_scores[song_name] = calculate_normalized_score(P, G, missed_notes, striked_notes, difficulty)

                        except ValueError as e:
                            error_messages.append(f"⚠️ Error for {username} in {song_name}: {str(e)}")
                            continue

                # If songs were found and processed, update the player's data with new instrument scores
                if song_found:
                    user_data[player_instrument] = {
                        "songs": instrument_scores
                    }

                # Log if no matching song was found for an instrument
                if not song_found:
                    print(f"❌ No matching song found for player {username} in {player_instrument}.")

    # If no results for any players
    if not error_messages:
        print("❌ No errors encountered.")
    
    # Save the updated player data
    save_player_data(player_data)

    # Send any error messages
    if error_messages:
        await interaction.response.send_message("\n".join(error_messages))
        return

    # Optionally, you can inform the user that the results are saved
    await interaction.response.send_message("Player scores have been updated.")

# Run the bot
bot.run(bot_token)
