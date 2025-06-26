# @author: stephen

import fire
from library.action_trace import ActionTraces, ActionDocument, RecentActions
from library.repo_java_parser import RepoJavaParser


def fetch_api_context(doc: ActionDocument, parser: RepoJavaParser, debug: bool = False) -> list[str]:
    controller = doc.get_context_controller()
    impl = parser.find(controller.get_package(), controller.get_class_name())
    app = parser.find_app_or_module_of_class(controller.get_package(), controller.get_class_name())
    interface = parser.find_class_interface(controller.get_package(), controller.get_class_name())
    method_references = impl.get_method_references(controller.get_class_name(), controller.get_method_name())

    if debug:
        print(f"**Processing document: {doc.app} - {doc.action} - {doc.get_context_controller().controller}")
        print(f"    Found file: {impl.path}")
        print(f"    Found app file: {app.path}")
        print(f"    Found web service file: {interface.path}")
        for f in method_references:
            print(f"    Found method reference files: {parser.find(f.package, f.class_name).path}")

    return [impl.path, app.path, interface.path] + [parser.find(f.package, f.class_name).path for f in method_references]


def fetch_http_context(doc: ActionDocument, parser: RepoJavaParser, debug: bool = False) -> list[str]:
    controller = doc.get_context_controller()
    impl = parser.find(controller.get_package(), controller.get_class_name())
    references = impl.get_references()

    if debug:
        print(f"**Processing document: {doc.app} - {doc.action} - {doc.get_context_controller().controller}")
        print(f"    Found file: {impl.path}")
        for f in references:
            print(f"    Found reference file: {parser.find(f.package, f.class_name).path}")

    return [impl.path] + [parser.find(f.package, f.class_name).path for f in references]


def fetch_job_context(doc: ActionDocument, parser: RepoJavaParser, debug: bool = False) -> list[str]:

    job_class = doc.get_context_job_class()
    impl = parser.find(job_class.get_package(), job_class.get_class_name())
    references = impl.get_references()
    impl_references = parser.find_references(job_class.get_package(), job_class.get_class_name())

    if debug:
        print(f"**Processing document: {doc.app} - {doc.action} - {doc.get_context_job_class().job_class}")
        print(f"    Found file: {impl.path}")
        for f in references:
            print(f"    Found reference file: {parser.find(f.package, f.class_name).path}")
        for f in impl_references:
            print(f"    Found reference by file: {f.path}")

    return [impl.path] + [parser.find(f.package, f.class_name).path for f in references] + [f.path for f in impl_references]


def fetch_handler_context(doc: ActionDocument, parser: RepoJavaParser, debug: bool = False) -> list[str]:
    handler = doc.get_context_handler()
    impl = parser.find(handler.get_package(), handler.get_class_name())
    references = impl.get_references()

    impl_references = parser.find_references(handler.get_package(), handler.get_class_name())

    if debug:
        print(f"**Processing document: {doc.app} - {doc.action} - {doc.get_context_handler().handler}")
        print(f"    Found file: {impl.path}")
        for f in references:
            print(f"    Found reference file: {parser.find(f.package, f.class_name).path}")
        for f in impl_references:
            print(f"    Found reference by file: {f.path}")

    return [impl.path] + [parser.find(f.package, f.class_name).path for f in references] + [f.path for f in impl_references]


def fetch_action_context(action: str, parser: RepoJavaParser, level: int = 3, seen: set[str] = None, debug: bool = False) -> list[str]:
    trace = ActionTraces(action)
    if trace.get_root_doc().app not in parser.apps:
        print(f"Action {action} does not belong to any of the specified apps in the repo: {parser.apps}")
        return []
    if seen:
        identifier = (trace.get_root_doc().app, trace.get_root_doc().action)
        if identifier in seen:
            print(f"Action {action} has already been processed.")
            return []
        seen.add(action)
    if debug:
        print(f"Processing action: {action}")
        print(f"===============================")
    files = []
    for doc in trace.walk(level):
        if doc.action.startswith("api:"):
            files = files + fetch_api_context(doc, parser)
        elif doc.action.startswith("http:"):
            files = files + fetch_http_context(doc, parser)
        elif doc.action.startswith("job:"):
            files = files + fetch_job_context(doc, parser)
    return files


def build_repo_action_context(parser: RepoJavaParser):
    print(f"Building action context for repository: {parser.repo_path}")
    actions = RecentActions(10, path="recent_actions.json")
    seen = set()
    for action in actions.actions:
        fetch_action_context(action.action, parser, seen=seen)


def main(repo_path: str, action: str = None):
    parser = RepoJavaParser(repo_path)
    if action:
        fetch_action_context(action, parser)
    else:
        build_repo_action_context(parser)

if __name__ == '__main__':
    fire.Fire(main)