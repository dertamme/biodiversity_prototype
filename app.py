import glob
import json
import os
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for
import ee
from prompt_toolkit import HTML
from functions.calculations import calculate_ndvi_development
from functions.crud import *
from functions.etc import *
from functions.paths import *
from functions.visualization import *


try:
    create_big_map()
    ee.Authenticate()
    ee.Initialize(project="bb-biodiv")
    print("Earth Engine API erfolgreich initialisiert!")
except Exception as e:
    print(f"Fehler: {e}")



app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Fehler: {e}")
    return render_template("error.html", error_message="Ein unerwarteter Fehler ist aufgetreten."), 500

@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", error_message="Seite nicht gefunden."), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("error.html", error_message="Interner Serverfehler."), 500

@app.errorhandler(400)
def internal_server_error(error):
    return render_template("error.html", error_message="Ungültige Anfrage. Typfehler vermutet."), 400


@app.route("/", methods=["GET", "POST"])
def index():
    return redirect(url_for('summary'))

@app.route("/summary", methods=["GET", "POST"])
def summary():
    
    logo_directory = "static/img/"
    dax_files = [{"name": os.path.splitext(file)[0]} for file in os.listdir(dax_directory) if file.endswith(".json")]
    NDVI_CACHE_FILE = "data/ndvi_cache.json"
    with open(NDVI_CACHE_FILE, "r", encoding="utf-8") as f:
        ndvi_cache = json.load(f)
    # Lade Unternehmensstandorte aus den JSON-Dateien
    dax_dir = dax_directory
    companies = []
    dax_files = []

    for file in os.listdir(dax_dir):
        if file.endswith(".json"):
            with open(os.path.join(dax_dir, file), "r", encoding="utf-8") as f:
                locations = json.load(f)
                company_name = file.replace("_", " ").replace(".json", "").title()
                
                # Berechne den durchschnittlichen NDVI für 2024
                ndvi_values = [
                    float(entry["value"]) for entry in ndvi_cache
                    if any(entry["Stadt"] == loc["Stadt"] and entry["Land"] == loc["Land"] and entry["Jahr"] == "2024" for loc in locations)
                ]
                avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 4) if ndvi_values else "Keine Daten"

                # Berechne die NDVI-Entwicklung von 2018 bis 2024
                ndvi_development = calculate_ndvi_development(locations)

                companies.append({
                    "name": company_name,
                    "average_ndvi": avg_ndvi,
                    "ndvi_development": ndvi_development if ndvi_development is not None else "Keine Daten"
                })
                simplified_name = company_name.split()[0]

                companies = sorted(companies, key=lambda x: x["name"])

                dax_files.sort(key=lambda x: x["name"].lower())

    # Karte einlesen
    with open("templates/map_big.html", "r", encoding="utf-8") as f:
        map_big = f.read()

    return render_template("summary.html", map_big=map_big, companies=companies, dax_files=dax_files)

@app.route("/standortanalyse", methods=["GET"])
def standortanalyse_dashboard():
    return render_template(
        "standort.html",
        city=None,
        years=[],
        ndvi_changes=[],
        ndwi_changes=[], 
        ndbi_changes=[],        
        green_changes=[],
        sealed_changes=[],
        unknown_changes=[],
        ndvi_change=None,
        ndwi_change=None,
        ndbi_change=None,
        land_cover_changes={"green": None, "sealed": None, "unknown": None},
        map_html=None,
        is_city_provided=False  

    )

