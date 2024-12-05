from ollama import chat
from ollama import ChatResponse
import pandas as pd
import json
import nfl_data_py as nfl
from openai import OpenAI
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import yaml
# TODO:
# presentation, streamlit app
# get benchmarking working 
# ideas, average stats out in the past few game, 
# give llm the future schedule with projected points and schedule difficulty

load_dotenv()

stats = nfl.import_weekly_data([2024])
ids = nfl.import_ids()

def convert_player_name(player_name: str) -> str:
    all_players_list = stats["player_display_name"].unique().tolist()

    scores = process.extract(player_name, all_players_list, scorer=fuzz.token_set_ratio, limit=5)


    print(scores[0], scores[1])

    # if the similarity score is greater than 80, return the player name
    if scores[0][1] > 60:
        return scores[0][0]
    else:
        return player_name


def get_value(player_name: str) -> str:
    """
    Gets the value of a fantasy football player, from fantasycalc.com

    Args:
      player_name (str): The name of the player

    Returns:
       int: The value of a player ranging from 0-10000
    """
    player_name = convert_player_name(player_name)
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

def get_nfl_stats(player_name: str) -> str:
    """
    Gets the stats for the last n games of a player

    Args:
        player_name (str): The name of the player

    Returns:
        str: The stats for the player
    """
    player_name = convert_player_name(player_name)

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


SYSTEM_PROMPT = """
You are a knowledgeable fantasy football assistant. When making decisions, do not use outside data, instead use the tools provided.
Try to provide specific information about the players such as their value, stats, etc. 
For any players a user asks about, you should call both the get_value and get_nfl_stats tools.

If you can't find a player or are unsure of who they mean, ask the user for clarification on the name of the player.
Always answer the user's question to the best of your ability.
"""

available_functions = {
  'get_value': get_value,
  'get_nfl_stats': get_nfl_stats,
}

get_nfl_stats_tool = {
    'type': 'function',
    'function': {
        'name': 'get_nfl_stats',
        'description': 'Get the stats for a player',
        'parameters': {
            'type': 'object',
            'required': ['player_name'],
            'properties': {
                'player_name': {'type': 'string', 'description': 'The name of the player'},
            },
        },
    },
}

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

class NFLAgent:
    def __init__(self):
        self.messages = [{
                            'role': 'system',
                            'content': SYSTEM_PROMPT,
                            }]
        
    def run(self, prompt, verbose=False):
        self.messages.append({'role': 'user', 'content': prompt})
        response: ChatResponse = chat(
            model='llama3.1',
            messages=self.messages,
            tools=[get_value, get_nfl_stats],
        )

        if response.message.tool_calls:
            # There may be multiple tool calls in the response
            for tool in response.message.tool_calls:
                # Ensure the function is available, and then call it
                if function_to_call := available_functions.get(tool.function.name):
                    output = function_to_call(**tool.function.arguments)
                    if verbose:
                        print('Calling function:', tool.function.name)
                        print('Arguments:', tool.function.arguments)
                        print('Function output:', output)
                    self.messages.append({'role': 'tool', 'content': str(output), 'name': tool.function.name})
                else:
                    print('Function', tool.function.name, 'not found')

        if verbose:    
            print(self.messages)

        # Get final response from model with function outputs
        final_response = chat('llama3.1', messages=self.messages, tools=[get_value, get_nfl_stats])
        self.messages.append({'role': 'system', 'content': final_response.message.content})
        if verbose:
            print('Final response:', final_response.message.content)
        return final_response.message.content
    
    def run_openai(self, prompt, verbose=False):
        self.messages.append({'role': 'user', 'content': prompt})
        client = OpenAI(base_url=os.getenv("OLLAMA_URL"), api_key=os.getenv("KEY"))
        response = client.chat.completions.create(
            model="llama3.1",
            messages=self.messages,
            tools=[get_value_tool, get_nfl_stats_tool],
        )

        if response.choices[0].message.tool_calls:
            for tool in response.choices[0].message.tool_calls:
                if function_to_call := available_functions.get(tool.function.name):
                    output = function_to_call(**json.loads(tool.function.arguments))
                    if verbose:
                        print('Calling function:', tool.function.name)
                        print('Arguments:', tool.function.arguments)
                        print('Function output:', output)
                    self.messages.append({'role': 'tool', 'content': str(output), 'name': tool.function.name})
                else:
                    print('Function', tool.function.name, 'not found')
        if verbose:
            print(self.messages)

        final_response = client.chat.completions.create(
            temperature=0.85,
            model="llama3.1",
            messages=self.messages,
            tools=[get_value_tool, get_nfl_stats_tool])
        self.messages.append({'role': 'system', 'content': final_response.choices[0].message.content})
        if verbose:
            print('Final response:', final_response.choices[0].message.content)

        return final_response.choices[0].message.content
    
    def reset(self):
        self.messages = [{
                            'role': 'system',
                            'content': SYSTEM_PROMPT,
                            }]
        
    def test_interface(self, user_input, expected_output, verbose=False):
        response = self.run(user_input, verbose)
        print(user_input, "\n")
        print("Expected: " + expected_output, " Actual: " + response, expected_output.upper() in response.upper())
        print("\n")
        self.reset()
        return expected_output.upper() in response.upper()
    

nfl_agent = NFLAgent()
# nfl_agent.run_openai("Should I start Tyreek Hill or a kicker this week? You must respond with only one word, either 'Hill' or 'kicker'")

def load_benchmark(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# benchmark_file = '../benchmarking/benchmark.yaml'
# benchmark_data = load_benchmark(benchmark_file)

client = OpenAI(base_url=os.getenv("URL"), api_key=os.getenv("KEY"))

def basic_llama(input, expected_answer):
    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        messages=[
            {"role": "user", "content": input},
        ],
    )

    print(expected_answer, response.choices[0].message.content, expected_answer.upper() in response.choices[0].message.content.upper())

    return expected_answer.upper() in response.choices[0].message.content.upper()

def calculate_accuracy(benchmark_data, test_func):
    total_questions = 0
    correct_answers = 0

    for category, qa_pairs in benchmark_data.items():
        for qa in qa_pairs:
            user_input = qa['question']
            expected_answer = qa['answer']
            result = test_func(user_input, expected_answer)
            if result:
                correct_answers += 1
            total_questions += 1

    accuracy = (correct_answers / total_questions) * 100
    return accuracy

# print(calculate_accuracy(benchmark_data, basic_llama))
# print(calculate_accuracy(benchmark_data, nfl_agent.test_interface))
nfl_agent.test_interface("Should I start dionate johnson or brian thomas jr next week?", "no", verbose=True)


# different prompts for 
#  

# TODO:
# have two gpts, one that has a different prompt about tooling, and another that has a different prompt about the nfl
# future schedule with projected points and schedule difficulty



# start doing few shot prompting? 