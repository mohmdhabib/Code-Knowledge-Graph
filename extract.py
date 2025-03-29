import ast
import os

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = os.path.normpath(filename).replace("\\", "/")
        self.entities = []
        self.relationships = []
        self.calls = []
        self.data_flows = []
        self.current_class = None  # Track if inside a class

    def visit_Import(self, node):
        for alias in node.names:
            self.entities.append(("Library", alias.name, self.filename))
            self.relationships.append((self.filename, "IMPORTS", alias.name))

    def visit_ClassDef(self, node):
        self.entities.append(("Class", node.name, self.filename))
        self.relationships.append((self.filename, "CONTAINS", node.name))
        
        self.current_class = node.name  # Set current class
        self.generic_visit(node)
        self.current_class = None  # Reset after visiting class

    def visit_FunctionDef(self, node):
        if self.current_class:
            # If inside a class, treat as a method
            self.entities.append(("Method", node.name, self.current_class))
            self.relationships.append((self.current_class, "DEFINES", node.name))
        else:
            # Otherwise, treat as a top-level function
            self.entities.append(("Function", node.name, self.filename))
            self.relationships.append((self.filename, "CONTAINS", node.name))

        # Capture Function Calls
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                self.calls.append((node.name, "CALLS", stmt.func.id))
            
            # Data Flow (Variable Assignments)
            if isinstance(stmt, ast.Assign):
                targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
                if isinstance(stmt.value, ast.Constant):
                    value = str(stmt.value.value)
                    for target in targets:
                        self.data_flows.append((value, "FLOW_TO", target))
        self.generic_visit(node)

    def analyze(self, code):
        tree = ast.parse(code)
        self.visit(tree)
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "calls": self.calls,
            "data_flows": self.data_flows,
        }

def extract_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    analyzer = CodeAnalyzer(filepath)
    return analyzer.analyze(code)

def extract_from_repo(repo_path):
    all_entities = []
    all_relationships = []
    all_calls = []
    all_data_flows = []
    
    for repo_path in repo_paths:
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        result = extract_from_file(file_path)
                        all_entities.extend(result["entities"])
                        all_relationships.extend(result["relationships"])
                        all_calls.extend(result["calls"])
                        all_data_flows.extend(result["data_flows"])
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")

    return {
        "entities": all_entities,
        "relationships": all_relationships,
        "calls": all_calls,
        "data_flows": all_data_flows,
    }

repo_paths = ["app_repo"]

result = extract_from_repo(repo_paths)

print("✅ Extracted Entities:")
for entity in result["entities"]:
    print(entity)

print("\n✅ Extracted Relationships:")
for rel in result["relationships"]:
    print(rel)

print("\n✅ Execution Flow (Function Calls):")
for call in result["calls"]:
    print(call)

print("\n✅ Data Flow (Variable Dependencies):")
for flow in result["data_flows"]:
    print(flow)
