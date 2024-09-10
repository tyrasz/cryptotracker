import json
import nltk
from textblob import TextBlob
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    if sentiment > 0.05:
        return "Positive"
    elif sentiment < -0.05:
        return "Negative"
    else:
        return "Neutral"

def extract_keywords(text, num_keywords=5):
    # Tokenize and remove stopwords
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(text.lower())
    words = [word for word in words if word.isalnum() and word not in stop_words]
    
    # Count word frequencies
    word_freq = Counter(words)
    
    # Get the most common words
    keywords = [word for word, _ in word_freq.most_common(num_keywords)]
    return keywords

def summarize_announcement(announcement, max_summary_length=3):
    content = announcement['content']
    sentences = content.split('.')
    
    # Extract keywords from the entire content
    keywords = extract_keywords(content)
    
    # Find sentences containing keywords
    relevant_sentences = []
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in keywords):
            relevant_sentences.append(sentence)
    
    # Limit the summary to max_summary_length sentences
    summary = '. '.join(relevant_sentences[:max_summary_length]) + '.'
    return summary.strip()

def process_announcements(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for announcement in data['announcements']:
            title = announcement['title']
            content = announcement['content']
            
            sentiment = analyze_sentiment(content)
            keywords = extract_keywords(content)
            summary = summarize_announcement(announcement)
            
            f.write(f"Title: {title}\n")
            f.write(f"Sentiment: {sentiment}\n")
            f.write(f"Keywords: {', '.join(keywords)}\n")
            f.write(f"Summary: {summary}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"Analysis results have been saved to {output_file}")

# Process the announcements
process_announcements('adgm_announcements.json', 'announcement_analysis.txt')