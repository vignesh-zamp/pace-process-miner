import requests
import json
import urllib.parse

BASE_URL = "http://localhost:8000"

def test_history():
    print("Fetching documents list...")
    res = requests.get(f"{BASE_URL}/documents")
    if res.status_code != 200:
        print(f"Failed to list documents: {res.text}")
        return

    data = res.json()
    documents = data.get("documents", [])
    print(f"Found {len(documents)} documents.")
    
    if not documents:
        return

    first_doc = documents[0]
    print(f"First Doc: {json.dumps(first_doc, indent=2)}")
    
    # Simulate frontend path construction
    # relativePath = `${doc.company}/${doc.filename}`
    company = first_doc['company']
    filename = first_doc['filename']
    relative_path = f"{company}/{filename}"
    
    print(f"Constructed Relative Path: {relative_path}")
    
    encoded_path = urllib.parse.quote(relative_path)
    url = f"{BASE_URL}/document?path={encoded_path}"
    print(f"Requesting: {url}")
    
    res = requests.get(url)
    if res.status_code == 200:
        print("Success! Content length:", len(res.json().get("content", "")))
    else:
        print(f"Failed to read document: {res.status_code} - {res.text}")

if __name__ == "__main__":
    test_history()
