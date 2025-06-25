# @author: stephen

import fire
from library.action_trace import ActionTraces, ActionDocument
from library.repo_java_parser import RepoJavaParser


def fetch_trace_context(doc: ActionDocument, parser: RepoJavaParser):
    print(f"Processing document: {doc.app} - {doc.action} - {doc.context.get('controller')[0]}")
    print(f"=============================")

    controller = doc.get_context_controller()
    impl = parser.find(controller.get_package(), controller.get_class_name())
    app = parser.find_app_or_module_of_class(controller.get_package(), controller.get_class_name())
    interface = parser.find_class_interface(controller.get_package(), controller.get_class_name())
    method_references = impl.get_method_references(controller.get_class_name(), controller.get_method_name())

    print(f"\tFound file: {impl.path}")
    print(f"\tFound app file: {app.path}")
    print(f"\tFound web service file: {interface.path}")
    for f in method_references:
        print(f"\tFound web service method import files: {parser.find(f.package, f.class_name).path}")


def main(repo_path: str, action: str):
    trace = ActionTraces(action)
    parser = RepoJavaParser(repo_path)
    for doc in trace.walk(5):
        fetch_trace_context(doc, parser)

if __name__ == '__main__':
    fire.Fire(main)