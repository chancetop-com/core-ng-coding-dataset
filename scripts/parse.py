import fire
from library.java_parser import JavaParser, JavaFieldParser
from library.repo_java_parser import RepoJavaParser


def parse_field(content: str) -> None:
    JavaFieldParser(content)


def parse_file(file_path: str) -> str:
    parser = JavaParser(file_path)
    imports = parser.get_method_body_imports("HTTPServer", "start")
    return str(parser.result)


def parse_repo(repo_path: str, reparse: bool = False, output_path: str = None) -> None:
    RepoJavaParser(repo_path, reparse, output_path)

if __name__ == "__main__":
    fire.Fire({
        "repo": parse_repo,
        "file": parse_file,
        "field": parse_field
    })