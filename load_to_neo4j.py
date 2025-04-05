import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from extract import extract_from_repo

# Load environment variables
load_dotenv()

# Get credentials from .env
NEO4J_URI = os.getenv("uri")
NEO4J_USER = os.getenv("user")
NEO4J_PASSWORD = os.getenv("password")

class Neo4jLoader:
    def __init__(self, uri, user, password):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the database connection"""
        self.driver.close()

    def run_query(self, query, params=None):
        """Run a Cypher query with optional parameters"""
        with self.driver.session() as session:
            result = session.run(query, params)
            return result

    def create_schema_constraints(self):
        """Create schema constraints to improve query performance"""
        # Create constraints for each node type to ensure uniqueness
        node_types = ["File", "Function", "Library", "Class", "Method"]
        for node_type in node_types:
            query = f"""
            CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_type}) REQUIRE n.name IS UNIQUE
            """
            try:
                self.run_query(query)
                print(f"✅ Created constraint for {node_type}")
            except Exception as e:
                print(f"⚠️ Error creating constraint for {node_type}: {e}")

    def create_file_nodes(self, entities):
        """Create all File nodes first to ensure file references exist"""
        # Extract all unique files from entities
        files = set()
        for (entity_type, name, file) in entities:
            if '/' in file or '\\' in file:  # This is a file path
                files.add(file)
        
        # Create File nodes
        for file in files:
            query = """
            MERGE (f:File {name: $name})
            """
            self.run_query(query, {'name': file})
        
        print(f"✅ Created {len(files)} File nodes")

    def create_nodes_and_relationships(self, entities, relationships, calls):
        """Create nodes and relationships in Neo4j"""
        # Create schema constraints for better performance
        self.create_schema_constraints()
        
        # Create File nodes first
        self.create_file_nodes(entities)

        # Step 1: Create all Nodes
        for (entity_type, name, file) in entities:
            query = f"""
            MERGE (n:{entity_type} {{name: $name, file: $file}})
            """
            self.run_query(query, {'name': name, 'file': file})

        print(f"✅ Created {len(entities)} entity nodes")

        # Step 2: Create Relationships from the relationships list
        relationship_count = 0
        for (source, relation, target) in relationships:
            query = None
            params = {'source': source, 'target': target}

            # CONTAINS Relationship (File-to-Entity)
            if relation == 'CONTAINS':
                # Determine target type from entities
                target_type = None
                for (entity_type, name, _) in entities:
                    if name == target:
                        target_type = entity_type
                        break
                
                if target_type:
                    query = f"""
                    MATCH (a:File {{name: $source}}), (b:{target_type} {{name: $target}})
                    MERGE (a)-[r:CONTAINS]->(b)
                    RETURN r
                    """
                else:
                    # Fallback if type not found
                    query = """
                    MATCH (a:File {name: $source}), (b {name: $target})
                    MERGE (a)-[r:CONTAINS]->(b)
                    RETURN r
                    """

            # IMPORTS Relationship (File-to-Library)
            elif relation == 'IMPORTS':
                query = """
                MATCH (a:File {name: $source}), (b:Library {name: $target})
                MERGE (a)-[r:IMPORTS]->(b)
                RETURN r
                """

            # DEFINES Relationship (Class-to-Method)
            elif relation == 'DEFINES':
                query = """
                MATCH (a:Class {name: $source}), (b:Method {name: $target})
                MERGE (a)-[r:DEFINES]->(b)
                RETURN r
                """
            
            # Execute the query if it exists
            if query:
                result = self.run_query(query, params)
                if result:
                    relationship_count += 1

        print(f"✅ Created relationships from relationship list")

        # Step 3: Create Function CALLS Relationships
        calls_count = 0
        for (source, relation, target) in calls:
            if relation == 'CALLS':
                # Try to find the source and target functions/methods
                query = """
                MATCH (a), (b)
                WHERE (a:Function OR a:Method) AND a.name = $source
                AND (b:Function OR b:Method OR b:Library) AND b.name = $target
                MERGE (a)-[r:CALLS]->(b)
                RETURN r
                """
                result = self.run_query(query, {'source': source, 'target': target})
                if result:
                    calls_count += 1

        print(f"✅ Created {calls_count} CALLS relationships")
        
        # Verify all relationship types exist in the database
        self.verify_relationships()

    def verify_relationships(self):
        """Verify all relationship types exist in the Neo4j database"""
        expected_relationships = ["CONTAINS", "IMPORTS", "DEFINES", "CALLS"]
        
        print("\n🔍 Verifying relationships in database:")
        for rel_type in expected_relationships:
            query = f"""
            MATCH ()-[r:{rel_type}]->() 
            RETURN count(r) as count
            """
            result = self.run_query(query).single()
            if result and result["count"] > 0:
                print(f"✅ {rel_type}: {result['count']} relationships found")
            else:
                print(f"⚠️ {rel_type}: No relationships found")

def main():
    repo_path = "app_repo"  # Change if needed
    result = extract_from_repo([repo_path])  # Extract data from repo
    
    if not result["entities"] and not result["relationships"]:
        print("⚠️ No data extracted! Check extract.py")
        return

    # Print summary of extracted data
    print(f"\n📊 Extraction Summary:")
    print(f"- {len(result['entities'])} entities")
    print(f"- {len(result['relationships'])} structural relationships")
    print(f"- {len(result['calls'])} function calls")
    print(f"- {len(result['data_flows'])} data flows\n")

    loader = Neo4jLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Clear existing data for clean import (optional - comment out if not needed)
    loader.run_query("MATCH (n) DETACH DELETE n")
    print("🧹 Cleared existing data from Neo4j database")
    
    # Create nodes and relationships
    loader.create_nodes_and_relationships(
        result["entities"], 
        result["relationships"],
        result["calls"]
    )
    
    loader.close()
    print("\n✅ Data successfully loaded to Neo4j!")

if __name__ == "__main__":
    main()