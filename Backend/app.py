from flask import Flask, request, jsonify, send_from_directory
from scraper import scrape_company_data
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return send_from_directory("../frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("../frontend", path)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    result = scrape_company_data(url)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
