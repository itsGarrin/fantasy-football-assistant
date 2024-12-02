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

def calculate_accuracy(benchmark_data, nfl_interface):
    total_questions = 0
    correct_answers = 0

    for category, qa_pairs in benchmark_data.items():
        for qa in qa_pairs:
            user_input = qa['question']
            expected_answer = qa['answer']
            result = nfl_interface.test_interface(user_input, expected_answer)
            if result:
                correct_answers += 1
            total_questions += 1

    accuracy = (correct_answers / total_questions) * 100
    return accuracy

if __name__ == "__main__":
    benchmark_file = '../benchmarking/benchmark.yaml'
    benchmark_data = load_benchmark(benchmark_file)
    print_benchmark(benchmark_data)

    nfl_interface = NFLInterface()
    accuracy = calculate_accuracy(benchmark_data, nfl_interface)
    print(f"Accuracy: {accuracy:.2f}%")