@app.route("/standortanalyse/<city>", methods=["GET"])
def standortanalyse(city):
    ndvi_change = None
    ndwi_change = None
    ndbi_change = None
    land_cover_changes = {"green": "Keine Daten", "sealed": "Keine Daten", "water": "Keine Daten", "unknown": "Keine Daten"}
    map_html = None
    start_year=2017
    end_year = 2024

    # Caches laden
    ndvi_cache = load_cache(NDVI_CACHE)
    ndwi_cache = load_cache(NDWI_CACHE)
    ndbi_cache = load_cache(NDBI_CACHE)
    green_cache = load_cache(GREEN_CACHE)
    sealed_cache = load_cache(SEALED_CACHE)
    water_cache = load_cache(WATER_CACHE)
    unknown_cache = load_cache(UNKNOWN_CACHE)

    # Initialisierung der Variablen
    ndvi_changes = []
    ndwi_changes = []
    ndbi_changes = []
    green_changes = []
    sealed_changes = []
    water_changes = []
    unknown_changes = []

    city_data = get_city_data(city)
    
    if not city:
        return render_template(
            "standort.html",
            city=city,
            years=list(range(2017, 2024)),
            ndvi_changes=ndvi_changes,
            ndwi_changes=ndwi_changes,
            ndbi_changes=ndbi_changes,           
            green_changes=green_changes,
            sealed_changes=sealed_changes,
            water_changes=water_changes,
            unknown_changes=unknown_changes,
            ndvi_change=ndvi_change,
            ndwi_change=ndwi_change,
            ndbi_change=ndbi_change,
            land_cover_changes=land_cover_changes,
            map_html=map_html,
            is_city_provided=False  
        )
    if not city_data :
        print(f"Keine Werte für {city} gefunden. Neue Werte werden berechnet.")

        result = get_polygons(city)
       
        if result == (None, 'Kein Ort gefunden.'):
            print("Error!")
            return render_template("error.html"), 404
        region = result[0]["polygon"]
        land = get_country_from_city(city)
        addCity(region, city, land, ndwi_cache, ndvi_cache, ndbi_cache, green_cache, water_cache, sealed_cache, unknown_cache)

        # Schleife erneut ausführen, um die neu berechneten Werte zu laden
        ndvi_changes.clear()
        ndwi_changes.clear()
        ndbi_changes.clear()
        green_changes.clear()
        sealed_changes.clear()
        unknown_changes.clear()

        for year in range(int(2017), int(2024)):
            ndvi_value = get_cached_value(ndvi_cache, year, city)
            ndwi_value = get_cached_value(ndwi_cache, year, city)
            ndbi_value = get_cached_value(ndbi_cache, year, city)
            green_value = get_cached_value(green_cache, year, city)
            sealed_value = get_cached_value(sealed_cache, year, city)
            unknown_value = get_cached_value(unknown_cache, year, city)

            ndvi_changes.append(ndvi_value)
            ndwi_changes.append(ndwi_value)
            ndbi_changes.append(ndbi_value)
            green_changes.append(green_value)
            sealed_changes.append(sealed_value)
            unknown_changes.append(unknown_value)

    print(f"Daten für {city} geladen.")

    city_data = get_city_data(city)

    # Extrahiere Diagramm- und Kartendaten
    years = [entry["Jahr"] for entry in city_data["green"]]
    print(years)
    start_year = min(years)
    end_year =max(years)
    ndvi_changes = [round(float(entry["value"]), 4) for entry in city_data["ndvi"] if 2017 <= int(entry["Jahr"]) <= 2024]
    ndwi_changes = [round(float(entry["value"]), 4) for entry in city_data["ndwi"] if 2017 <= int(entry["Jahr"]) <= 2024]
    ndbi_changes = [round(float(entry["value"]), 4) for entry in city_data["ndbi"] if 2017 <= int(entry["Jahr"]) <= 2024]
    green_changes = [round(float(entry["value"]), 4) for entry in city_data["green"] if 2017 <= int(entry["Jahr"]) <= 2024]
    water_changes = [round(float(entry["value"]), 4) for entry in city_data["water"] if 2017 <= int(entry["Jahr"]) <= 2024]
    sealed_changes = [round(float(entry["value"]), 4) for entry in city_data["sealed"] if 2017 <= int(entry["Jahr"]) <= 2024]
    unknown_changes = [round(float(entry["value"]), 4) for entry in city_data["unknown"] if 2017 <= int(entry["Jahr"]) <= 2024]

    # Berechne Veränderungen
    ndvi_change = round(ndvi_changes[-1] - ndvi_changes[0], 4) if len(ndvi_changes) > 1 else None
    ndwi_change = round(ndwi_changes[-1] - ndwi_changes[0], 4) if len(ndwi_changes) > 1 else None
    ndbi_change = round(ndbi_changes[-1] - ndbi_changes[0], 4) if len(ndbi_changes) > 1 else None
    green_change = round(green_changes[-1] - green_changes[0], 4) if len(green_changes) > 1 else None
    sealed_change = round(sealed_changes[-1] - sealed_changes[0], 4) if len(sealed_changes) > 1 else None
    water_change = round(water_changes[-1] - water_changes[0], 4) if len(water_changes) > 1 else None
    unknown_change = round(unknown_changes[-1] - unknown_changes[0], 4) if len(unknown_changes) > 1 else None

    # Erstelle land_cover_changes
    land_cover_changes = {
        "green": green_change,
        "sealed": sealed_change,
        "water": water_change,
        "unknown": unknown_change
    }

    # Daten pro Jahr überprüfen und berechnen
    for year in range(int(start_year), int(end_year)):
        # Cache überprüfen
        ndvi_value = get_cached_value(ndvi_cache, year, city)
        ndwi_value = get_cached_value(ndwi_cache, year, city)
        ndbi_value = get_cached_value(ndbi_cache, year, city)
        green_value = get_cached_value(green_cache, year, city)
        sealed_value = get_cached_value(sealed_cache, year, city)
        water_value = get_cached_value(water_cache, year, city)
        unknown_value = get_cached_value(unknown_cache, year, city)

        # Werte zur Anzeige speichern
        ndvi_changes.append(ndvi_value)
        ndwi_changes.append(ndwi_value)
        ndbi_changes.append(ndbi_value)
        green_changes.append(green_value)
        sealed_changes.append(sealed_value)
        water_changes.append(water_value)
        unknown_changes.append(unknown_value)

    # Map laden
    try:
        pattern = f"data/maps/{city}_*"
        matching_files = glob.glob(pattern)
        if matching_files:
            filename = matching_files[0]
        else:
            print("Keine Passende Karte gefunden, eine neue wird erstellt...")
            land = get_country_from_city(city)
            location = f"{city}, {land}"
            result, error = get_polygons(location)
            region = result['polygon']
            filename = f"data/maps/{city}_{land}_Map.html"
            generate_and_save_map(str(filename), result, int(start_year), int(end_year), region, get_ndvi, get_ndwi, get_ndbi)
    except Exception as e:
        print(f"Fehler bei der Karten-Generierung: {e}")
        map_html = None


    with open(filename, "r") as f:
        map_html = f.read()

    return render_template(
        "standort.html",
        city=city,
        years=years,
        start_year = start_year,
        end_year = 2024,
        ndvi_changes=ndvi_changes,
        ndwi_changes=ndwi_changes,
        ndbi_changes=ndbi_changes,
        green_changes=green_changes,
        water_changes=water_changes,
        sealed_changes=sealed_changes,
        unknown_changes=unknown_changes,
        ndvi_change=ndvi_change,
        ndwi_change=ndwi_change,
        ndbi_change=ndbi_change,
        land_cover_changes=land_cover_changes,
        map_html=map_html,
        is_city_provided=True  
    )
    
