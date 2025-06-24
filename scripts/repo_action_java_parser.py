# @author: stephen

import fire
from library.action_trace import ActionTraces
from library.java_parser import file_name_to_class_name
from library.file_utils import search_java_file
from library.repo_java_parser import RepoJavaParser


def find_root_app_file(repo_path: str, filename: str) -> str:
    class_name = file_name_to_class_name(filename)

    def match(java_file):
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return (class_name in content and
                        ('extends App {' in content or 'extends Module {' in content))
        except Exception as e:
            print(f"Error reading file {java_file}: {e}")
            return False

    return search_java_file(repo_path, match)


def main(repo_path: str, action: str):
    trace = ActionTraces(action)
    root_doc = trace.get_root_doc()
    root_controller = root_doc.get_context_controller()

    parser = RepoJavaParser(repo_path)
    root_file_rst = parser.find(root_controller.get_package(), root_controller.get_class_name())
    if not root_file_rst:
        print(f"Error: Root file for action {action} not found.")
        return

    root_app_file = find_root_app_file(repo_path, root_controller.get_class_name())

    print(f"Found root file: {root_file_rst.path}")
    print(f"Found root app file: {root_app_file}")
    # print(f"Found root web service file: {root_web_service_file}")
    # for f in root_web_service_method_import_files:
    #     print(f"Found root web service method import files: {f}")
    # for f in root_method_import_files:
    #     print(f"Found root method import files: {f}")
    # for f in root_method_inject_files:
    #     print(f"Found root method inject files: {f}")


if __name__ == '__main__':
    fire.Fire(main)