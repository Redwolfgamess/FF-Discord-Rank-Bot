import discord
from discord.ui import Button, View

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

class LeaderboardPaginationView(View):
    def __init__(self, players, instrument, page=0):
        super().__init__(timeout=120)
        self.players = players
        self.instrument = instrument
        self.page = page
        self.per_page = 10  # Players per page

        # Disable buttons if necessary
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.players) - 1) // self.per_page

    def generate_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        displayed_players = self.players[start:end]

        if not displayed_players:
            leaderboard_text = "No scores found."
        else:
            leaderboard_text = "\n".join([
                f"**{username}**: {score:.2f} ({song})\n**Perfect:** {perfect} | **Good:** {good}"
                for username, score, song, perfect, good in displayed_players
            ])

        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=f"Top player scores{' for ' + self.instrument if self.instrument else ''}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Top Players", value=leaderboard_text, inline=False)
        embed.set_footer(text=f"Page {self.page + 1} of {(len(self.players) - 1) // self.per_page + 1}")

        return embed

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        self.page -= 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.players) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.page += 1
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= (len(self.players) - 1) // self.per_page
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

# class PaginationView(View):
#     def __init__(self, missing_songs, total_songs_with_difficulty, songs_with_total_notes, page=0):
#         super().__init__(timeout=120)
#         self.missing_songs = missing_songs
#         self.page = page
#         self.total_songs_with_difficulty = total_songs_with_difficulty
#         self.songs_with_total_notes = songs_with_total_notes
#         self.per_page = 10  # Songs per page

#         # Disable previous button if on first page
#         self.previous_button.disabled = self.page == 0

#         # Disable next button if on last page
#         self.next_button.disabled = self.page >= (len(missing_songs) - 1) // self.per_page

#     def generate_embed(self):
#         percentage = (self.songs_with_total_notes / self.total_songs_with_difficulty) * 100 if self.total_songs_with_difficulty else 0

#         # Get 10 songs for the current page
#         start = self.page * self.per_page
#         end = start + self.per_page
#         displayed_songs = self.missing_songs[start:end]

#         missing_songs_text = "\n".join([f"🎵 {song} ({instrument})" for instrument, song in displayed_songs]) if displayed_songs else "✅ All songs have total notes!"

#         embed = discord.Embed(
#             title="📊 Total Notes Coverage",
#             description=f"**Total Songs with Difficulty Set:** {self.total_songs_with_difficulty}\n"
#                         f"**Songs with Total Notes:** {self.songs_with_total_notes}\n"
#                         f"**Coverage Percentage:** {percentage:.2f}%\n\n"
#                         f"**Missing Total Notes:**\n{missing_songs_text}",
#             color=discord.Color.blue()
#         )
#         embed.set_footer(text=f"Page {self.page + 1} of {(len(self.missing_songs) - 1) // self.per_page + 1}")
#         return embed

#     @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
#     async def previous_button(self, interaction: discord.Interaction, button: Button):
#         self.page -= 1
#         self.previous_button.disabled = self.page == 0
#         self.next_button.disabled = self.page >= (len(self.missing_songs) - 1) // self.per_page
#         await interaction.response.edit_message(embed=self.generate_embed(), view=self)

#     @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
#     async def next_button(self, interaction: discord.Interaction, button: Button):
#         self.page += 1
#         self.previous_button.disabled = self.page == 0
#         self.next_button.disabled = self.page >= (len(self.missing_songs) - 1) // self.per_page
#         await interaction.response.edit_message(embed=self.generate_embed(), view=self)