@app.route("/api/standorte", methods=["GET"])
def api_standorte():
    standorte = load_json(STANDORTE_JSON)
    return jsonify(standorte)

@app.route("/unternehmen", methods=["GET", "POST"])
def unternehmen():
    company_name = ""
    if request.method == "POST":
        # Wenn ein Unternehmensname im Suchfeld eingegeben wurde
        company_name = request.form.get('companySearch').strip()  # Zugriff auf das Eingabefeld
        
    return render_template("unternehmen.html", company_name=company_name)

@app.route("/unternehmen/<unternehmen_name>")
def unternehmen_detail(unternehmen_name):
    formatted_name = unternehmen_name.replace("_", " ")
    return render_template("unternehmen.html", company_name=formatted_name)

@app.route("/api/location/suggest", methods=["GET"])
def suggest_location():
    query = request.args.get("query", "").lower()

    try:
        with open("data/ndvi_cache.json", "r", encoding="utf-8") as f:
            ndvi_data = json.load(f)
    except Exception as e:
        return jsonify({"error": "Failed to load NDVI data."}), 500

    # Doubletten entfernen
    seen = set()
    starts_with_city_query = []
    starts_with_country_query = []
    contains_query = []

    
    for entry in ndvi_data:
        city = entry["Stadt"]
        country = entry["Land"]

        city_country = f"{city}, {country}"

        # Suche zuerst nach Städten
        if query in city.lower():
            if city.lower().startswith(query) and city_country not in seen:
                starts_with_city_query.append({"city": city, "country": country})
                seen.add(city_country)
        # Suche danach nach Ländern
        elif query in country.lower():
            if country.lower().startswith(query) and city_country not in seen:
                starts_with_country_query.append({"city": city, "country": country})
                seen.add(city_country)
        # Wenn die Eingabe irgendwo im Stadt- oder Ländernamen enthalten ist
        elif city_country not in seen and (query in city.lower() or query in country.lower()):
            contains_query.append({"city": city, "country": country})
            seen.add(city_country)

    # Sortiere die Listen alphabetisch (nur die, die die Eingabe nicht beginnen)
    contains_query.sort(key=lambda x: f"{x['city']} {x['country']}")

    #Zuerst die, die mit der Eingabe beginnen (Stadt zuerst, dann Land), danach alphabetisch
    suggestions = starts_with_city_query + starts_with_country_query + contains_query

    return jsonify(suggestions)

