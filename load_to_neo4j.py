import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from extract import extract_from_repo

# Load environment variables from .env
load_dotenv()

# Get credentials from .env
NEO4J_URI = os.getenv("uri")
NEO4J_USER = os.getenv("user")
NEO4J_PASSWORD = os.getenv("password")

class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()

    def run_query(self, query, params=None):
        with self.driver.session() as session:
            session.run(query, params)

    def create_nodes_and_relationships(self, entities, relationships):
        # Create nodes
        for (entity_type, name, file) in entities:
            query = f"""
            MERGE (n:{entity_type} {{name: $name, file: $file}})
            """
            self.run_query(query, {'name': name, 'file': file})

        # Create relationships
        for (source, relation, target) in relationships:
            if relation == 'CALLS':
                query = """
                MATCH (a:Function), (b:Function)
                WHERE a.name = $source AND b.name = $target
                MERGE (a)-[:CALLS]->(b)
                """
            else:
                query = """
                MATCH (a), (b)
                WHERE a.name = $source AND b.name = $target
                MERGE (a)-[:{relation}]->(b)
                """.format(relation=relation)
            self.run_query(query, {'source': source, 'target': target})

def main():
    # Extract entities and relationships from the repo
    repo_path = "sample_repo"
    result = extract_from_repo(repo_path)
    
    entities = result["entities"]
    relationships = result["relationships"]

    # Initialize loader
    loader = Neo4jLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    loader.create_nodes_and_relationships(entities, relationships)
    loader.close()
    print("✅ Data successfully loaded to Neo4j!")

if __name__ == "__main__":
    main()
