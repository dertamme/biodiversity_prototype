#Skript wurde genutzt, um ein paar Statistiken bzgl der Entwicklung innerhalb der Kontinente zu berechnen.
#Kann gelöscht werden.
import json

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# Mapping von Ländern zu Regionen
REGION_MAPPING = {
    "Deutschland": "Europa",
    "Frankreich": "Europa",
    "Spanien": "Europa",
    "Italien": "Europa",
    "Niederlande": "Europa",
    "Belgien": "Europa",
    "Schweiz": "Europa",
    "Österreich": "Europa",
    "Polen": "Europa",
    "Portugal": "Europa",
    "Schweden": "Europa",
    "Norwegen": "Europa",
    "Finnland": "Europa",
    "Rumänien": "Europa",
    "Tschechien": "Europa",
    "Slowakei": "Europa",
    "Slowenien": "Europa",
    "Ungarn": "Europa",
    "Serbien": "Europa",
    "Vereinigtes Königreich": "Europa",
    "USA": "Nordamerika",
    "Kanada": "Nordamerika",
    "Mexiko": "Nordamerika",
    "Brasilien": "Südamerika",
    "Argentinien": "Südamerika",
    "Chile": "Südamerika",
    "Kolumbien": "Südamerika",
    "Peru": "Südamerika",
    "Venezuela": "Südamerika",
    "China": "Asien",
    "Indien": "Asien",
    "Japan": "Asien",
    "Südkorea": "Asien",
    "Indonesien": "Asien",
    "Vietnam": "Asien",
    "Malaysia": "Asien",
    "Singapur": "Asien",
    "Thailand": "Asien",
    "Philippinen": "Asien",
    "Taiwan": "Asien",
    "Hongkong": "Asien",
    "Kasachstan": "Asien",
    "Saudi Arabien": "Asien",
    "Vereinigte Arabische Emirate": "Asien",
    "Israel": "Asien",
    "Türkei": "Asien",
    "Russland": "Asien",
    "Ukraine": "Europa",
    "Weißrussland": "Europa",
    "Ägypten": "Afrika",
    "Kenia": "Afrika",
    "Marokko": "Afrika",
    "Algerien": "Afrika",
    "Australien": "Ozeanien",
    "Neuseeland": "Ozeanien",
    "Fidschi": "Ozeanien"
}

def calculate_percentage_change(data):
    changes_by_region = {region: [] for region in ["Europa", "Nordamerika", "Südamerika", "Asien", "Ozeanien", "Afrika"]}
    city_land_values = {}
    
    # Speichere Werte für 2023 und 2024
    for entry in data:
        if entry["value"] is None:
            continue
        year = entry["Jahr"]
        city_land = (entry["Stadt"], entry["Land"])
        region = REGION_MAPPING.get(entry["Land"], "Unbekannt")
        if year in ["2023", "2024"]:
            if city_land not in city_land_values:
                city_land_values[city_land] = {"region": region}
            city_land_values[city_land][year] = float(entry["value"])
    
    # Berechne die prozentuale Veränderung pro Region
    for city_land, years in city_land_values.items():
        if "2023" in years and "2024" in years:
            value_2023 = years["2023"]
            value_2024 = years["2024"]
            region = years["region"]
            if value_2023 != 0 and region in changes_by_region:  # Vermeidung einer Division durch Null
                change = ((value_2024 - value_2023) / value_2023) * 100
                changes_by_region[region].append(change)
    
    # Berechne den durchschnittlichen prozentualen Wandel pro Region
    for region, changes in changes_by_region.items():
        avg_change = sum(changes) / len(changes) if changes else 0
        print(f"Durchschnittliche prozentuale Veränderung in {region}: {avg_change:.2f}%")

if __name__ == "__main__":
    file_path = "data/green_cache.json"  # Ersetze dies mit dem tatsächlichen Dateipfad
    data = load_json(file_path)
    calculate_percentage_change(data)