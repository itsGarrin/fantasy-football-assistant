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