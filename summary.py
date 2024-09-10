import json
from datetime import datetime

# Load the JSON data
with open('adgm_announcements.json', 'r') as f:
    announcements = json.load(f)

# Filter relevant announcements
regulatory_announcements = [
    a for a in announcements
    if a['authority'] in ['ADGM FSRA', 'ADGM RA'] or
    any(keyword in a['title'].lower() for keyword in ['regulatory', 'framework', 'consultation'])
]

# Sort announcements by date
regulatory_announcements.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y') if '/' in x['date'] else datetime.now(), reverse=True)

# Generate summary
summary = "Regulatory Update Summary:\n\n"

for announcement in regulatory_announcements:
    summary += f"- {announcement['title']} ({announcement['date']})\n"
    summary += f"  Link: {announcement['link']}\n\n"

print(summary)