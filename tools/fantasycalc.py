import nfl_data_py as nfl
import utils

stats = nfl.import_weekly_data([2024])
ids = nfl.import_ids()

def get_value(player_name: str) -> str:
    """
    Gets the value of a fantasy football player, from fantasycalc.com

    Args:
      player_name (str): The name of the player

    Returns:
       int: The value of a player ranging from 0-10000
    """
    player_name = utils.convert_player_name(player_name)
    try:
        sleeper_id = ids[ids["name"] == player_name]["sleeper_id"].iloc[0]
    except IndexError:
        return "The value of " + player_name + " is either not available or equal to 0."

    # read from csv file python
    # df = pd.read_csv(f'fantasy_calc_rankings/{self.league_type_string}_{self.ppr_value}_{self.league_size}.csv', sep=';')
    df = pd.read_csv('../fantasy_calc_rankings/fantasycalc_redraft_rankings.csv', sep=';')
    df = df[df['sleeperId'] == sleeper_id]

    if df.empty:
        return "The value of " + player_name + " is either not available or equal to 0."
        return player_name + " not found"

    # get the value and overallRank from the df
    value = df['value'].iloc[0]
    overallRank = df['overallRank'].iloc[0]

    return "The value of " + player_name + " is " + str(value) + " which is ranked " + str(overallRank) + " at their position."
