# @author: stephen

import tree_sitter_java as tsj
from pathlib import Path
from tree_sitter import Language, Parser, Node



LANGUAGE = Language(tsj.language())
# no need to collect all java.lang classes, just a few common ones for the first filter
JAVA_LANG_CLASSES = {
    "Object", "String", "StringBuilder", "StringBuffer", "Integer", "Long", "Double", "Float",
    "Boolean", "Byte", "Short", "Character", "Void", "Math", "System", "Thread", "Runnable",
    "Exception", "RuntimeException", "IllegalArgumentException", "IllegalStateException",
    "NullPointerException", "IndexOutOfBoundsException", "Throwable", "Error", "Override",
    "Deprecated", "SuppressWarnings", "Class", "ClassLoader"
}
JAVA_PRIMITIVE_TYPES = {"byte", "short", "int", "long", "float", "double", "boolean", "char", "void", "var"}


class MethodBodyParseResult:
    def __init__(self):
        self.body: str = ""
        self.references: list[str] = []

    def __repr__(self):
        return f"MethodBodyParseResult(body={self.body}, references={self.references})"


class MethodParseResult:
    def __init__(self):
        self.name: str = ""
        self.modifiers: str = ""
        self.type_parameters: str = ""
        self.type: str = ""
        self.parameters: str = ""
        self.throws: str = ""

    def __repr__(self):
        parts = []
        if self.modifiers:
            parts.append(self.modifiers)
        if self.type_parameters:
            parts.append(self.type_parameters)
        if self.type:
            parts.append(self.type)
        if self.parameters:
            parts.append(self.name + f"{self.parameters}")
        else:
            parts.append(self.name)
        if self.throws:
            parts.append(f"throws {self.throws}")
        return " ".join(parts) + ";"


class FieldParseResult:
    def __init__(self):
        self.modifiers: str = ""
        self.type: str = ""
        self.declarator: str = ""

    def __repr__(self):
        parts = []
        if self.modifiers:
            parts.append(self.modifiers)
        if self.type:
            parts.append(self.type)
        if self.declarator:
            parts.append(self.declarator)
        return " ".join(parts) + ";"


class ClassParseResult:
    def __init__(self):
        self.name: str = ""
        self.modifiers: str = ""
        self.type: str = ""
        self.type_parameters: str = ""
        self.superclass: str = ""
        self.interfaces: str = ""
        self.methods: dict[str, MethodParseResult] = {}
        self.fields: list[FieldParseResult] = []

    def get_method_by_name(self, name: str) -> MethodParseResult:
        return self.methods[name]

    def __repr__(self):
        parts = []
        if self.modifiers:
            parts.append(self.modifiers)
        if self.type == "class_declaration":
            parts.append("class")
        if self.type == "interface_declaration":
            parts.append("interface")
        if self.type == "enum_declaration":
            parts.append("enum")
        if self.type == "annotation_type_declaration":
            parts.append("@interface")
        if self.type == "record_declaration":
            parts.append("record")
        if self.type_parameters:
            parts.append(self.name + self.type_parameters)
        else:
            parts.append(self.name)
        if self.superclass:
            parts.extend(["extends", self.superclass])
        if self.interfaces:
            parts.append(self.interfaces)
        return " ".join(parts) + " {\n" + "\n".join(["    " + str(m) for m in self.methods.values()]) + "\n}" 

class ImportParseResult:
    def __init__(self):
        self.package: str | None = ""
        self.class_name: str = ""

    def __repr__(self):
        return "import " + self.package + "." + self.class_name + ";"

