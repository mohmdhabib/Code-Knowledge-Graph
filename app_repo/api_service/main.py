from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/greet', methods=['GET'])
def greet():
    name = request.args.get('name', 'World')
    return jsonify({"message": f"Hello, {name}!"})

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    if not data or 'x' not in data or 'y' not in data:
        return jsonify({"error": "Invalid input"}), 400
    result = data['x'] + data['y']
    return jsonify({"result": result})
