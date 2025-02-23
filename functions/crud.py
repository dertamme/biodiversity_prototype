import json
import os
import ee
import json
import os
import json

from functions.calculations import get_ndbi, get_ndvi, get_ndwi


from functions.etc import get_polygons
from functions.paths import GREEN_CACHE, NDBI_CACHE, NDVI_CACHE, NDWI_CACHE, SEALED_CACHE, UNKNOWN_CACHE, WATER_CACHE
from functions.visualization import generate_export_location_map, generate_location_pdf, generate_and_save_map



# Cache-Daten laden
def load_cache(filename):
    filepath = os.path.join(filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

#JSON-Dateien laden
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Funktion zum Überprüfen, ob ein Wert im Cache vorhanden ist
def get_cached_value(cache, year, city):
    
    # Splitte city in Stadt und optional Land
    parts = city.split(", ")
    stadt = parts[0]
    land = parts[1] if len(parts) > 1 else None

    for entry in cache:
        if entry["Jahr"] == str(year) and entry["Stadt"] == stadt:
            # Wenn das Land angegeben ist, berücksichtige es optional
            if land is None or entry.get("Land") == land:
                return float(entry["value"])
    return None

# Cache-Daten speichern
def save_cache(filename, data):
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                existing_data = json.load(file)
        # Speichern der kombinierten Daten
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern des Caches {filename}: {e}")

# Funktion zum Hinzufügen eines Werts zum Cache
def add_to_cache(cache, year, location, value):
    stadt, land = location.split(", ")
    for entry in cache:
        if entry["Jahr"] == str(year) and entry["Stadt"] == stadt and entry["Land"] == land:
            return  # Eintrag existiert bereits, nichts tun
    cache.append({"Jahr": str(year), "Stadt": stadt, "Land": land, "value": str(value)})

# Daten zu einer Location laden    
def get_city_data(city_name):
    green_data = load_json(GREEN_CACHE)
    ndvi_data = load_json(NDVI_CACHE)
    ndwi_data = load_json(NDWI_CACHE)
    ndbi_data = load_json(NDBI_CACHE)
    sealed_data = load_json(SEALED_CACHE)
    water_data = load_json(WATER_CACHE)
    unknown_data = load_json(UNKNOWN_CACHE)
    print(f"Suche Ergebnisse für {city_name}...")

    # Filtere Standortdaten
    def filter_data_by_city(data):
        return [entry for entry in data if entry["Stadt"].lower() == city_name.lower()]

    # Filtern der Daten für die Stadt
    ndvi_city_data = filter_data_by_city(ndvi_data)
    ndwi_city_data = filter_data_by_city(ndwi_data)
    ndbi_city_data = filter_data_by_city(ndbi_data)
    green_city_data = filter_data_by_city(green_data)
    sealed_city_data = filter_data_by_city(sealed_data)
    water_city_data = filter_data_by_city(water_data)
    unknown_city_data = filter_data_by_city(unknown_data)

    # Wenn keine Daten für die Stadt vorhanden sind, gebe None zurück
    if not green_city_data and not ndvi_city_data and not ndwi_city_data and not ndbi_city_data and not sealed_city_data and not water_city_data and not unknown_city_data :
        return None

    # Daten für die Stadt zurückgeben
    city_data = {
        "standort": city_name,
        "ndvi": ndvi_city_data,
        "ndwi": ndwi_city_data,
        "ndbi": ndbi_city_data,
        "green": green_city_data,
        "sealed": sealed_city_data,
        "water": water_city_data,
        "unknown": unknown_city_data,
    }

    return city_data

#Unternehmensnamen für Üebrsichtsstabelle
def get_dax_companies_and_ndvi(dax_directory="data/DAX", ndvi_file="data/ndvi_cache.json"):

    # Lade die NDVI-Daten
    with open(ndvi_file, "r", encoding="utf-8") as f:
        ndvi_data = json.load(f)

    # Funktion, um den NDVI-Wert für einen bestimmten Standort zu erhalten
    def get_ndvi_for_location(city, country, year="2024"):
        for entry in ndvi_data:
            if entry["Stadt"] == city and entry["Land"] == country and entry["Jahr"] == year:
                return float(entry["value"])
        return None

    # DAX-Unternehmen und ihre durchschnittlichen NDVI-Werte
    companies_info = []

    for filename in os.listdir(dax_directory):
        if filename.endswith(".json"):
            # Unternehmensname formatieren
            name_without_extension = os.path.splitext(filename)[0]
            company_name = name_without_extension.replace("_", " ").title()

            # Lade die Unternehmensstandorte
            with open(os.path.join(dax_directory, filename), "r", encoding="utf-8") as f:
                locations = json.load(f)

            # NDVI-Werte für die Standorte sammeln
            ndvi_values = []
            for location in locations:
                city = location["Stadt"]
                country = location["Land"]
                ndvi = get_ndvi_for_location(city, country)
                if ndvi is not None:
                    ndvi_values.append(ndvi)

            # Durchschnittlichen NDVI berechnen
            avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 4) if ndvi_values else "Keine Daten"

            companies_info.append({
                "name": company_name,
                "average_ndvi": avg_ndvi
            })

    return companies_info

