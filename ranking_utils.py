from constants import INSTRUMENT_THRESHOLDS, TOP_PERFORMANCES, DECAY_RATE, NAMED_RANK_TOP_PERFORMANCES, RANK_THRESHOLDS

def determine_rank(score, instrument=None):
    thresholds = INSTRUMENT_THRESHOLDS.get(instrument.lower(), RANK_THRESHOLDS) if instrument else RANK_THRESHOLDS
    for rank, threshold in thresholds.items():
        if score >= threshold:
            return rank
    return "Bronze"

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

def calculate_final_rank(scores):
    scores = sorted(scores, reverse=True)[:TOP_PERFORMANCES]
    weighted_scores = [score * (DECAY_RATE ** i) for i, score in enumerate(scores)]
    return sum(weighted_scores)

def calculate_named_rank(scores, instrument):
    scores = sorted(scores, reverse=True)[:NAMED_RANK_TOP_PERFORMANCES]
    average_top_5 = sum(scores) / len(scores) if scores else 0
    return determine_rank(average_top_5, instrument)

def get_user_instrument_data(username, instrument, data):
    for player_id, player_info in data.items():
        if player_info.get("username", "").lower() == username.lower():
            return player_info.get(instrument.lower())
    return None

def get_song_metadata(song_name, instrument, song_info):
    instrument_key = instrument.lower()
    song_key = song_name.lower().strip()
    
    if instrument_key in song_info and song_key in song_info[instrument_key]:
        return song_info[instrument_key][song_key]
    return None

def calculate_notes(score, song_metadata):
    if song_metadata:
        difficulty = song_metadata.get("difficulty", 1)
        total_notes = song_metadata.get("total_notes", 1)
        return reverse_normalized_score(score, 0, 0, difficulty, total_notes)
    return 0, 0  # Default values if metadata is missing

def reverse_normalized_score(normalized_score, missed, striked, difficulty, total_notes):
    if difficulty == 0 or total_notes == 0:
        return 0, 0  # Avoid division by zero
    
    # Compute the scaling factor
    scaling_factor = 1 + (total_notes ** 0.1) * 0.02

    # Calculate the perfect note count
    perfect_ratio = normalized_score / (scaling_factor * difficulty * 100)
    perfect = perfect_ratio * total_notes

    # Calculate the remaining good notes
    good = total_notes - (perfect + missed + striked)

    # Adjust rounding to prevent drift
    perfect = round(perfect)
    good = total_notes - (perfect + missed + striked)  # Ensures sum consistency

    perfect += 1
    good -= 1
    return perfect, good

