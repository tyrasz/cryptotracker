from flask import Flask, request, jsonify, render_template
import json
import os
from fuzzywuzzy import fuzz

app = Flask(__name__)

# Load the announcements from the JSON file
json_file_path = 'adgm_announcements_20240915_182338.json'
if os.path.exists(json_file_path):
    with open(json_file_path, 'r') as f:
        data = json.load(f)
        announcements = data['announcements']
else:
    print(f"Warning: {json_file_path} not found. Starting with empty announcements list.")
    announcements = []

def fuzzy_search(query, text, threshold=70):
    """Perform fuzzy search on text."""
    return fuzz.partial_ratio(query.lower(), text.lower()) >= threshold

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_announcements():
    tags = request.args.get('tags', '').lower().split(',')
    
    if not tags or tags == ['']:
        return render_template('results.html', results=[], tags="None provided")

    results = []
    for announcement in announcements:
        match = False
        for tag in tags:
            # Check tags
            if any(fuzzy_search(tag, t) for t in announcement.get('tags', [])):
                match = True
                break
            # Check title
            if fuzzy_search(tag, announcement.get('title', '')):
                match = True
                break
            # Check content (if available)
            if 'content' in announcement and fuzzy_search(tag, announcement['content']):
                match = True
                break
        if match:
            results.append(announcement)

    return render_template('results.html', results=results, tags=', '.join(tags))

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

if __name__ == '__main__':
    app.run(debug=True)