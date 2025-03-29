import requests

def get_greeting(name):
    response = requests.get(f"http://localhost:5000/api/greet?name={name}")
    return response.json()

def send_calculation(x, y):
    response = requests.post(
        "http://localhost:5000/api/calculate",
        json={"x": x, "y": y}
    )
    return response.json()
