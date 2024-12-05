import json
import os

import nfl_data_py as nfl
import yaml
from dotenv import load_dotenv
from ollama import ChatResponse
from ollama import chat
from openai import OpenAI

from tools.fantasycalc import get_value, get_value_tool
from tools.nflstats import get_nfl_stats, get_nfl_stats_tool
from tools.sleeper import get_player_projected_points, get_player_projected_points_tool
from tools.sleeper import get_player_total_projected_points
from scrapers.sleeper import get_league_info

# TODO:
# presentation, streamlit app
# get benchmarking working 
# ideas, average stats out in the past few game, 
# give llm the future schedule with projected points and schedule difficulty

load_dotenv()

stats = nfl.import_weekly_data([2024])
ids = nfl.import_ids()

TOOL_SYSTEM_PROMT = """
You are a bot whose job is to provide an LLM with the data it needs to make informed decisions about fantasy football. 
You are given a prompt and should call the appropriate tools to provide the necessary information.

Try to call as many tools as possible to provide the most amount of information to the LLM. 
Make sure the information is relevant to the prompt and the tools you are calling are appropriate for the task at hand.

It is currently week 14 of the 2024 NFL season. The league the user is in is a 12 team PPR league. 
There are 17 weeks in the fantasy season, and the playoffs are weeks 15,16,17.

For the get_player_projected_points tool, make sure to provide week numbers as a comma separated string, for example, "12,13,14".
"""


SYSTEM_PROMPT = """
You are a knowledgeable fantasy football assistant. You have been given a prompt and tools to help answer the user's question.

Always answer the user's question to the best of your ability.

Try to call as many tools as possible to provide the most amount of information to the LLM. 
Make sure the information is relevant to the prompt and the tools you are calling are appropriate for the task at hand.
For the get_player_projected_points tool, make sure to provide week numbers as a comma separated string, for example, "12,13,14".

It is currently week 14 of the 2024 NFL season. 

For each tool call, provide the information in a clear and concise manner. 

A player name is a string that contains the full name of the player. For example, "Christian McCaffrey" is a valid player name. Do not use "player1" or "every player" as player names, or any variables.
You can call tools as many times as you want.

A good fantasy performance is a performance that is above average for that player's position.

Use the Sleeper league information to provide context about the league the user is in. Always answer questions from the perspective of the users team.
"""
# Use the Sleeper league information to provide context about the league the user is in. Always give advice in the perspective of the user and their opponents.
SYSTEM_PROMPT += get_league_info()

available_functions = {
    'get_value': get_value,
    'get_nfl_stats': get_nfl_stats,
    'get_player_projected_points': get_player_projected_points,
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
            tools=[get_value, get_nfl_stats, get_player_projected_points],
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
        final_response = chat('llama3.1', messages=self.messages, tools=[get_value, get_nfl_stats, get_player_projected_points])
        self.messages.append({'role': 'system', 'content': final_response.message.content})
        if verbose:
            print('Final response:', final_response.message.content)
        return final_response.message.content
    
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
nfl_agent.run("Can you get me the stats in the last 2 games for each player on my team?", verbose=True)


# different prompts for 
#  

# TODO:
# have two gpts, one that has a different prompt about tooling, and another that has a different prompt about the nfl
# future schedule with projected points and schedule difficulty



# start doing few shot prompting? 