import discord
from discord import app_commands
from discord.ui import Button, View
from json_utils import update_player_data
import re
from constants import RANK_PRIORITY

# Autocomplete function for usernames
async def username_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=member.name, value=member.name)
        for member in interaction.guild.members
        if current.lower() in member.name.lower()
    ][:25]  # Limit to 25 options per Discord's restrictions

async def song_name_autocomplete(interaction: discord.Interaction, current: str):
    from json_utils import load_song_info
    song_info = load_song_info()
    all_songs = {song for instrument in song_info.values() for song in instrument.keys()}  # Get all unique song names
    suggestions = [app_commands.Choice(name=song, value=song) for song in all_songs if current.lower() in song.lower()]
    return suggestions[:25]  # Discord limits autocomplete to 25 choices

async def get_average_rank(member):
    instrument_keywords = ["Lead", "Vocals", "Bass", "Drums", "Pro Lead", "Pro Bass"]

    instrument_ranks = {}  # Track ranks per instrument

    def clean_role_name(role_name):
        """Removes emoji prefixes and extra spaces from role names."""
        return re.sub(r"[\U0001F300-\U0001FAD6]", "", role_name).strip()  # Removes emoji

    for role in member.roles:
        role_name = clean_role_name(role.name)  # Normalize role name (remove emojis)
        for rank in RANK_PRIORITY:
            if rank in role_name:
                for instrument in instrument_keywords:
                    if instrument in role_name:
                        instrument_ranks[instrument] = rank  # Store rank per instrument
                        break

    if len(instrument_ranks) < 4:
        return None  # Not enough different instrument ranks

    # Determine the highest common rank across instruments
    for rank in RANK_PRIORITY:
        if rank in instrument_ranks.values():
            return rank

    return None

async def assign_role(member, instrument, named_rank):

    from json_utils import load_player_data
    # Load player data
    player_data = load_player_data().get(str(member.id), {})
    instrument_data = player_data.get(instrument, {})

    if not instrument_data or len(instrument_data["songs"]) < 4:
        print(f"{member.name} does not have enough scores for {instrument}. Role not assigned.")
        return

    # Define role names for the instrument (with emoji prefixes)
    role_name = {
        "lead": f"🎸Lead - {named_rank}",
        "vocals": f"🎤Vocals - {named_rank}",
        "bass": f"🎚️Bass - {named_rank}",
        "drums": f"🥁Drums - {named_rank}",
        "pro lead": f"🎸Pro Lead - {named_rank}",
        "pro bass": f"🎚️Pro Bass - {named_rank}",
    }.get(instrument.lower())

    if not role_name:
        return

    guild = member.guild
    role = discord.utils.get(guild.roles, name=role_name)

    if not role:
        print(f"Role '{role_name}' does not exist. Please ensure it is created beforehand.")
        return

    # Remove previous roles for the same instrument
    instrument_prefixes = {
        "lead": "🎸Lead",
        "vocals": "🎤Vocals",
        "bass": "🎚️Bass",
        "drums": "🥁Drums",
        "pro lead": "🎸Pro Lead",
        "pro bass": "🎚️Pro Bass",
    }

    instrument_prefix = instrument_prefixes.get(instrument.lower())

    if instrument_prefix:
        for existing_role in member.roles:
            if existing_role.name.startswith(instrument_prefix):
                await member.remove_roles(existing_role)

    # Assign the new instrument-specific role
    await member.add_roles(role)

    # Determine the user's overall rank and assign the role if applicable
    average_rank = await get_average_rank(member)
    if average_rank:
        overall_role_name = f"{average_rank}"
        overall_role = discord.utils.get(guild.roles, name=overall_role_name)

        if overall_role:
            # Remove existing overall rank roles before assigning the new one
            for existing_role in member.roles:
                if any(rank in existing_role.name for rank in RANK_PRIORITY):
                    await member.remove_roles(existing_role)

            await member.add_roles(overall_role)
        else:
            print(f"Role '{overall_role_name}' does not exist. Please ensure it is created beforehand.")


async def pending_scores(embed, guild, player_id, submitter_username, instrument, song_name, perfect, good, missed, striked):
    # Get the #pending-scores channel
    pending_scores_channel = discord.utils.get(guild.text_channels, name="pending-scores")

    if pending_scores_channel:
        # Convert values to integers
        perfect, good, missed, striked = map(int, (perfect, good, missed, striked))

        # Create accept and deny buttons
        class ScoreReviewView(View):
            def __init__(self):
                super().__init__(timeout=None)

            async def update_message(self, interaction: discord.Interaction, status: str, color: discord.Color, accept: bool):
                """Create a new embed to reflect the score's accepted/denied status."""
                await update_player_data(player_id, song_name, instrument, perfect, accept)

                original_embed = interaction.message.embeds[0]  # Get existing embed
                
                # Create a new embed with updated color and title
                updated_embed = discord.Embed(
                    title=f"{original_embed.title} ({status})",
                    description=original_embed.description,
                    color=color
                )

                # Copy over existing fields
                for field in original_embed.fields:
                    updated_embed.add_field(name=field.name, value=field.value, inline=field.inline)

                # Copy image if there was one
                if original_embed.image.url:
                    updated_embed.set_image(url=original_embed.image.url)

                # Disable all buttons
                for child in self.children:
                    child.disabled = True

                await interaction.message.edit(embed=updated_embed, view=self)
                await interaction.response.send_message(f"Score {status.lower()}!", ephemeral=True)

            @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
            async def accept_callback(self, interaction: discord.Interaction, button: Button):
                await self.update_message(interaction, "Accepted", discord.Color.green(), accept=True)

            @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
            async def deny_callback(self, interaction: discord.Interaction, button: Button):
                await self.update_message(interaction, "Denied", discord.Color.red(), accept=False)

        view = ScoreReviewView()

        # Add user info & score details to the embed
        embed.add_field(name="🆔 Player ID", value=f"`{player_id}`", inline=False)
        embed.add_field(name="👤 Submitted By", value=f"`{submitter_username}`", inline=False)
        embed.add_field(name="🎵 Song", value=f"`{song_name}`", inline=True)
        embed.add_field(name="🎸 Instrument", value=f"`{instrument}`", inline=True)
        embed.add_field(name="🎯 Entered Perfect Notes", value=f"`{perfect}`", inline=True)
        embed.add_field(name="👍 Entered Good Notes", value=f"`{good}`", inline=True)
        embed.add_field(name="❌ Entered Missed Notes", value=f"`{missed}`", inline=True)
        embed.add_field(name="⚠️ Entered Strikes", value=f"`{striked}`", inline=True)

        await pending_scores_channel.send(embed=embed, view=view)

    else:
        print("Error: #pending-scores channel not found")

