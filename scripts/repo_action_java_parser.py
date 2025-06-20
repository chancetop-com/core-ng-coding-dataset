# @author: stephen

import re
import fire
from library.action_trace import ActionTraces
from library.java_parser import *
from library.file_utils import *
from scripts.library.repo_java_parser import RepoJavaParser


def find_root_app_file(repo_path: str, filename: str) -> str:
    """
    find app file
    """
    classname = file_name_to_class_name(filename)

    def match(java_file):
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return (classname in content and
                        ('extends App {' in content or 'extends Module {' in content))
        except Exception as e:
            print(f"Error reading file {java_file}: {e}")
            return False

    return search_java_file(repo_path, match)

def filter_by_package(package: str, files: list[str]):
    filtered = []
    for file in files:
        rst = JavaParser(file).result
        if package in rst.package:
            filtered.append(file)
    return filtered

def find_root_file(repo_path: str, package: str, classname: str) -> str:
    action_root_java_filename = class_name_to_file_name(classname)
    def match(java_file):
        return java_file.name == action_root_java_filename
    files = search_java_files(repo_path, match)
    return filter_by_package(package, files)[0]


def find_root_web_service_file(repo_path: str, path: str) -> str:
    """
    Finds the web service interface file based on its implementation class.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return None

    classname = path_to_class_name(path)
    pattern = fr"public\s+class\s+{classname}\s+implements\s+(\S+)\s*\{{"
    match = re.search(pattern, content)
    if not match:
        return None
    web_service = match.group(1).strip()

    def match(java_file):
        return java_file.name == class_name_to_file_name(web_service)

    parser = JavaParser(path)
    i = parser.result.get_import_by_class_name(web_service)
    package = import_to_package(i)

    files = search_java_files(repo_path, match)
    return filter_by_package(package, files)[0]


def find_method_signature_import_files(repo_path: str, path: str, method: str) -> list[str]:
    """
    Finds the import files of a method in a web service interface file.
    """
    parser = JavaParser(path)
    imports = parser.get_method_signatrue_imports(path_to_class_name(path), method)
    import_filenames = [class_name_to_file_name(import_to_class_name(i)) for i in imports]
    def match(java_file):
        return java_file.name in import_filenames
    files = search_java_files(repo_path, match)

    parser = JavaParser(path)
    i = parser.result.get_import_by_class_name(web_service)
    package = import_to_package(i)

    return filter_by_package(package, files)


def find_method_body_import_files(repo_path: str, package: str, path: str, method: str) -> list[str]:
    """
    Finds the import files of a method in a java file.
    """
    parser = JavaParser(path)
    imports = parser.get_method_body_imports(path_to_class_name(path), method)
    import_filenames = [class_name_to_file_name(import_to_class_name(i)) for i in imports]
    def match(java_file):
        return java_file.name in import_filenames
    files = search_java_files(repo_path, match)
    return filter_by_package(package, files)


def find_method_body_inject_files(repo_path: str, package: str, path: str, method: str) -> list[str]:
    parser = JavaParser(path)
    method_body = parser.result.classes[0].get_method_by_name(method).body
    imports = parser.result.imports
    injects = []
    for field in parser.result.classes[0].fields:
        field_parser = JavaFieldParser(field)
        if field_parser.is_inject():
            injects.append(field_parser.result)
    def contain_inject(i: str) -> bool:
        for inject in injects:
            if inject.type in i and inject.name in method_body:
                return True
        return False
    
    imports = [i for i in imports if contain_inject(i)]
    import_filenames = [class_name_to_file_name(import_to_class_name(i)) for i in imports]
    def match(java_file):
        return java_file.name in import_filenames
    files = search_java_files(repo_path, match)
    return filter_by_package(package, files)


def main(repo_path: str, action: str):
    trace = ActionTraces(action)
    root_doc = trace.get_root_doc()
    root_package = root_doc.get_context_controller_package()
    root_class_name = root_doc.get_context_controller_class_name()
    root_method_name = root_doc.get_context_controller_method_name()

    parser = RepoJavaParser(repo_path)
    root_file = parser.find(root_package, root_class_name)
    root_app_file = find_root_app_file(repo_path, class_name_to_file_name(root_class_name))
    root_web_service_file = find_root_web_service_file(repo_path, root_file)
    root_web_service_method_import_files = find_method_signature_import_files(repo_path, root_web_service_file, root_method_name)
    root_method_import_files = find_method_body_import_files(repo_path, root_package, root_file, root_method_name)
    root_method_inject_files = find_method_body_inject_files(repo_path, root_package, root_file, root_method_name)

    print(f"Found root file: {root_file}")
    print(f"Found root app file: {root_app_file}")
    print(f"Found root web service file: {root_web_service_file}")
    for f in root_web_service_method_import_files:
        print(f"Found root web service method import files: {f}")
    for f in root_method_import_files:
        print(f"Found root method import files: {f}")
    for f in root_method_inject_files:
        print(f"Found root method inject files: {f}")


if __name__ == '__main__':
    fire.Fire(main)