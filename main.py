import nfl_data_py as nfl
import json
import datetime
import re
from enum import Enum
import pandas as pd
import os
from openai import OpenAI

SYSTEM_PROMPT = """
You are a helpful fantasy football assisant. You have access to the latest NFL stats and rankings. 
For each query, return a list of tools you want to use to answer the user's question. The list can be empty.
You will receive the answers from 'System', and they will be in a list

Never suppose your knowledge is up-to-date, always use the tools to confirm.

Available functions are:
- get_value: Gets a value of a player, ranging from 0 to 100000. Example: {"function":"get_value","player_name":"Joe Mixon"}</s> returns {"value":1000}
- get_stats: Gets the up to date stats of a player for the last x weeks Example: {"function":"get_stats","player_name":"Joe Mixon", "last_x_weeks":4}</s> returns {"yards":100,"points":20}
- say: Answer to the user {"function":"say","message":"Sample sentence"}</s>
- end: End the conversation. Example: {"function":"end"}</s>

Example:
User: should I start Joe Mixon or Nick Chubb?
Assistant: [{"function":"get_value","player_name":"Joe Mixon"}, {"function":"get_value","player_name":"Nick Chubb"}, {"function":"get_stats","player_name":"Joe Mixon", "last_x_weeks":4}, {"function":"get_stats","player_name":"Nick Chubb", "last_x_weeks":4}]
System: [{"value":1000},{"value":2000}, {"yards":100,"points":20}, {"yards":200,"points":30}]
"""

TOOL_PROMPT = """
You are an agent helping another agent be a successful fantasy football assistant. 
Your job is to take a user's prompt and respond with a list of tools that the assistant should use to answer the user's question. The list can be empty.

<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You have access to the following functions:

Use the function 'spotify_trending_songs' to: Get top trending songs on Spotify
{"name": "spotify_trending_songs", "description": "Get top trending songs on Spotify", "parameters": {"n": {"param_type": "int", "description": "Number of trending songs to get", "required": true}}}


If a you choose to call a function ONLY reply in the following format:
<{start_tag}={function_name}>{parameters}{end_tag}
where

start_tag => `<function`
parameters => a JSON dict with the function argument name as key and function argument value as value.
end_tag => `</function>`

Here is an example,
<function=example_function_name>{"example_name": "example_value"}</function>

Reminder:
- Function calls MUST follow the specified format
- Required parameters MUST be specified
- Put the entire function call reply on one line
- Each function should be on a separate line
"""

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
        self.client = OpenAI(base_url=os.getenv("URL"), api_key=os.getenv("KEY"))
        self.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

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
        # df = pd.read_csv(f'fantasy_calc_rankings/{self.league_type_string}_{self.ppr_value}_{self.league_size}.csv', sep=';')
        df = pd.read_csv('fantasy_calc_rankings/fantasycalc_redraft_rankings.csv', sep=';')
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

        self.client.beta.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct",
            messages=self.conversation,
            tools
        )

        self.client.chat.completions.create(
        messages = self.conversation,
        model = "meta-llama/Meta-Llama-3.1-8B-Instruct",
        temperature=0)

        self.client.beta.assistants.create(
            instructions="You are a fantasy football bot. Use the provided tools to answer the user's question.",
            model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        )
        if verbose:
            print(build_prompt)

        return build_prompt

    def test_interface(self, prompt: str, answer: str):
        res = self.build_prompt(prompt, verbose=False)
        return res == answer


nfl_interface = NFLInterface()
nfl_interface.test_interface()