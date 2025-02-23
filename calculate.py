8071.0,


def calculate_perfect_good(S, D, M, R, total_notes, W_p, W_g, W_m, W_s):
    if W_g == W_p:
        raise ValueError("W_g and W_p cannot be the same, division by zero error!")

    numerator = (S / D) - (M * W_m) - (R * W_s) - ((total_notes - (M + R)) * W_p)
    denominator = W_g - W_p
    G = numerator / denominator
    P = total_notes - (M + R) - G

    return int(P), int(G)

# Example usage:
S = 6713.0  # Example normalized score - Get From player_data.json
D = 3       # Difficulty level - Get from song_info.json
M = 0      # Missed notes - Assume is 0
R = 0       # Striked notes - Assume is 0
total_notes = 737
W_p = 1.0  # Weight for perfect notes - Variable imported from constants WEIGHTS 
W_g = 0.5   # Weight for good notes
W_m = -0.5  # Weight for missed notes
W_s = -0.75  # Weight for striked notes

P, G = calculate_perfect_good(S, D, M, R, total_notes, W_p, W_g, W_m, W_s)
print(P, G)

# 1108 30