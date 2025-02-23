import json
import ee
from functions.paths import NDVI_CACHE


# Funktion zur Berechnung des mittleren NDVI für ein gegebenes Jahr
def get_ndvi(year, region):
    start_date = f"{year}-05-01"
    end_date = f"{year}-08-31"

    # Funktion zur Wolkenmaskierung mit dem SCL-Band
    def mask_clouds(image):
        scl = image.select("SCL")
        cloud_mask = scl.neq(3).And(scl.neq(8))  # Maskiere Wolken (3) und Schatten (8)
        return image.updateMask(cloud_mask)

    # Sentinel-2-Daten filtern und verarbeiten
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")  # Sentinel-2 Oberflächenreflexionsdaten
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        .map(mask_clouds)  # Wolkenmaskierung anwenden
        .map(lambda image: image.normalizedDifference(["B8", "B4"]).rename("NDVI"))  # NDVI berechnen
        .sort("CLOUDY_PIXEL_PERCENTAGE")  # Nach Wolkenbedeckung sortieren
        .limit(20)  # Maximal 10 beste Bilder verwenden
    )

    # Anzahl der Bilder
    collection_size = collection.size().getInfo()
    print(f"Jahr: {year}, Anzahl der Bilder: {collection_size}. Berechnung des NDVI läuft...")

    if collection_size == 0:
        print(f"Warnung: Keine Daten für das Jahr {year}")
        return None

    # Berechnung des mittleren NDVI
    ndvi_image = collection.select("NDVI").mean().clip(region)
    
    return ndvi_image

# Funktion zur Berechnung des mittleren NDWI für ein gegebenes Jahr
def get_ndwi(year, region):
    start_date = f"{year}-05-01"
    end_date = f"{year}-08-31"

    # Funktion zur Wolkenmaskierung mit dem SCL-Band
    def mask_clouds(image):
        scl = image.select("SCL")
        cloud_mask = scl.neq(3).And(scl.neq(8))  # Maskiere Wolken (3) und Schatten (8)
        return image.updateMask(cloud_mask)

    # Sentinel-2-Daten filtern und verarbeiten
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")  # Sentinel-2 Oberflächenreflexionsdaten
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        .map(mask_clouds)  # Wolkenmaskierung anwenden
        .map(lambda image: image.normalizedDifference(["B3", "B8"]).rename("NDWI"))  # NDWI berechnen
        .sort("CLOUDY_PIXEL_PERCENTAGE")  # Nach Wolkenbedeckung sortieren
        .limit(20)  # Maximal 15 beste Bilder verwenden
    )

    # Anzahl der Bilder
    collection_size = collection.size().getInfo()
    print(f"Jahr: {year}, Anzahl der Bilder: {collection_size}. Berechnung des NDWI läuft...")

    if collection_size == 0:
        print(f"Warnung: Keine Daten für das Jahr {year}")
        return None

    # Berechnung des mittleren NDWI
    ndwi_image = collection.select("NDWI").mean().clip(region)
    
    return ndwi_image

# Funktion zur Berechnung des mittleren NDBI für ein gegebenes Jahr
def get_ndbi(year, region):
    start_date = f"{year}-05-01"
    end_date = f"{year}-08-31"

    # Funktion zur Wolkenmaskierung mit dem SCL-Band
    def mask_clouds(image):
        scl = image.select("SCL")
        cloud_mask = scl.neq(3).And(scl.neq(8))  # Maskiere Wolken (3) und Schatten (8)
        return image.updateMask(cloud_mask)

    # Sentinel-2-Daten filtern und verarbeiten
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")  # Sentinel-2 Oberflächenreflexionsdaten
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        .map(mask_clouds)  # Wolkenmaskierung anwenden
        .map(lambda image: image.normalizedDifference(["B11", "B8"]).rename("NDBI"))  # NDBI berechnen
        .sort("CLOUDY_PIXEL_PERCENTAGE")  # Nach Wolkenbedeckung sortieren
        .limit(20)  # Maximal 15 beste Bilder verwenden
    )

    # Anzahl der Bilder
    collection_size = collection.size().getInfo()
    print(f"Jahr: {year}, Anzahl der Bilder: {collection_size}. Berechnung des NDBI läuft...")

    if collection_size == 0:
        print(f"Warnung: Keine Daten für das Jahr {year}")
        return None

    # Berechnung des mittleren NDBI
    ndbi_image = collection.select("NDBI").mean().clip(region)
    
    return ndbi_image

# Berechnung von NDVI-Veränderungen. LOREM
def calculate_ndvi_development(locations):
    NDVI_CACHE_FILE = NDVI_CACHE
    with open(NDVI_CACHE_FILE, "r", encoding="utf-8") as f:
        ndvi_cache = json.load(f)
    """Berechnet die NDVI-Entwicklung von 2018 bis 2024 für die angegebenen Standorte eines Unternehmens."""
    ndvi_values_2018 = []
    ndvi_values_2024 = []

    for location in locations:
        city = location["Stadt"]
        country = location["Land"]

        # Suche NDVI-Werte für 2018 und 2024 im Cache
        for entry in ndvi_cache:
            if entry["Stadt"] == city and entry["Land"] == country:
                if entry["Jahr"] == "2018" and entry["value"] != "Keine Daten":
                    ndvi_values_2018.append(float(entry["value"]))
                if entry["Jahr"] == "2024" and entry["value"] != "Keine Daten":
                    ndvi_values_2024.append(float(entry["value"]))

    # Berechne den Durchschnitt für 2018 und 2024
    avg_2018 = sum(ndvi_values_2018) / len(ndvi_values_2018) if ndvi_values_2018 else None
    avg_2024 = sum(ndvi_values_2024) / len(ndvi_values_2024) if ndvi_values_2024 else None

    # Berechne die NDVI-Entwicklung
    if avg_2018 is not None and avg_2024 is not None:
        return round(avg_2024 - avg_2018, 4)
    return None

# Veränderungen berechnern LOREM
def calculate_change(changes):
    valid_changes = [float(c) for c in changes if isinstance(c, (int, float))]
    if len(valid_changes) < 2:
        raise ValueError("Nicht genügend gültige Werte für die Berechnung der Änderung.")
    return round(valid_changes[-1] - valid_changes[0], 7)