# Berechnet und speichert die Daten eines neuen Standortes
def addCity(region, city, land, ndwi_cache, ndvi_cache, ndbi_cache, green_cache, water_cache, sealed_cache, unknown_cache):
    START_YEAR = 2016
    END_YEAR = 2024
    first_year = 9999
    stadt = city
    land = land
    firmen = ""
    location = f"{stadt}, {land}"
    print(f"\nBearbeite Standort: {location} (Firmen: {firmen})")

    # Polygon und Region abrufen
    result, error = get_polygons(location)
    if error or "polygon" not in result:
        print(f"Fehler beim Abrufen der Region für {location}: {error}")
        return

    # Werte für jedes Jahr berechnen
    for year in range(START_YEAR, END_YEAR + 1):
        print(f"\n  -> Berechne Werte für Jahr {year}...")

        # Überprüfen, ob Werte im Cache vorhanden sind
        ndvi_value = get_cached_value(ndvi_cache, year, location)
        ndwi_value = get_cached_value(ndwi_cache, year, location)
        ndbi_value = get_cached_value(ndbi_cache, year, location)
        green_value = get_cached_value(green_cache, year, location)
        sealed_value = get_cached_value(sealed_cache, year, location)
        water_value = get_cached_value(water_cache, year, location)
        unknown_value = get_cached_value(unknown_cache, year, location)

        # Falls nicht im Cache, berechne die Werte
        if ndvi_value is None or ndwi_value is None or ndbi_value is None or green_value is None or sealed_value is None or unknown_value is None:
            try:
                ndvi_image = get_ndvi(year, region)
                ndwi_image = get_ndwi(year, region)
                ndbi_image = get_ndbi(year, region)

                # Überspringen, wenn keine Satelitenbilder vorhanden sind
                if ndvi_image is None or ndwi_image is None or ndbi_image is None:
                    print(f"    Keine Bilder für {location} im Jahr {year}. Überspringe...")
                    continue

                # NDVI berechnen
                ndvi_value = ndvi_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDVI")

                # NDWI berechnen
                ndwi_value = ndwi_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDWI")

                # NDBI berechnen
                ndbi_value = ndbi_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDBI")

                # Überspringen, wenn NDVI oder NDWI oder NDBI nicht berechnet werden konnte
                if ndvi_value is None or ndwi_value is None or ndbi_value is None:
                    print(f"    Keine gültigen NDVI/NDWI/NDBI-Werte für {location} im Jahr {year}. Überspringe...")
                    continue

                # Gesamtfläche berechnen
                total_area = region.area().getInfo()  # Gesamtfläche in Quadratmetern