class JavaParseResult:
    def __init__(self):
        self.path: str = ""
        self.package: str = ""
        self.root: str = ""
        self.imports: list[ImportParseResult] = []
        self.implicit_imports: list[str] = []
        self.classes: list[ClassParseResult] = []
    
    def get_import_by_class_name(self, class_name: str) -> ImportParseResult | None:
        for i in self.imports:
            if i.class_name == class_name:
                return i
        return None

    def is_import_class(self, package: str, class_name: str) -> bool:
        for imp in self.imports:
            if imp.package == package and imp.class_name == class_name:
                return True
        return False

    def get_class_by_name(self, class_name: str) -> ClassParseResult | None:
        for cls in self.classes:
            if cls.name == class_name:
                return cls
        return None

    def get_method_by_name(self, class_name: str, method_name: str) -> MethodParseResult | None:
        cls = self.get_class_by_name(class_name)
        if cls:
            return cls.get_method_by_name(method_name)
        return None

    def get_superclass_of_class(self, class_name: str) -> str:
        cls = self.get_class_by_name(class_name)
        return cls.superclass.split(" ")[-1] if cls and cls.superclass else ""

    def get_interface_of_class(self, class_name: str) -> str:
        cls = self.get_class_by_name(class_name)
        return cls.interfaces.split(" ")[-1] if cls and cls.interfaces else ""

    def _get_method_signature_references(self, class_name: str, method_name: str) -> list[ImportParseResult]:
        method = self.get_method_by_name(class_name, method_name)
        references = []
        for imp in self.imports:
            if imp.class_name == method.type or imp.class_name in method.parameters:
                references.append(imp)
        return references

    def get_method_body(self, class_name: str, method_name: str) -> MethodBodyParseResult:
        parser = JavaBodyParser(self.path)
        return parser.parse(class_name, method_name)

    def _get_method_body_references(self, class_name: str, method_name: str) -> list[ImportParseResult]:
        body = self.get_method_body(class_name, method_name)
        types = set([i.class_name for i in self.imports] + [i for i in self.implicit_imports])
        field_types = {}
        for f in self.get_class_by_name(class_name).fields:
            field_types[f.declarator] = f.type
        references = []
        for ref in body.references:
            if ref in types:
                import_result = self.get_import_by_class_name(ref)
                if import_result:
                    references.append(import_result)
            if ref in field_types:
                field_type = field_types[ref]
                import_result = self.get_import_by_class_name(field_type)
                if import_result:
                    references.append(import_result)
        return references

    def get_method_references(self, class_name: str, method_name: str) -> list[ImportParseResult]:
        """
        Get all imports that are used in a method's signature or body.

        Args:
            class_name: The name of the class containing the method
            method_name: The name of the method to analyze

        Returns:
            A list of ImportParseResult objects that are used in the method
        """
        signature_references = self._get_method_signature_references(class_name, method_name)
        body_references = self._get_method_body_references(class_name, method_name)
        references = set(signature_references + body_references)
        references = [ref for ref in references if not ref.package.startswith("core.framework")]
        return references


class JavaBodyParser:
    def __init__(self, path: str):
        self.result = None
        self.parser = Parser(LANGUAGE)
        self.path = path


    def parse(self, class_name: str, method_name: str) -> MethodBodyParseResult:
        if self.result is not None: return self.result

        self.result = MethodBodyParseResult()

        try:
            with open(self.path, "rb") as file:
                source_bytes = file.read()
        except FileNotFoundError:
            print(f"Error: File not found at {self.path}")
            return self.result
        except Exception as e:
            print(f"Error reading file: {e}")
            return self.result

        tree = self.parser.parse(source_bytes)
        root_node = tree.root_node

        method_node = self._find_method_node(root_node, class_name, method_name)
        if not method_node:
            return self.result

        body_node = method_node.child_by_field_name("body")
        if body_node:
            self.result.body = body_node.text.decode('utf-8')
            self._collect_identifier_and_type_identifier(body_node, self.result.references)

        return self.result

    # noinspection PyMethodMayBeStatic
    def _collect_identifier_and_type_identifier(self, node, refs):
        if node.type == "type_identifier" or node.type == "identifier":
            type_name = node.text.decode("utf-8")
            if type_name not in refs:
                refs.append(type_name)
        for child in node.children:
            self._collect_identifier_and_type_identifier(child, refs)


    def _find_method_node(self, node, class_name: str, method_name: str, current_class=None):
        if node.type in (
                "class_declaration", "interface_declaration",
                "enum_declaration", "record_declaration", "annotation_type_declaration"
        ):
            name_node = node.child_by_field_name('name')
            if name_node:
                current_class = name_node.text.decode('utf-8')
        if node.type == "method_declaration" and current_class == class_name:
            name_node = node.child_by_field_name('name')
            if name_node and name_node.text.decode('utf-8') == method_name:
                return node
        for child in node.children:
            result = self._find_method_node(child, class_name, method_name, current_class)
            if result:
                return result
        return None


class JavaFieldParser:
    def __init__(self, content: str = None):
        self.result = None
        self.parser = Parser(LANGUAGE)
        if content is not None:
            self.parse(content)
    
    def parse(self, content: str):
        if self.result is not None: return self.result
        
        self.result = FieldParseResult()
        
        tree = self.parser.parse(content.encode())
        node = tree.root_node.children[0]
        if node.children[0].type == "modifiers":
            self.result.modifiers = node.children[0].text.decode('utf-8')
        self.result.type = node.child_by_field_name("type").text.decode('utf-8')
        self.result.declarator = node.child_by_field_name("declarator").text.decode('utf-8')
        
    def is_inject(self):
        return "@Inject" in self.result.modifiers


