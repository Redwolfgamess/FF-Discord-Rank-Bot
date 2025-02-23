import os
import discord
import json
from constants import INSTRUMENT_THRESHOLDS

from ranking_utils import determine_rank, calculate_final_rank, calculate_named_rank

from config import bot

# {
#     "{PLAYER ID}": { 
#         "username": "{USERNAME}", 
#         "{INSTUMENT}": { 
#             "songs": {
#                 "{SONG NAME}": {SCORE} 
#             }
# }

PLAYER_DATA_FILE = "player_data.json"
SONG_INFO_DATA_FILE = "song_info.json"
def load_player_data():
    try:
        if os.path.exists(PLAYER_DATA_FILE) and os.path.getsize(PLAYER_DATA_FILE) > 0:
            with open(PLAYER_DATA_FILE, "r") as file:
                return json.load(file)
        else:
            return {}
    except json.JSONDecodeError:
        return {}

def load_song_info():
    try:
        if os.path.exists(SONG_INFO_DATA_FILE) and os.path.getsize(SONG_INFO_DATA_FILE) > 0:
            with open(SONG_INFO_DATA_FILE, "r") as file:
                return json.load(file)
        else:
            return {}
    except json.JSONDecodeError:
        return {}
    
def save_song_info(song_info):
    with open(SONG_INFO_DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(song_info, file, indent=4)

async def save_data(player_id, username, instrument, song_name, score):
    from discord_utils import assign_role
    try:
        # Load existing data
        data = load_player_data()

        # Initialize player data if not present
        if player_id not in data:
            data[player_id] = {
                "username": username,
                instrument: {
                    "songs": {},
                    "final_rank_score": 0,
                    "rank": "Bronze",
                    "named_rank": "Bronze"
                }
            }

        # Initialize instrument data if missing
        if instrument not in data[player_id]:
            data[player_id][instrument] = {
                "songs": {},
                "final_rank_score": 0,
                "rank": "Bronze",
                "named_rank": "Bronze"
            }

        # Update the best score for the song
        instrument_data = data[player_id][instrument]
        best_scores = instrument_data["songs"]
        # Load song info to get correct capitalization
        song_info = load_song_info()

        # Find the correct capitalization from the JSON
        correct_song_name = next(
            (key for instrument_songs in song_info.values() for key in instrument_songs if key.lower() == song_name.lower()), 
            song_name
        )
        current_score = best_scores.get(correct_song_name, 0)
        if score > current_score:
            best_scores[correct_song_name] = score


        # Update final rank score and rank for the submitted instrument
        scores = list(best_scores.values())
        instrument_data["final_rank_score"] = calculate_final_rank(scores)
        instrument_data["rank"] = determine_rank(instrument_data["final_rank_score"], instrument)

        # Cycle through all instruments to update named rank
        for instr in INSTRUMENT_THRESHOLDS.keys():
            if instr in data[player_id]:
                scores = list(data[player_id][instr]["songs"].values())
                data[player_id][instr]["named_rank"] = calculate_named_rank(scores, instr)

        # Role assignment logic
        guild = discord.utils.find(lambda g: g.get_member(int(player_id)), bot.guilds)
        if guild:
            member = guild.get_member(int(player_id))
            if member:
                await assign_role(member, instrument, instrument_data["named_rank"])

        # Save updated data
        with open(PLAYER_DATA_FILE, "w") as file:
            json.dump(data, file, indent=4)

    except Exception as e:
        print(f"Error saving data: {e}")

async def update_player_data(player_id, song_name, instrument, score, accept=True):
    """Updates the player data JSON file with the new score if accepted, otherwise does nothing."""
    # Ensure the file exists
    if not os.path.exists(PLAYER_DATA_FILE):
        with open(PLAYER_DATA_FILE, "w") as f:
            json.dump({}, f, indent=4)

    # Load existing data
    with open(PLAYER_DATA_FILE, "r") as f:
        player_data = json.load(f)

    if accept:
        # Ensure player data exists
        if player_id not in player_data:
            player_data[player_id] = {"username": "Unknown", instrument: {"songs": {}}}

        # Ensure instrument exists
        if instrument not in player_data[player_id]:
            player_data[player_id][instrument] = {"songs": {}}

        # Update score for the song
        player_data[player_id][instrument]["songs"][song_name] = score

        # Save changes
        with open(PLAYER_DATA_FILE, "w") as f:
            json.dump(player_data, f, indent=4)
