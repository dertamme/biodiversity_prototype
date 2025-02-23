# Skript wurde genutzt um zu prüfen, wie die Metrik-Veränderungen innerhalb eienr Zeitspanne war. 
#Kann gelöscht werden.
import json


# Funktion, um die Daten aus den Cache-Dateien zu laden
def load_cache(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Funktion, um die Veränderungen (2021-2024) für die entsprechenden Werte zu berechnen
def calculate_change(data, city, year_start, year_end):
    value_start = None
    value_end = None
    for entry in data:
        if entry["Stadt"] == city and entry["Jahr"] == str(year_start):
            value_start = float(entry["value"])
        elif entry["Stadt"] == city and entry["Jahr"] == str(year_end):
            value_end = float(entry["value"])
    if value_start is not None and value_end is not None:
        return value_end - value_start
    return None

# Standorte laden
with open("data/standorte.json", "r", encoding="utf-8") as file:
    locations = json.load(file)

# Daten für NDVI, NDWI, NDBI laden
ndvi_data = load_cache("data/ndvi_cache.json")
ndwi_data = load_cache("data/ndwi_cache.json")
ndbi_data = load_cache("data/ndbi_cache.json")

# Listen für die Veränderungen
ndvi_changes = []
ndwi_changes = []
ndbi_changes = []

# Berechnungen der Veränderungen und Sammlung der Standorte
for location in locations:
    city = location["Stadt"]
    country = location["Land"]

    # Veränderung für NDVI, NDWI, NDBI berechnen
    ndvi_change = calculate_change(ndvi_data, city, 2020, 2024)
    ndwi_change = calculate_change(ndwi_data, city, 2020, 2024)
    ndbi_change = calculate_change(ndbi_data, city, 2020, 2024)

    # Wenn eine Veränderung existiert, in die Listen aufnehmen
    if ndvi_change is not None:
        ndvi_changes.append({"Stadt": city, "Land": country, "NDVI_Veränderung": ndvi_change})
    if ndwi_change is not None:
        ndwi_changes.append({"Stadt": city, "Land": country, "NDWI_Veränderung": ndwi_change})
    if ndbi_change is not None:
        ndbi_changes.append({"Stadt": city, "Land": country, "NDBI_Veränderung": ndbi_change})

# Listen nach Veränderung absteigend sortieren
ndvi_changes.sort(key=lambda x: x["NDVI_Veränderung"], reverse=True)
ndwi_changes.sort(key=lambda x: x["NDWI_Veränderung"], reverse=True)
ndbi_changes.sort(key=lambda x: x["NDBI_Veränderung"], reverse=True)

# Ausgabe als JSON-Dateien
with open("ndvi_changes_sorted.json", "w", encoding="utf-8") as file:
    json.dump(ndvi_changes, file, ensure_ascii=False, indent=4)

with open("ndwi_changes_sorted.json", "w", encoding="utf-8") as file:
    json.dump(ndwi_changes, file, ensure_ascii=False, indent=4)

with open("ndbi_changes_sorted.json", "w", encoding="utf-8") as file:
    json.dump(ndbi_changes, file, ensure_ascii=False, indent=4)

print("Die JSON-Dateien wurden erstellt und gespeichert.")
