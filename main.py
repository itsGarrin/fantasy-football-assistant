import nfl_data_py as nfl
import json
import datetime
import re
from enum import Enum
import pandas as pd

class LeagueType(Enum):
    REDRAFT = 1
    DYNASTY = 2

class NFLInterface:
    """
    NFL interface.
    """
    def __init__(self, league_type=LeagueType.REDRAFT, league_size=12, ppr_value=1):
        self.stats = nfl.import_weekly_data([2024])
        self.all_players_list = self.stats["player_display_name"].unique().tolist()
        self.league_type = league_type
        self.league_size = league_size
        self.ppr_value = ppr_value

        if self.league_type == LeagueType.REDRAFT:
            self.league_type_string = "redraft"
        elif self.league_type == LeagueType.DYNASTY:
            self.league_type_string = "dynasty"

        assert self.stats is not None
        assert self.all_players_list is not None

    # n_rows = number of previous weeks stats to give GPT
    def get_nfl_stats(self, player_name, n_rows=10):
        player_stats = self.stats[self.stats["player_display_name"] == player_name]
        first_n_rows = player_stats.to_dict(orient='records')
        first_n_rows.reverse()
        first_n_rows = first_n_rows[:n_rows]
        keys_to_remove = []
        stats_string = '\n'
        stats_string += f'---------- Recent Stats for {player_name} ----------\n'
        for elem in first_n_rows:
            for key in keys_to_remove:
                elem.pop(key, None)
            stats_string += json.dumps(elem)
            stats_string += '\n'
        stats_string += '-----------------------------------------------\n'
        return stats_string
    
    # gets a ranking of a player 
    def get_ranking(self, player_name):
        # read from csv file python
        df = pd.read_csv(f'fantasy_calc_rankings/{self.league_type_string}_{self.ppr_value}_{self.league_size}.csv', sep=';')
        df = df[df['name'] == player_name]

        # get the value and overallRank from the df
        value = df['value'].iloc[0]
        overallRank = df['overallRank'].iloc[0]

        return value, overallRank

    def find_player_name(self, user_prompt_text):
        pattern = r'\b(?:' + '|'.join(re.escape(name) for name in self.all_players_list) + r')\b'
        # Search for names in the prompt using the regex pattern, ignoring case
        matches = re.findall(pattern, user_prompt_text, flags=re.IGNORECASE)

        # Return names as they originally appear in the names list
        return [name for name in self.all_players_list if
                any(re.match(re.escape(name), match, re.IGNORECASE) for match in matches)]

    def build_prompt(self, user_input, verbose=False):

        # add context window, league team, opponent team etc
        # based on query, tell GPT if it needs tools it has a get_ranking and get_nfl_stats (and i can add a get_nfl_news)
        names_found = self.find_player_name(user_input)

        build_prompt = ""

        build_prompt += f"User question: {user_input}\n"
        # reddit_res = scrape_reddit(player_name=player_name, n_rows=10, subreddit_name='nfl')
        # build_prompt += reddit_res

        if verbose:
            print(build_prompt)

        return build_prompt

    def test_interface(self, prompt: str, answer: str):
        res = self.build_prompt(prompt, verbose=False)
        return res == answer


nfl_interface = NFLInterface()
nfl_interface.test_interface()