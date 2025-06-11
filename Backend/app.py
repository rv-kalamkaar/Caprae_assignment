# backend/app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from Backend.scraper import discover_links, extract_main_page_data
from Backend.analyzer import generate_swot, find_leaders, detect_tech_stack

app = Flask(__name__, template_folder='../frontend')
CORS(app)  # Allow cross-origin requests if needed

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        links = discover_links(url)
        page_data = extract_main_page_data(url)

        swot = generate_swot(page_data['text'])
        leaders = find_leaders(page_data['soup'])
        tech_stack = detect_tech_stack(page_data['html'])

        return jsonify({
            "url": url,
            "discovered_links": links,
            "swot": swot,
            "leaders": leaders,
            "tech_stack": tech_stack
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
