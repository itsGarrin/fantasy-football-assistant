import json
import os

import nfl_data_py as nfl
import yaml
from dotenv import load_dotenv
from ollama import ChatResponse
from ollama import chat
from openai import OpenAI

from tools.fantasycalc import get_value
from tools.nflstats import get_nfl_stats
from tools.sleeper import get_player_projected_points
from tools.sleeper import get_player_total_projected_points

# TODO:
# presentation, streamlit app
# get benchmarking working 
# ideas, average stats out in the past few game, 
# give llm the future schedule with projected points and schedule difficulty

load_dotenv()

stats = nfl.import_weekly_data([2024])
ids = nfl.import_ids()


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
    'get_player_projected_points': get_player_projected_points,
    'get_player_total_projected_points': get_player_total_projected_points
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
        response = self.run_openai(user_input, verbose)
        print(user_input, "\n")
        print("Expected: " + expected_output, " Acutal: " + response, expected_output.upper() in response.upper())
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
nfl_agent.test_interface("can you compare travis etienne to bucky irving?", "no", verbose=True)


# different prompts for 
#  

# TODO:
# have two gpts, one that has a different prompt about tooling, and another that has a different prompt about the nfl
# future schedule with projected points and schedule difficulty
