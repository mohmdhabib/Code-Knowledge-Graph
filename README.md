# Code Knowledge Graph (CKG) for App Repo

## Overview
This project creates a **Code Knowledge Graph (CKG)** for the `app_repo` directory, analyzing entities such as **Libraries**, **Functions**, **Classes**, **Methods**, and their relationships. It utilizes **Neo4j** as the graph database to visualize code structure and interactions.

## Project Structure
```
app_repo/
├── api_service/
│   └── main.py
├── core_module/
│   └── calculator.py
├── microservice_client/
│   └── client.py
├── utils/
│   └── helper.py
├── extract.py
├── load_to_neo4j.py
├── .env
└── README.md
```

## Features
- **Entity Extraction:** Identifies Libraries, Functions, Classes, and Methods.
- **Relationship Mapping:** Tracks `CALLS`, `IMPORTS`, `CONTAINS`, and `DEFINES` relationships.
- **Neo4j Integration:** Loads data into **Neo4j** for visualization.

---

## Prerequisites
1. **Neo4j Desktop** or **Neo4j Aura** (Cloud)
2. **Python 3.8+**
3. **Dependencies:**
```bash
pip install neo4j python-dotenv
```

---

## Setup
### 1. Create `.env` File
Add your Neo4j credentials to the `.env` file:
```env
uri=bolt://localhost:7687
user=neo4j
password=your_password
```

### 2. File Structure
Ensure the `app_repo` directory contains all relevant project files.

---

## How to Run
### 1. Extract Entities and Relationships
Run the extraction script:
```bash
python extract.py
```

### 2. Load Data into Neo4j
```bash
python load_to_neo4j.py
```

✅ **Expected Output:**
```plaintext
✅ Extracted Entities:
('Function', 'greet', 'app_repo/api_service/main.py')
('Class', 'Calculator', 'app_repo/core_module/calculator.py')
...

✅ Extracted Relationships:
('greet', 'CALLS', 'jsonify')
('client.py', 'IMPORTS', 'requests')
...
```

---

## Visualizing in Neo4j
1. Open **Neo4j Browser**.
2. Run the following Cypher queries:
```cypher
// View All Nodes and Relationships
MATCH (n)-[r]->(m) RETURN n, r, m;

// View Specific Relationships
MATCH (f:Function)-[:CALLS]->(g) RETURN f, g;
```

---

## Troubleshooting
- **Missing Libraries?**
  - Ensure dynamic imports are captured.
- **Duplicate Relationships?**
  - Use `MERGE` instead of `CREATE` in Cypher.
- **Empty Results?**
  - Check `.env` credentials and Neo4j service status.

---

## Contributing
Contributions are welcome! Create a pull request or open an issue for suggestions.

---

## License
[MIT License](LICENSE)

---

## Contact
For any questions, feel free to reach out!

