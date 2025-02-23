import os

STANDORTE_JSON = "data/standorte.json"
NDVI_CACHE = "data/ndvi_cache.json"
NDWI_CACHE = "data/ndwi_cache.json"
NDBI_CACHE = "data/ndbi_cache.json"
GREEN_CACHE = "data/green_cache.json"
SEALED_CACHE = "data/sealed_cache.json"
WATER_CACHE = "data/water_cache.json"
UNKNOWN_CACHE = "data/unknown_cache.json"
dax_directory = "data/DAX/"
MAP_DIR = "data/maps"
EXPORT_MAPS_DIR = "data/maps/exports"

os.makedirs(MAP_DIR, exist_ok=True)
os.makedirs(EXPORT_MAPS_DIR, exist_ok=True)