import ast
import os
import re

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = os.path.normpath(filename).replace("\\", "/")
        self.entities = []
        self.relationships = []
        self.calls = []
        self.data_flows = []
        self.current_class = None  # Track current class
        self.current_function = None  # Track current function
        self.api_endpoints = []  # Track API endpoints
        self.variables = set()  # Track defined variables

    def visit_Import(self, node):
        """Handles `import module` statements."""
        for alias in node.names:
            self.entities.append(("Library", alias.name, self.filename))
            self.relationships.append((self.filename, "IMPORTS", alias.name))

    def visit_ImportFrom(self, node):
        """Handles `from module import X` statements."""
        if node.module:
            self.entities.append(("Library", node.module, self.filename))
            self.relationships.append((self.filename, "IMPORTS", node.module))
            # Also track specific imports
            for alias in node.names:
                self.entities.append(("Import", alias.name, self.filename))
                self.relationships.append((node.module, "PROVIDES", alias.name))

    def visit_ClassDef(self, node):
        """Handles class definitions."""
        self.entities.append(("Class", node.name, self.filename))
        self.relationships.append((self.filename, "CONTAINS", node.name))
        
        # Track inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                # Add base class as entity if not added yet
                self.entities.append(("Class", base.id, self.filename))
                self.relationships.append((node.name, "INHERITS_FROM", base.id))
        
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Handles function and method definitions."""
        old_function = self.current_function
        self.current_function = node.name
        
        if self.current_class:
            self.entities.append(("Method", node.name, self.current_class))
            self.relationships.append((self.current_class, "DEFINES", node.name))
        else:
            self.entities.append(("Function", node.name, self.filename))
            self.relationships.append((self.filename, "CONTAINS", node.name))

        # Track parameters
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name != 'self':  # Skip 'self' in methods
                self.entities.append(("Parameter", arg_name, node.name))
                self.relationships.append((node.name, "ACCEPTS", arg_name))

        # Capture Decorators (e.g., @app.route)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                # Handle Flask route decorators
                if decorator.func.attr == 'route' and decorator.args:
                    # Extract the route path
                    if isinstance(decorator.args[0], ast.Constant):
                        route_path = decorator.args[0].value
                        self.api_endpoints.append((node.name, route_path))
                        self.entities.append(("API_Endpoint", route_path, self.filename))
                        self.relationships.append((node.name, "EXPOSES", route_path))
                        
                        # Check for HTTP methods in the decorator
                        for keyword in decorator.keywords:
                            if keyword.arg == 'methods' and isinstance(keyword.value, ast.List):
                                for elt in keyword.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        method = elt.value
                                        self.relationships.append((route_path, "SUPPORTS", method))
                                        self.entities.append(("HTTP_Method", method, route_path))
            
            if isinstance(decorator, ast.Name):
                self.relationships.append((node.name, "DECORATED_BY", decorator.id))
            elif isinstance(decorator, ast.Attribute):
                self.relationships.append((node.name, "DECORATED_BY", decorator.attr))

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        """Handles function calls."""
        if self.current_function:
            if isinstance(node.func, ast.Name):
                # Direct function call
                self.calls.append((self.current_function, "CALLS", node.func.id))
            elif isinstance(node.func, ast.Attribute):
                # Method call (obj.method())
                if isinstance(node.func.value, ast.Name):
                    # Track both the object and the method
                    obj_name = node.func.value.id
                    method_name = node.func.attr
                    self.calls.append((self.current_function, "CALLS", method_name))
                    
                    # Track usage of specific APIs
                    if obj_name == 'request' and method_name in ['json', 'args', 'get']:
                        self.relationships.append((self.current_function, "USES_INPUT", f"{obj_name}.{method_name}"))
                    elif obj_name == 'requests' and method_name in ['get', 'post', 'put', 'delete']:
                        # This is an HTTP client call
                        self.relationships.append((self.current_function, "MAKES_REQUEST", method_name))
        
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Handle variable assignments to track data flow."""
        targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
                # Add to variables set
                self.variables.add(target.id)
                
                # Create Variable entity if in a function scope
                if self.current_function:
                    self.entities.append(("Variable", target.id, self.current_function))
                    self.relationships.append((self.current_function, "DEFINES_VAR", target.id))
        
        # Track data flow
        if isinstance(node.value, ast.Constant):
            value = str(node.value.value)
            for target in targets:
                self.data_flows.append((value, "FLOW_TO", target))
        elif isinstance(node.value, ast.Name):
            source = node.value.id
            for target in targets:
                self.data_flows.append((source, "FLOW_TO", target))
        
        self.generic_visit(node)

    def visit_Return(self, node):
        """Handle return statements to track data flow."""
        if self.current_function:
            if isinstance(node.value, ast.Dict):
                # Track return structure (common in API responses)
                keys = []
                for key in node.value.keys:
                    if isinstance(key, ast.Constant):
                        keys.append(key.value)
                
                if keys:
                    self.relationships.append((self.current_function, "RETURNS_FIELDS", str(keys)))
            
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    func_name = node.value.func.id
                    self.relationships.append((self.current_function, "RETURNS_FROM", func_name))
        
        self.generic_visit(node)

    def analyze(self, code):
        try:
            tree = ast.parse(code)
            self.visit(tree)
            
            # Process Flask app initialization if present
            self._find_flask_app(code)
            
            return {
                "entities": list(set(self.entities)),
                "relationships": list(set(self.relationships)),
                "calls": list(set(self.calls)),
                "data_flows": list(set(self.data_flows)),
                "api_endpoints": list(set(self.api_endpoints)),
            }
        except SyntaxError as e:
            print(f"Syntax error in {self.filename}: {e}")
            return {
                "entities": [],
                "relationships": [],
                "calls": [],
                "data_flows": [],
                "api_endpoints": [],
            }

    def _find_flask_app(self, code):
        """Find Flask app initialization in code."""
        # Look for Flask app initialization (simple regex approach)
        match = re.search(r"(\w+)\s*=\s*Flask\(__name__\)", code)
        if match:
            app_name = match.group(1)
            self.entities.append(("WebApp", app_name, self.filename))
            self.relationships.append((self.filename, "DEFINES", app_name))

def extract_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    analyzer = CodeAnalyzer(filepath)
    return analyzer.analyze(code)

def extract_from_repo(repo_paths):
    all_entities = []
    all_relationships = []
    all_calls = []
    all_data_flows = []
    all_api_endpoints = []
    
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
                        all_api_endpoints.extend(result["api_endpoints"])
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")

    return {
        "entities": list(set(all_entities)),
        "relationships": list(set(all_relationships)),
        "calls": list(set(all_calls)),
        "data_flows": list(set(all_data_flows)),
        "api_endpoints": list(set(all_api_endpoints)),
    }

if __name__ == "__main__":
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
        
    print("\n✅ API Endpoints:")
    for endpoint in result["api_endpoints"]:
        print(endpoint)