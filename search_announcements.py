import json
import re

def load_announcements(filename='adgm_announcements.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def search_announcements(announcements, keywords, search_content=False):
    results = []
    for announcement in announcements:
        title = announcement['title'].lower()
        content = announcement['content'].lower() if search_content else ''
        
        if any(keyword.lower() in title or (search_content and keyword.lower() in content) for keyword in keywords):
            results.append(announcement)
    
    return results

def print_results(results):
    for result in results:
        print(f"Title: {result['title']}")
        print(f"Authority: {result['authority']}")
        print(f"Date: {result['date']}")
        print(f"Link: {result['link']}")
        print("Content preview:", result['content'][:200] + "..." if len(result['content']) > 200 else result['content'])
        print("-" * 80)

if __name__ == "__main__":
    announcements = load_announcements()
    
    while True:
        keywords = input("Enter keywords to search (comma-separated), or 'quit' to exit: ").split(',')
        if keywords[0].lower() == 'quit':
            break
        
        search_content = input("Search in content as well? (y/n): ").lower() == 'y'
        
        results = search_announcements(announcements, keywords, search_content)
        
        if results:
            print(f"\nFound {len(results)} matching announcements:")
            print_results(results)
        else:
            print("No matching announcements found.")
        
        print("\n")
