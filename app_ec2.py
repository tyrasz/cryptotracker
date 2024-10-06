from flask import Flask, request, jsonify
import json
import boto3
from botocore.exceptions import ClientError
from fuzzywuzzy import fuzz
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')

# Initialize S3 client
s3 = boto3.client('s3')

# S3 bucket and file details
BUCKET_NAME = 'crypto-crawler-bucket321'
FILE_NAME = 'adgm_announcements_20240915_182338.json'

def load_announcements_from_s3():
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)
        return data['announcements']
    except ClientError as e:
        logger.error(f"Error loading announcements from S3: {e}")
        return []

announcements = load_announcements_from_s3()

def fuzzy_search(query, text, threshold=70):
    """Perform fuzzy search on text."""
    return fuzz.partial_ratio(query.lower(), text.lower()) >= threshold

@app.route('/search', methods=['GET'])
def search_announcements():
    tags = request.args.get('tags', '').lower().split(',')
    
    if not tags or tags == ['']:
        return jsonify({"error": "No tags provided"}), 400

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

    return jsonify({"results": results})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)