@app.route("/api/suggest", methods=["GET"])
def suggest():
    query = request.args.get("query", "").lower()
    companies = get_dax_companies_and_ndvi()

    company_names = [company["name"] for company in companies]

    # Sortieren: Zuerst die Unternehmen, die mit der Eingabe beginnen, dann die, die die Eingabe enthalten
    starts_with_query = [name for name in company_names if name.lower().startswith(query)]
    contains_query = [name for name in company_names if query in name.lower() and not name.lower().startswith(query)]

    # Zuerst die, die mit der Eingabe beginnen, dann die anderen
    suggestions = starts_with_query + contains_query

    return jsonify(suggestions)

@app.route("/api/company_locations", methods=["GET"])
def get_company_locations():
    company_name = request.args.get("name")
    print(f"Received company name: '{company_name}'")
    
    
    ndvi_file = "data/ndvi_cache.json"
    standorte_file = "data/standorte.json"

    # NDVI-Daten laden
    try:
        with open(ndvi_file, "r", encoding="utf-8") as f:
            ndvi_data = json.load(f)
        print(f"Loaded {len(ndvi_data)} NDVI entries.")
    except Exception as e:
        print(f"Error loading NDVI file: {e}")
        return jsonify({"error": "Failed to load NDVI data."}), 500

    # Standortdaten laden
    try:
        with open(standorte_file, "r", encoding="utf-8") as f:
            standorte_data = json.load(f)
        print(f"Loaded {len(standorte_data)} location entries.")
    except Exception as e:
        print(f"Error loading standorte file: {e}")
        return jsonify({"error": "Failed to load location data."}), 500

    # DAX-Dateien durchsuchen
    for filename in os.listdir(dax_directory):
        if filename.endswith(".json"):
            name_without_extension = os.path.splitext(filename)[0]
            formatted_name = name_without_extension.replace("_", " ").title()
            print(f"Checking DAX file: '{formatted_name}' against '{company_name}'")

            if formatted_name.strip().lower() == company_name.strip().lower():
                print(f"Match found: '{formatted_name}'")
                try:
                    with open(os.path.join(dax_directory, filename), "r", encoding="utf-8") as f:
                        locations = json.load(f)
                    print(f"Loaded {len(locations)} locations for '{company_name}'")
                except Exception as e:
                    print(f"Error loading company file '{filename}': {e}")
                    return jsonify({"error": f"Failed to load company data for {company_name}."}), 500

                # Liste der Standorte mit NDVI-Werten
                location_data = []
                for loc in locations:
                    city = loc["Stadt"]
                    country = loc["Land"]

                    # NDVI-Wert für den Standort suchen
                    ndvi = next(
                        (float(entry["value"]) for entry in ndvi_data if entry["Stadt"] == city and entry["Land"] == country and entry["Jahr"] == "2024"),
                        None
                    )
                    # NDVI-Änderung (2018-2024) berechnen
                    ndvi_change = None
                    ndvi_2018 = next(
                        (float(entry["value"]) for entry in ndvi_data if entry["Stadt"] == city and entry["Land"] == country and entry["Jahr"] == "2018"),
                        None
                    )
                    if ndvi is not None and ndvi_2018 is not None:
                        ndvi_change = round(ndvi - ndvi_2018, 4)

                    # Koordinaten aus den Standortdaten laden
                    koordinaten = next(
                        (standort["Koordinaten"] for standort in standorte_data if standort["Stadt"] == city and standort["Land"] == country),
                        None
                    )

                    if koordinaten:
                        location_data.append({
                            "company_name":loc["Unternehmen"],
                            "city": city,
                            "country": country,
                            "latitude": koordinaten[0],
                            "longitude": koordinaten[1],
                            "ndvi": ndvi,
                            "ndvi_change": ndvi_change if ndvi_change is not None else "Keine Daten"

                        })
                return jsonify({"locations": location_data})
                

    print("No matching company found.")
    return jsonify({"locations": []})

