# @author: stephen

import fire
import json
from library.java_parser import JavaParser
from library.repo_java_parser import RepoJavaParser
from library.action_trace import ActionTraces, RecentActions


def fetch_recent_traces(size: int = 10, path: str = None) -> None:
    actions = RecentActions(size, path=path)
    actions.print_recent_actions()


def trace(action: str) -> str:
    parser = ActionTraces(action)
    return str(parser)


def parse_file(file_path: str) -> str:
    parser = JavaParser(file_path)
    return str(parser.result)


def parse_repo(repo_path: str, reparse: bool = False, output_path: str = None) -> str:
    parser = RepoJavaParser(repo_path, reparse, output_path)
    return "Parsed repository successfully: " + str(parser.output_path)


def find_reference(repo_path: str, package: str, class_name: str) -> list[str]:
    parser = RepoJavaParser(repo_path)
    rsts = parser.find_references(package, class_name)
    return [rst.path for rst in rsts]


def merge_library_and_example_qa_result(library_qa_path: str = "library-source-code-to-qa.jsonl", example_qa_path: str = "example-repo-action-to-qa.jsonl", output_qa_path: str = "train.jsonl") -> None:
    with open(library_qa_path, 'r', encoding='utf-8') as lib_file:
        lib_qa = json.load(lib_file)

    with open(example_qa_path, 'r', encoding='utf-8') as ex_file:
        exm_qa = json.load(ex_file)

    merged_qa = lib_qa + exm_qa

    with open(output_qa_path, 'w', encoding='utf-8') as out_file:
        for qa in merged_qa:
            rst = {"prompt": qa['query'], "completion": qa['response']}
            out_file.write(json.dumps(rst, ensure_ascii=False) + '\n')

    print(f"Merged {len(lib_qa)} library QA entries and {len(exm_qa)} example QA entries into {output_qa_path}")


def merge_wiki_to_jsonl(wiki_qa_path: str = "../train-wiki.jsonl", original_qa_path: str = "train.jsonl", output_qa_path: str = "../train-v2.jsonl") -> None:
    merged_qa = []
    wiki_count = 0
    original_count = 0

    with open(wiki_qa_path, 'r', encoding='utf-8') as wiki_fd:
        for line in wiki_fd:
            data = json.loads(line)
            j = {"prompt": data['messages'][1]["content"], "completion": data['messages'][2]["content"]}
            merged_qa.append(j)
            wiki_count += 1

    with open(original_qa_path, 'r', encoding='utf-8') as original_fd:
        for line in original_fd:
            merged_qa.append(json.loads(line))
            original_count += 1

    with open(output_qa_path, 'w', encoding='utf-8') as out_file:
        for entry in merged_qa:
            out_file.write(json.dumps(entry, ensure_ascii=False) + '\n')


    print(f"Merged {wiki_count} wiki QA entries and {original_count} original QA entries into {output_qa_path}")


CORE_NG_CODING_SYSTEM_PROMPT = """You are a helpful coding assistant. Your task is to assist with coding-related questions and tasks. Please provide clear and concise answers, and if necessary, write code snippets in a format that is easy to understand and execute."""

def change_text_generation_format_to_chat_completion_format(input_path: str, output_path: str, system_prompt: str = CORE_NG_CODING_SYSTEM_PROMPT) -> None:
    data = []
    with open(input_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.readlines()
        for line in lines:
            j = json.loads(line)
            chat = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": j["prompt"]}, {"role": "assistant", "content": j["completion"]}]}
            data.append(chat)
    with open(output_path, 'w', encoding='utf-8') as output_file:
        for entry in data:
            output_file.write(json.dumps(entry, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    fire.Fire({
        "repo": parse_repo,
        "file": parse_file,
        "find": find_reference,
        "trace": trace,
        "recent": fetch_recent_traces,
        "merge": merge_library_and_example_qa_result,
        "mergev2": merge_wiki_to_jsonl,
        "change_format": change_text_generation_format_to_chat_completion_format
    })