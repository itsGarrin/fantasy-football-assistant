import os

import nfl_data_py as nfl
import pandas as pd

import tools.utils as utils

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
    sleeper_id = utils.convert_player_name_to_sleeper_id(player_name)
    
    # read from csv file python
    # df = pd.read_csv(f'fantasy_calc_rankings/{self.league_type_string}_{self.ppr_value}_{self.league_size}.csv', sep=';')
    file_path = os.path.join(os.path.dirname(__file__), '..', 'fantasy_calc_rankings', 'fantasycalc_redraft_rankings.csv')
    df = pd.read_csv(file_path, sep=';')
    df = df[df['sleeperId'] == sleeper_id]

    if df.empty:
        return "The value of " + player_name + " is either not available or equal to 0."

    # get the value and overallRank from the df
    value = df['value'].iloc[0]
    overallRank = df['overallRank'].iloc[0]

    return "The value of " + player_name + " is " + str(value) + " which is ranked " + str(overallRank) + " at their position."


get_value_tool = {
    'type': 'function',
    'function': {
        'name': 'get_value',
        'description': 'Get the value of a player',
        'parameters': {
            'type': 'object',
            'required': ['player_name'],
            'properties': {
                'player_name': {'type': 'string', 'description': 'The name of the player'},
            },
        },
    },
}