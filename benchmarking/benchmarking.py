import yaml

from main import NFLInterface


def load_benchmark(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def print_benchmark(benchmark_data):
    for category, qa_pairs in benchmark_data.items():
        print(f"Category: {category}")
        for qa in qa_pairs:
            print(f"  Q: {qa['question']}")
            print(f"  A: {qa['answer']}")
        print()

if __name__ == "__main__":
    benchmark_file = 'benchmarking/benchmark.yaml'
    benchmark_data = load_benchmark(benchmark_file)
    print_benchmark(benchmark_data)

    nfl_interface = NFLInterface()
    for category, qa_pairs in benchmark_data.items():
        for qa in qa_pairs:
            user_input = qa['question']
            res = nfl_interface.test_interface(qa['question'], qa['answer'], verbose=False)
            print(res)
            print(f"Expected Answer: {qa['answer']}")
            print()