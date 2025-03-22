from discord import app_commands

# Constants for rank calculation
WEIGHTS = {
    "perfect": 1.0,
    "good": 0.5,
    "missed": -0.5, # ___________
    "striked": -0.75 #Swap around?
}

DECAY_RATE = 0.95  # Decay rate for weighted ranks
TOP_PERFORMANCES = 100  
NAMED_RANK_TOP_PERFORMANCES = 5 #Maybe change to 10
GUILD_ID = 1315452784837132308

INSTRUMENTS = [
    "Lead",
    "Vocals",
    "Drums",
    "Bass",
    "Pro Lead",
    "Pro Bass"
]

# Rank Thresholds for final rank score
RANK_THRESHOLDS = {
    "Top 50": 100000,
    "Unreal": 50000,
    "Champion": 30000,
    "Diamond": 25000,
    "Gold": 17500,
    "Silver": 10000,
    "Bronze": 0,
}
#---------------------NAMED RANK THRESHOLDS------------------
# Rank Threshold for Lead
LEAD_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
}
# Rank Threshold for Drums
DRUMS_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
}
# Rank Threshold for Vocals
VOCALS_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
}
# Rank Threshold for Bass
BASS_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
}
# Rank Threshold for Bass
PRO_LEAD_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
    
}# Rank Threshold for Bass
PRO_BASS_RANK_THRESHOLDS = {
    "Top 50": 700, 
    "Unreal": 650,
    "Champion": 600 ,
    "Diamond": 500,
    "Gold": 400,
    "Silver": 300,
    "Bronze": 0,
}
# All instrument rank thresholds to be cycled through
INSTRUMENT_THRESHOLDS = {
    "lead": LEAD_RANK_THRESHOLDS,
    "drums": DRUMS_RANK_THRESHOLDS,
    "vocals": VOCALS_RANK_THRESHOLDS,
    "bass": BASS_RANK_THRESHOLDS,
    "pro lead": PRO_LEAD_RANK_THRESHOLDS,
    "pro bass": PRO_BASS_RANK_THRESHOLDS
}
#---------------------ACCURACY RANK THRESHOLDS------------------
ACCURACY_LEAD_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,
}
# Rank Threshold for Drums
ACCURACY_DRUMS_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,
}
# Rank Threshold for Vocals
ACCURACY_VOCALS_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,
}
# Rank Threshold for Bass
ACCURACY_BASS_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,
}
# Rank Threshold for Bass
ACCURACY_PRO_LEAD_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,   
}
# Rank Threshold for Bass
ACCURACY_PRO_BASS_RANK_THRESHOLDS = {
    "Top 50": 95, 
    "Unreal": 90,
    "Champion": 80,
    "Diamond": 70,
    "Gold": 60,
    "Silver": 50,
    "Bronze": 0,
}
# All instrument rank thresholds to be cycled through
ACCURACY_INSTRUMENT_THRESHOLDS = {
    "lead": LEAD_RANK_THRESHOLDS,
    "drums": DRUMS_RANK_THRESHOLDS,
    "vocals": VOCALS_RANK_THRESHOLDS,
    "bass": BASS_RANK_THRESHOLDS,
    "pro lead": PRO_LEAD_RANK_THRESHOLDS,
    "pro bass": PRO_BASS_RANK_THRESHOLDS
}

# Define instrument choices
INSTRUMENT_CHOICES = [
    app_commands.Choice(name="Lead", value="lead"),
    app_commands.Choice(name="Drums", value="drums"),
    app_commands.Choice(name="Vocals", value="vocals"),
    app_commands.Choice(name="Bass", value="bass"),
    app_commands.Choice(name="Pro Lead", value="pro lead"),
    app_commands.Choice(name="Pro Bass", value="pro bass"),
]

RANK_EMOJI = {
    "unreal": "<:UnrealIcon:1337238244152311858>",
    "champion": "<:Champion:1317635496708542597>",
    "diamond": "<:Diamond:1317635539184386159>",
    "platinum": "<:Platinum:1317635554757705769>",
    "gold": "<:Gold:1317635568103981076>",
    "silver": "<:Silver:1317635576911892713>",
    "bronze": "<:Bronze:1317635586391150603>"
}

RANK_PRIORITY = ["Top 50", "Unreal", "Champion", "Diamond", "Gold", "Silver", "Bronze"]

STATUS_CHANNEL_NAMES = ["bot-status", "🟢bot-status", "🔴bot-status"]