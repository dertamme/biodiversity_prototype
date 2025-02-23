# Skript wird genutzt, um die Metriken, Maps und Repots für die in data/standorte.json" gespeicherten Standorte zu berechnen.
# Wichtiges Skript

import json
import time
import ee
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from functions.crud import *
from functions.etc import *
from functions.paths import *
from functions.visualization import *

try:
    ee.Authenticate()
    ee.Initialize(project="bb-biodiv")
    print("Earth Engine API erfolgreich initialisiert!")
except Exception as e:
    print(f"Fehler: {e}")

geolocator = Nominatim(user_agent="location_finder")


# Jahre für die Berechnung
START_YEAR = 2017
END_YEAR = 2024

# Caches laden
ndvi_cache = load_cache(NDVI_CACHE)
ndbi_cache = load_cache(NDBI_CACHE)
ndwi_cache = load_cache(NDWI_CACHE)
green_cache = load_cache(GREEN_CACHE)
sealed_cache = load_cache(SEALED_CACHE)
water_cache = load_cache(WATER_CACHE)
unknown_cache = load_cache(UNKNOWN_CACHE)

def add_to_cache(cache, year, location, value):
    stadt, land = location.split(", ")
    cache.append({"Jahr": str(year), "Stadt": stadt, "Land": land, "value": str(value)})

def get_coordinates_raw(city, country):
    time.sleep(0.5)  
    try:
        location = geolocator.geocode(f"{city}, {country}")
        if location:
            return (location.latitude, location.longitude)
        else:
            print(f"Keine Koordinaten für {city}, {country} gefunden.")
            return None
    except GeocoderTimedOut:
        print(f"Zeitüberschreitung bei der Abfrage für {city}, {country}.")
        return None

# Standorte laden
with open("data/standorte.json", "r", encoding="utf-8") as f:
    standorte = json.load(f)

# Für jeden Standort die Werte berechnen
for standort in standorte:
    start_time = time.time()
    first_year = 9999
    stadt = standort["Stadt"]
    land = standort["Land"]
    firmen = ", ".join(standort["Firmen"])
    koordinaten_raw = standort.get("Koordinaten")
    location = f"{stadt}, {land}"
    print(f"\nBearbeite Standort: {location} (Firmen: {firmen})")

    # Koordinatenpunkt hinzufügen 
    if koordinaten_raw is None or koordinaten_raw == "Nicht gefunden":
        koordinaten = get_coordinates_raw(stadt, land)
        if koordinaten:
            standort["Koordinaten"] = koordinaten
        else:
            standort["Koordinaten"] = "Nicht gefunden"

        with open("data/standorte.json", "w", encoding="utf-8") as f:
            json.dump(standorte, f, indent=4, ensure_ascii=False)
            print(f"Koordinaten für {stadt}, {land} wurden in 'standorte.json' gespeichert.")
    
    # Polygon und Region abrufen
    result, error = get_polygons(location)
    if error or "polygon" not in result:
        print(f"Fehler beim Abrufen der Region für {location}: {error}")
        continue

    region = result["polygon"]

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

                # Gesamtfläche in Quadratmetern
                total_area = region.area().getInfo()

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
        
        end_time = time.time()
        duration = end_time - start_time
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Die Bearbeitung hat {int(hours):02}:{int(minutes):02}:{int(seconds):02} gebraucht.")

    else:    
        print(f"Der Eintrag für {location} kann nicht bearbeitet werden.")