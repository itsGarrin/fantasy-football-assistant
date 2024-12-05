import nfl_data_py as nfl
from fuzzywuzzy import process, fuzz

stats = nfl.import_weekly_data([2024])

def convert_player_name(player_name: str) -> str:
    all_players_list = stats["player_display_name"].unique().tolist()

    scores = process.extract(player_name, all_players_list, scorer=fuzz.token_set_ratio, limit=5)


    print(scores[0], scores[1])

    # if the similarity score is greater than 80, return the player name
    if scores[0][1] > 50:
        return scores[0][0]
    else:
        return player_name
    

def convert_player_name_to_sleeper_id(player_name: str) -> int:
    ids = nfl.import_ids()
    player_name = convert_player_name(player_name)
    try:
        sleeper_id = ids[ids["name"] == player_name]["sleeper_id"].iloc[0]
    except IndexError:
        return "The value of " + player_name + " is either not available or equal to 0."

    return int(sleeper_id)

def convert_scoring_type_to_text(scoring_type: int) -> str:
    if scoring_type == 1:
        return "ppr"
    elif scoring_type == 0.5:
        return "half_ppr"
    else:
        return "std"