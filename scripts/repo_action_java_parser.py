# @author: stephen

import fire
from library.action_trace import ActionTraces
from library.repo_java_parser import RepoJavaParser


def main(repo_path: str, action: str):
    trace = ActionTraces(action)
    root_doc = trace.get_root_doc()
    root_controller = root_doc.get_context_controller()

    parser = RepoJavaParser(repo_path)
    root_rst = parser.find(root_controller.get_package(), root_controller.get_class_name())
    if not root_rst:
        print(f"Error: Root file for action {action} not found.")
        return

    root_app_rst = parser.find_app_or_module_of_class(root_controller.get_package(), root_controller.get_class_name())
    root_interface_rst = parser.find_class_interface(root_controller.get_package(), root_controller.get_class_name())
    root_method_references = root_rst.get_method_references(root_controller.get_class_name(), root_controller.get_method_name())

    print(f"Found root file: {root_rst.path}")
    print(f"Found root app file: {root_app_rst.path}")
    print(f"Found root web service file: {root_interface_rst.path}")
    for f in root_method_references:
        print(f"Found root web service method import files: {parser.find(f.package, f.class_name).path}")


if __name__ == '__main__':
    fire.Fire(main)