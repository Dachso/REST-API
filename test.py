import requests

BASE_URL = "http://127.0.0.1:8000"

# TEST GET (all entries)
def get_all_entries():
    response = requests.get(f"{BASE_URL}/all-correspondences")
    if response.status_code == 200: # 200 => OK
        data = response.json()
        print("✅ Found all correspondences:")
        print(f"✅ {len(data['correspondence'])} Correspondences found:")
        for entry in data['correspondence']:
            print(f"- {entry['ID']}: {entry['Titel']} ({entry['Sprachen']})")
    else:
        print("❌ Error finding correspondences:", response.status_code, response.text)

# TEST GET (single entry)
def get_single_entry(entry_id):
    response = requests.get(f"{BASE_URL}/correspondence/{entry_id}")
    if response.status_code == 200: # 200 => OK
        data = response.json()
        print("✅ Found correspondence:")
        for key, value in data["correspondence"].items():
            print(f"  {key}: {value}")
    else:
        print("❌ Correspondence not found:", response.status_code, response.text)

# Test POST
def post_entry(signature, title, content, date, notes_on_date, extent, language, entry_id):
    new_entry = {
        "Signatur": signature,
        "Titel": title,
        "Form und Inhalt": content,
        "Entstehungszeitraum": date,
        "Bemerkungen zur Datierung": notes_on_date,
        "Bemerkungen zum Umfang": extent,
        "Sprachen":language,
        "ID": entry_id
    }

    response = requests.post(f"{BASE_URL}/correspondence", json=new_entry)

    if response.status_code == 201:
        print("✅ Correspondence created:")
        print(response.json())
    else:
        print("❌ Error during POST:", response.status_code)
        print(response.text)

# Test DELETE
def delete_entry(entry_id):
    response = requests.delete(f"{BASE_URL}/correspondence/{entry_id}")

    if response.status_code == 200:
        print("✅ Correspondence deleted:")
        print(response.json())
    elif response.status_code == 404:
        print("❌ Correspondence not found:", response.json()["detail"])
    else:
        print("❌ Error during DELETE:", response.status_code)
        print(response.text)


get_all_entries()
get_single_entry(42)
post_entry("B-I-EULER-1", "Thomas Mann an Leonhard Euler", "Fiktiver Brief über Mathematik und Literatur", "01.01.1901", "", "1 Bl./1 S.", "Deutsch", 9999)
post_entry("B-I-EULER-1", "Thomas Mann an Leonhard Euler", "Fiktiver Brief über Mathematik und Literatur", "01.01.1901", "", "1 Bl./1 S.", "Deutsch", 9999)
delete_entry(9999)