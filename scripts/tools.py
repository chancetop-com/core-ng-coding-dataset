# @author: stephen

import fire
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


if __name__ == "__main__":
    fire.Fire({
        "repo": parse_repo,
        "file": parse_file,
        "find": find_reference,
        "trace": trace,
        "recent": fetch_recent_traces
    })