import ee
import requests

# Gibt das entsprechende Land zu einer Stadt zurück.
def get_country_from_city(city):
    print(f"Suche nach einem geeigneten Land für {city}")
    url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&addressdetails=1&lang=de"
    headers = {
        "User-Agent": "Lorem Ipsum"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    if data:
        return data[0]['address'].get('country', 'Unbekannt')
    return "Unbekannt"

# Gibt die Polygone einer Stadt zurück.
def get_polygons(city):

    try:
        headers = {
            "User-Agent": "MyApp/1.0 (myemail@example.com)"
        }
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "polygon_geojson": 1},
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if len(data) == 0:
            return None, "Kein Ort gefunden."

        geojson_polygon = data[0].get("geojson")
        bounding_box = data[0]["boundingbox"]

        if not geojson_polygon or "coordinates" not in geojson_polygon or not geojson_polygon["coordinates"]:
            # Fallback auf Bounding Box, falls GeoJSON-Daten fehlen
            print(f"Falle auf Bounding Box für {city} zurück.")
            lat_min, lat_max, lon_min, lon_max = map(float, bounding_box)
            polygon = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        else:
            if geojson_polygon["type"] == "MultiPolygon":
                coordinates = []
                # Iteriere durch alle Polygone und füge sie der Koordinatenliste hinzu
                for polygon in geojson_polygon["coordinates"]:
                    coordinates.append(polygon)
                # Erstelle das Polygon unter Verwendung aller Koordinaten
                try:
                    polygon = ee.Geometry.MultiPolygon(coordinates)
                except ee.ee_exception.EEException as e:
                    return None, f"Fehler bei der Geometrieerstellung: {e}"
            else:
                coordinates = geojson_polygon["coordinates"]
                try:
                    polygon = ee.Geometry.Polygon(coordinates)
                except ee.ee_exception.EEException as e:
                    return None, f"Fehler bei der Geometrieerstellung: {e}"

        # Mittelpunkt für die Karte berechnen
        lat_min, lat_max, lon_min, lon_max = map(float, bounding_box)
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2

        return {
            "polygon": polygon,
            "center": (center_lat, center_lon),
            "geojson": geojson_polygon,
        }, None
    except requests.exceptions.RequestException as e:
        return None, f"Fehler beim Abrufen der Koordinaten: {e}"
    
# Berechnet die Ränder einer Stadt
def calculate_bounds(geojson_data):
        coordinates = []
        
        #print("GeoJSON-Daten:", json.dumps(geojson_data, indent=2))
            
        if geojson_data["type"] == "Polygon":
            coordinates = geojson_data["coordinates"][0]
        elif geojson_data["type"] == "MultiPolygon":
            coordinates = [coord for polygon in geojson_data["coordinates"] for coord in polygon[0]]
        elif geojson_data["type"] == "MultiLineString":
            coordinates = [coord for line in geojson_data["coordinates"] for coord in line]
        else:
            raise ValueError("Unbekannter GeoJSON-Typ")

        # Finde die minimalen und maximalen Koordinaten (Bounds)
        min_lon = min(coord[0] for coord in coordinates)
        max_lon = max(coord[0] for coord in coordinates)
        min_lat = min(coord[1] for coord in coordinates)
        max_lat = max(coord[1] for coord in coordinates)
            
        if not coordinates:
            raise ValueError("Keine Koordinaten im GeoJSON gefunden.")
        
        latitudes = [coord[1] for coord in coordinates]
        longitudes = [coord[0] for coord in coordinates]
        
        min_lat = min(latitudes)
        max_lat = max(latitudes)
        min_lon = min(longitudes)
        max_lon = max(longitudes)
        return [[min_lat, min_lon], [max_lat, max_lon]]