@app.route("/api/company_information", methods=["GET"])
def get_company_information():
    company_name = request.args.get("name")
    print(f"Information API received company name: '{company_name}'")
    
    information_file = "data/information.json"

    # Informationen laden
    try:
        with open(information_file, "r", encoding="utf-8") as f:
            company_data = json.load(f)
        print(f"Loaded information for {len(company_data)} companies.")
    except Exception as e:
        print(f"Error loading information file: {e}")
        return jsonify({"error": "Failed to load company information."}), 500

    # Firma suchen
    for company in company_data:
        if company["Unternehmen"].strip().lower() == company_name.strip().lower():
            print(f"Match found: '{company['Unternehmen']}'")
            return jsonify({
                "Unternehmen": company["Unternehmen"],
                "Branche": company["Branche"],
                "Mitarbeitende": company["Mitarbeitende"],
                "Umsatz": company["Umsatz"],
                "Logo": company.get("Logo", "default.png"),
                "Beschreibung": company.get("Beschreibung")
            })

    print("No matching company found.")
    return jsonify({"error": "Company not found."}), 404

@app.route("/export", methods=["GET"])
def export_pdf():
    # Parameter abrufen
    export_type = request.args.get("type") #location oder company
    what = request.args.get("what") # None oder CityName oder CompanyName
    format = request.args.get("format") # pdf oder json

    if export_type == "location":
        print(f"Beginne Export für Location {what}")
        ndvi_changes = []
        ndwi_changes = []
        ndbi_changes = []
        green_changes = []
        sealed_changes = []
        water_changes = []
        unknown_changes = []
        ndvi_cache = load_cache(NDVI_CACHE)
        ndwi_cache = load_cache(NDWI_CACHE)
        ndbi_cache = load_cache(NDBI_CACHE)
        green_cache = load_cache(GREEN_CACHE)
        water_cache = load_cache(WATER_CACHE)
        sealed_cache = load_cache(SEALED_CACHE)
        unknown_cache = load_cache(UNKNOWN_CACHE)

        for year in range(int(2017), int(2025)):
            ndvi_value = get_cached_value(ndvi_cache, year, what)
            ndwi_value = get_cached_value(ndwi_cache, year, what)
            ndbi_value = get_cached_value(ndbi_cache, year, what)
            green_value = get_cached_value(green_cache, year, what)
            sealed_value = get_cached_value(sealed_cache, year, what)
            water_value = get_cached_value(water_cache, year, what)
            unknown_value = get_cached_value(unknown_cache, year, what)

            ndvi_changes.append(ndvi_value)
            ndwi_changes.append(ndwi_value)
            ndbi_changes.append(ndbi_value)
            green_changes.append(green_value)
            sealed_changes.append(sealed_value)
            water_changes.append(water_value)
            unknown_changes.append(unknown_value)
        if not ndvi_changes:
            return jsonify({"error": "Location not found."}), 404
        
        if format == "pdf":
            result = generate_location_pdf(what, ndvi_changes, ndwi_changes, ndbi_changes, green_changes, sealed_changes, water_changes, unknown_changes)
            # PDF nach der Erstellung zurückgeben
            file_path = os.path.join('data', 'exports', 'location', f"{what}_report.pdf")
            if os.path.exists(file_path):
                return send_from_directory(
                    directory=os.path.dirname(file_path),
                    path=os.path.basename(file_path),
                    as_attachment=True
                )
            else:
                return jsonify({"error": "PDF nicht gefunden"}), 404
        elif format == "json":
            file_path = generate_location_json(what, ndvi_changes, ndwi_changes, ndbi_changes, green_changes, sealed_changes, water_changes, unknown_changes)
            if os.path.exists(file_path):
                return send_from_directory(
                    directory=os.path.dirname(file_path),
                    path=os.path.basename(file_path),
                    as_attachment=True
                )
            else:
                 abort(400, description="Invalid export type.")
        else:
            # Falls der Formatparameter ungültig ist
            return jsonify({"Fehler": "Invalid format. Supported formats: PDF, JSON."}), 400
    elif export_type == "company":
         abort(400, description="Invalid export type.")
    
    else:
        abort(400, description="Invalid export type.")
    


    

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Standardmäßig Port 5000, falls kein PORT gesetzt ist
    app.run(host='0.0.0.0', port=port)
    #app.run(debug=True)