class JavaParser:
    def __init__(self, path: str = None):
        self.result = None
        self.parser = Parser(LANGUAGE)
        if path is not None:
            self.parse(path)

    def parse(self, path: str) -> JavaParseResult:
        if self.result is not None: return self.result

        self.result = JavaParseResult()
        self.result.path = path

        try:
            with open(path, "rb") as file:
                source_bytes = file.read()
        except FileNotFoundError:
            print(f"Error: File not found at {path}")
            return self.result 
        except Exception as e:
            print(f"Error reading file: {e}")
            return self.result

        tree = self.parser.parse(source_bytes)
        root_node = tree.root_node

        self._traverse_tree(root_node, self.result)
        return self.result


    def _find_class(self, class_name: str) -> ClassParseResult | None:
        """
        Helper method to find a class by name.
        
        Args:
            class_name: The name of the class to find
            
        Returns:
            The ClassParseResult object if found, None otherwise
        """
        for cls in self.result.classes:
            if cls.name == class_name:
                return cls
        return None

    
    def _get_method_block(self, class_name: str, method_name: str) -> str:
        with open(self.result.path, "rb") as file:
            source_bytes = file.read()
            tree = self.parser.parse(source_bytes)
            root_node = tree.root_node
            method_node = self._find_method_node(root_node, class_name, method_name)
            if method_node:
                return method_node.text.decode('utf-8')
            return ""
    
    def _find_method_node(self, node: Node, class_name: str, method_name: str, current_class: str = None) -> Node | None:
        """
        Recursively find the method node in the AST.
        
        Args:
            node: Current AST node
            class_name: Target class name
            method_name: Target method name
            current_class: Current class context during traversal
            
        Returns:
            The method node if found, None otherwise
        """
        # Check if current node is a class declaration
        if (node.type == "class_declaration" 
                or node.type == "interface_declaration" 
                or node.type == "enum_declaration" 
                or node.type == "record_declaration"
                or node.type == "annotation_type_declaration"):
            name_node = node.child_by_field_name('name')
            if name_node:
                current_class = name_node.text.decode('utf-8')
        
        # Check if current node is a method declaration in the target class
        if node.type == "method_declaration" and current_class == class_name:
            name_node = node.child_by_field_name('name')
            if name_node and name_node.text.decode('utf-8') == method_name:
                return node
        
        # Recursively search in child nodes
        for child in node.children:
            result = self._find_method_node(child, class_name, method_name, current_class)
            if result:
                return result
        
        return None

    def _get_method_imports(self, class_name: str, method_name: str, content: str) -> list[str]:
        """
        Helper method to get imports used in a given method content.
        
        Args:
            class_name: The name of the class containing the method
            method_name: The name of the method to analyze
            content: The content to check for imports (signature or body)
            
        Returns:
            A list of import statements that are used in the content
        """
        if not content:
            return []
            
        # Check all imports against the content
        used_imports = []
        for imp in self.result.imports:
            # Remove import keyword and semicolon
            clean_import = imp.replace("import", "").replace(";", "").strip()
            if clean_import.endswith(".*"):
                # Always include wildcard imports
                used_imports.append(imp)
            else:
                # Check if the class name appears in the content
                name = clean_import.split(".")[-1]
                if name in content:
                    used_imports.append(imp)
                    
        return used_imports

    def get_method_signature_imports(self, class_name: str, method_name: str) -> list[str]:
        """
        Get Java imports that are used in a method's signature.
        
        Args:
            class_name: The name of the class containing the method
            method_name: The name of the method to analyze
            
        Returns:
            A list of import statements that are used in the method signature
        """
        target_class = self._find_class(class_name)
        if not target_class:
            return []
            
        method_result = target_class.methods.get(method_name)
        if not method_result:
            return []
            
        signature_text = method_result.parameters + method_result.type
        return self._get_method_imports(class_name, method_name, signature_text)

    def get_method_body_imports(self, class_name: str, method_name: str) -> list[str]:
        """
        Get Java imports that are used by a specific method body.
        
        Args:
            class_name: The name of the class containing the method
            method_name: The name of the method to analyze
            
        Returns:
            A list of import statements that are used in the method
        """
        target_class = self._find_class(class_name)
        if not target_class:
            return []
            
        method_result = target_class.methods.get(method_name)
        if not method_result:
            return []
            
        body = self._get_method_block(class_name, method_name)

        related_fields = ""
        for field in target_class.fields:
            if field.declarator in body:
                related_fields = related_fields + field.type + " "

        return self._get_method_imports(class_name, method_name, body + " " + related_fields)

    def _traverse_tree(self, node: Node, rst: JavaParseResult, current_class: ClassParseResult = None):
        if node.type == "identifier":
            identifier = node.text.decode('utf-8')
            if identifier[0].isupper() \
                    and identifier not in JAVA_LANG_CLASSES \
                    and identifier not in JAVA_PRIMITIVE_TYPES \
                    and identifier not in rst.implicit_imports \
                    and identifier not in [i.class_name for i in rst.imports]:
                rst.implicit_imports.append(identifier)

        elif node.type == "type_identifier":
            type_identifier = node.text.decode('utf-8')
            if type_identifier[0].isupper() \
                    and type_identifier not in JAVA_LANG_CLASSES \
                    and type_identifier not in JAVA_PRIMITIVE_TYPES \
                    and type_identifier not in rst.implicit_imports \
                    and type_identifier not in [i.class_name for i in rst.imports]:
                rst.implicit_imports.append(type_identifier)


        elif node.type == "package_declaration":
            package_name_node = node.named_children[0]
            if package_name_node:
                rst.package = package_name_node.text.decode('utf-8')

        elif node.type == "import_declaration":
            import_text = node.text.decode('utf-8')
            rst.imports.append(self._build_import_import_result(import_text))

        elif (node.type == "class_declaration" 
                or node.type == "interface_declaration" 
                or node.type == "enum_declaration" 
                or node.type == "record_declaration"
                or node.type == "annotation_type_declaration"):
            new_class = self._build_class_parse_result(node)
            rst.classes.append(new_class)
            if not current_class:
                rst.root = new_class.name
            # Recursively traverse children with the new class context
            for child in node.children:
                self._traverse_tree(child, rst, current_class=new_class)
            return  # Important: return here to avoid double traversal

        elif node.type == "field_declaration":
            if current_class:
                field_text = node.text.decode('utf-8').strip()
                current_class.fields.append(JavaFieldParser(field_text).result)

        elif node.type == "method_declaration":
            if current_class:
                method_result = self._build_method_parse_result(node)
                current_class.methods[method_result.name] = method_result

        # Continue traversal for other nodes
        for child in node.children:
            self._traverse_tree(child, rst, current_class)


    # noinspection PyMethodMayBeStatic
    def _build_class_parse_result(self, node: Node) -> ClassParseResult:
        clazz = ClassParseResult()
        clazz.type = node.type
        if node.children[0].type == "modifiers":
            clazz.modifiers = node.children[0].text.decode('utf-8')
        name_node = node.child_by_field_name('name')
        if name_node:
            clazz.name = name_node.text.decode('utf-8')
        type_parameters_node = node.child_by_field_name("type_parameters")
        if type_parameters_node:
            clazz.type_parameters = type_parameters_node.text.decode("utf-8")
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            clazz.superclass = superclass_node.text.decode("utf-8")
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node:
            clazz.interfaces = interfaces_node.text.decode("utf-8")
        return clazz

    # noinspection PyMethodMayBeStatic
    def _build_method_parse_result(self, node: Node) -> MethodParseResult:
        method = MethodParseResult()
        if node.children[0].type == "modifiers":
            method.modifiers = node.children[0].text.decode('utf-8')
        name_node = node.child_by_field_name('name')
        if name_node:
            method.name = name_node.text.decode('utf-8')
        parameters_node = node.child_by_field_name('parameters')
        if parameters_node:
            method.parameters = parameters_node.text.decode('utf-8')
        type_node = node.child_by_field_name('type')
        if type_node:
            method.type = type_node.text.decode('utf-8')
        type_parameters_node = node.child_by_field_name('type_parameters')
        if type_parameters_node:
            method.type = type_parameters_node.text.decode('utf-8')
        throws_node = node.child_by_field_name('throws')
        if throws_node:
            method.type = throws_node.text.decode('utf-8')
        return method

    # noinspection PyMethodMayBeStatic
    def _build_import_import_result(self, import_text: str) -> ImportParseResult:
        import_result = ImportParseResult()
        import_text = import_text.strip()
        if import_text.endswith(";"):
            import_text = import_text[:-1].strip()
        if "import" in import_text:
            import_text = import_text.replace("import", "").strip()
        parts = import_text.split(".")
        if len(parts) > 1:
            import_result.package = ".".join(parts[:-1])
            import_result.class_name = parts[-1]
        else:
            import_result.package = None
            import_result.class_name = parts[0]
        return import_result


def path_to_class_name(path: str) -> str:
    return Path(path).stem


def import_to_package_and_class_name(import_statement: str) -> tuple[str, str]:
    clean_import = import_statement.replace("import", "").replace(";", "").strip()
    parts = clean_import.split(".")
    return ".".join(parts[:-1]), parts[-1]


def class_name_to_file_name(class_name: str) -> str:
    return class_name + ".java"


def file_name_to_class_name(filename: str) -> str:
    return filename.split(".")[0]