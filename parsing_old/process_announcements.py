import spacy
from gensim import corpora
from gensim.models import LdaModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import json
import sys

# Load spacy model
nlp = spacy.load("en_core_web_sm")

# Function to preprocess text
def preprocess_text(text):
    doc = nlp(text)
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    print("Tokens:", tokens)  # Debug print
    return ' '.join(tokens)

# Function to extract entities from text
def extract_entities(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

# Function to perform topic modeling
def perform_topic_modeling(texts, num_topics=5):
    # Tokenize and preprocess each announcement
    tokenized_texts = [preprocess_text(text).split() for text in texts]
    tokenized_texts = [text for text in tokenized_texts if text]  # Filter out empty texts
    if not tokenized_texts:
        raise ValueError("No valid texts for topic modeling")

    dictionary = corpora.Dictionary(tokenized_texts)
    corpus = [dictionary.doc2bow(text) for text in tokenized_texts]

    # Create the LDA model
    lda_model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=10)
    topics = lda_model.print_topics(num_words=5)
    return topics

# Function to find similar documents based on TF-IDF and cosine similarity
def find_similar_documents(texts):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix

# Function to summarize text using HuggingFace's transformer pipeline
summarizer = pipeline("summarization")
def summarize_text(text):
    summary = summarizer(text, max_length=100, min_length=30, do_sample=False)
    return summary[0]['summary_text']

# Main function to run all tasks on a JSON file containing announcements
def process_announcements(json_file):
    with open(json_file, 'r') as f:
        announcements = json.load(f)

    texts = [ann['content'] for ann in announcements]  # Assuming 'content' holds the main announcement text
    
    # Print out the texts for debugging
    print("Extracted Texts:")
    for text in texts:
        print(text)
    
    # Preprocess texts
    preprocessed_texts = [preprocess_text(text) for text in texts]

    # Print out preprocessed texts for debugging
    print("Preprocessed Texts:")
    for text in preprocessed_texts:
        print(text)
    
    # Extract entities for each announcement
    all_entities = [extract_entities(text) for text in texts]

    # Perform topic modeling
    topics = perform_topic_modeling(texts)

    # Find similar documents
    similarity_matrix = find_similar_documents(texts)

    # Summarize each announcement
    summaries = [summarize_text(text) for text in texts]

    # Structure the results
    results = []
    for i, ann in enumerate(announcements):
        result = {
            "title": ann.get('title', 'No Title'),
            "content": ann['content'],
            "preprocessed": preprocessed_texts[i],
            "entities": all_entities[i],
            "summary": summaries[i]
        }
        results.append(result)

    return results, topics, similarity_matrix

# Entry point for command-line execution
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_announcements.py <json_file>")
        sys.exit(1)

    json_file = sys.argv[1]
    results, topics, similarity_matrix = process_announcements(json_file)

    # Optionally, print or save results
    print("Results:")
    for result in results:
        print(result)
    print("Topics:")
    for topic in topics:
        print(topic)
    print("Similarity Matrix:")
    print(similarity_matrix)