# Grünflächen berechnen (prozentualer Anteil)
                green_area = ndvi_image.gte(0.3).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDVI", 0)
                green_percentage = (green_area / total_area) * 100

                # Versiegelte Flächen berechnen (prozentualer Anteil)
                sealed_area = ndbi_image.gt(-0.05).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDBI", 0)
                sealed_percentage = (sealed_area / total_area) * 100

                # Wasserflächen berechnen (prozentualer Anteil)
                water_area = ndwi_image.gt(0.0).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDWI", 0)
                water_percentage = (water_area / total_area) * 100

                # Überlappung zwischen grün und versiegelt
                green_sealed_overlap = ndvi_image.gte(0.3).And(ndbi_image.gt(-0.05)).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDVI", 0)

                # Überlappung zwischen grün und wasser
                green_water_overlap = ndvi_image.gte(0.3).And(ndwi_image.gt(0.0)).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDVI", 0)

                # Überlappung zwischen versiegelt und wasser
                sealed_water_overlap = ndbi_image.gt(-0.05).And(ndwi_image.gt(0.0)).multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e13
                ).getInfo().get("NDBI", 0)

                # Berechnungen der Flächen ohne Überlappung
                green_percentage -= (green_sealed_overlap / total_area) * 100
                green_percentage -= (green_water_overlap / total_area) * 100

                sealed_percentage -= (green_sealed_overlap / total_area) * 100
                sealed_percentage -= (sealed_water_overlap / total_area) * 100

                water_percentage -= (green_water_overlap / total_area) * 100
                water_percentage -= (sealed_water_overlap / total_area) * 100

                # Alles, was nicht eindeutig ist, fließt in "unknown" ein
                unknown_percentage = 100 - green_percentage - sealed_percentage - water_percentage

                # Sicherstellen, dass der Prozentsatz für unknown nicht negativ wird
                if unknown_percentage < 0:
                    unknown_percentage = 0


                # Ergebnisse in den Cache speichern
                add_to_cache(ndvi_cache, year, location, ndvi_value)
                add_to_cache(ndwi_cache, year, location, ndwi_value)
                add_to_cache(ndbi_cache, year, location, ndbi_value)
                add_to_cache(green_cache, year, location, green_percentage)
                add_to_cache(sealed_cache, year, location, sealed_percentage)
                add_to_cache(water_cache, year, location, water_percentage)
                add_to_cache(unknown_cache, year, location, unknown_percentage)

                # Caches speichern
                save_cache(NDVI_CACHE, ndvi_cache)
                save_cache(NDWI_CACHE, ndwi_cache) 
                save_cache(NDBI_CACHE, ndbi_cache)
                save_cache(GREEN_CACHE, green_cache)
                save_cache(SEALED_CACHE, sealed_cache)
                save_cache(WATER_CACHE, water_cache)
                save_cache(UNKNOWN_CACHE, unknown_cache)               

                if first_year > year:
                    first_year = year

            except Exception as e:
                print(f"    Fehler bei der Berechnung für {location} im Jahr {year}: {e}")
                continue

        if first_year > year:
            first_year = year

    if first_year < 9999:
        generate_and_save_map(f"data/maps/{stadt}_{land}_map.html", result, first_year, END_YEAR, region, get_ndvi, get_ndwi, get_ndbi)
        generate_export_location_map(stadt, result, region)
        ndwi_changes = []
        ndvi_changes = []
        ndbi_changes = []        
        green_changes = []
        sealed_changes = []
        water_changes = []
        unknown_changes = []       
        for year in range(int(2017), int(2025)):
            ndwi_value = get_cached_value(ndwi_cache, year, stadt)
            ndvi_value = get_cached_value(ndvi_cache, year, stadt)
            ndbi_value = get_cached_value(ndbi_cache, year, stadt)
            green_value = get_cached_value(green_cache, year, stadt)
            sealed_value = get_cached_value(sealed_cache, year, stadt)
            water_value = get_cached_value(water_cache, year, stadt)
            unknown_value = get_cached_value(unknown_cache, year, stadt)
            ndwi_changes.append(ndwi_value)
            ndvi_changes.append(ndvi_value)
            ndbi_changes.append(ndbi_value)
            green_changes.append(green_value)
            sealed_changes.append(sealed_value)
            water_changes.append(water_value)
            unknown_changes.append(unknown_value)
        generate_location_pdf(stadt, ndvi_changes, ndwi_changes, ndbi_changes, green_changes, sealed_changes, water_changes, unknown_changes)
        print(f"\nBearbeiung für {location} abgeschlossen.")
    else:    
        print(f"Der Eintrag für {location} kann nicht bearbeitet werden.")

