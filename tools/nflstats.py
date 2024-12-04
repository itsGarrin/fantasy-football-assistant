import json

import nfl_data_py as nfl

import utils

stats = nfl.import_weekly_data([2024])

def get_nfl_stats(player_name: str) -> str:
    """
    Gets the stats for the last n games of a player

    Args:
        player_name (str): The name of the player

    Returns:
        str: The stats for the player
    """
    player_name = utils.convert_player_name(player_name)

    player_stats = stats[stats["player_display_name"] == player_name]

    if player_stats.empty:
        return player_name + " not found"

    first_n_rows = player_stats.to_dict(orient='records')
    first_n_rows.reverse()
    first_n_rows = first_n_rows[:4]
    keys_to_keep = ['recent_team', 'position', 'week', 'opponent_team', 'fantasy_points', 'passing_yards', 'passing_tds', 'interceptions', 'rushing_yards', 'rushing_tds', 'receptions', 'receiving_yards', 'receiving_tds', 'fantasy_points_ppr']
    stats_string = '\n'
    stats_string += f'---------- Recent Stats for {player_name} ----------\n'
    for elem in first_n_rows:
        elem = {k: elem[k] for k in keys_to_keep}
        # remove keys that are equal to 0 or None
        keys_to_remove = [k for k, v in elem.items() if v == 0 or v is None]

        for key in keys_to_remove:
            if elem["position"] == "QB" and key in ["passing_yards", "passing_tds", "interceptions"]:
                continue
            if elem["position"] == "RB" and key in ["rushing_yards", "rushing_tds"]:
                continue
            if elem["position"] == "WR" and key in ["receiving_yards", "receiving_tds"]:
                continue
            if elem["position"] == "TE" and key in ["receiving_yards", "receiving_tds"]:
                continue
            elem.pop(key, None)
        stats_string += json.dumps(elem)
        stats_string += '\n'
    stats_string += '-----------------------------------------------\n'
    return stats_string
