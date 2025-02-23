import json
import os
import ee
import folium
import json
import ee
import os
import folium
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from flask import jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from functions.calculations import get_ndvi
from functions.etc import calculate_bounds
from functions.paths import EXPORT_MAPS_DIR


# Erstellt und speichert die FOlium-Map für eine Location
def generate_and_save_map(filename, result, start_year, end_year, region, get_ndvi, get_ndwi, get_ndbi):

    if os.path.exists(filename):
        print(f"Die Datei {filename} existiert bereits.")
        return

    print(f"Die Datei {filename} existiert nicht und wird erstellt.")
    print("Generiere Karte...")
 
    # Karte und Figure initialisieren
    bounds = calculate_bounds(result["geojson"])
    f = folium.Figure(width=500, height=1000)  
    folium_map = folium.Map(location=result["center"], zoom_start=11)
    folium_map.add_to(f)
    folium_map.fit_bounds(bounds)

    # GeoJSON-Region hinzufügen
    folium.GeoJson(result["geojson"], name="Region").add_to(folium_map)

    # NDVI/NDWI/NDBI-Daten für Startjahr und Endjahr berechnen
    ndwi_start = get_ndwi(start_year, region)
    ndwi_end = get_ndwi(end_year, region)
    ndvi_start = get_ndvi(start_year, region)
    ndvi_end = get_ndvi(end_year, region)
    ndbi_start = get_ndbi(start_year, region)
    ndbi_end = get_ndbi(end_year, region)
    if ndvi_start is None or ndvi_end is None or ndbi_end is None:
        print(f"Keine gültigen NDVI/NDWI/NDBI-Daten für {start_year} oder {end_year}. Karte wird übersprungen.")
        return
    ndvi_change = ndvi_end.subtract(ndvi_start)
    ndwi_change = ndwi_end.subtract(ndwi_start)
    ndbi_change = ndbi_end.subtract(ndbi_start)

    # NDVI/NDWI/NDBI-TileLayer für Startjahr und Endjahr erstellen
    ndvi_change_map = ndvi_change.getMapId({'min': -0.5, 'max': 0.5, 'palette': ['red', 'white', 'green']})
    ndwi_change_map = ndwi_change.getMapId({'min': -0.5, 'max': 0.5, 'palette': ['#8B4513', '#D2B48C', '#87CEFA', '#0000FF']})
    ndbi_change_map = ndbi_change.getMapId({'min': -0.5, 'max': 0.5, 'palette': ['#000000', '#808080', '#FFFFFF', '#0000FF']})


    # TileLayer für jedes Jahr zwischen Start- und Endjahr hinzufügen
    for year in range(start_year, end_year +1):
        print("---")
        ndvi_year = get_ndvi(year, region)
        ndwi_year = get_ndwi(year, region)
        ndbi_year = get_ndbi(year, region)
        if ndvi_year is None or ndwi_year is None or ndbi_year is None:
            print(f"    Keine gültigen NDVI/NDWI/NDBI-Werte im Jahr {year}. Überspringe...")
            continue
        ndvi_year_map = ndvi_year.getMapId({'min': 0, 'max': 1, 'palette': ['red', 'yellow', 'green']})
        ndwi_year_map = ndwi_year.getMapId({'min': 0, 'max': 1, 'palette': ['#8B4513', '#D2B48C', '#87CEFA', '#0000FF']})
        ndbi_year_map = ndbi_year.getMapId({'min': -1, 'max': 1, 'palette': ['#FFFFFF', '#FFFFFF', '#D3D3D3', '#808080', '#000000']})


        folium.TileLayer(
            tiles=ndvi_year_map['tile_fetcher'].url_format,
            attr=f"NDVI {year}",
            overlay=True,
            show=False,
            name=f"NDVI {year}"
        ).add_to(folium_map)

        folium.TileLayer(
            tiles=ndwi_year_map['tile_fetcher'].url_format,
            attr=f"NDWI {year}",
            overlay=True,
            show=False,
            name=f"NDWI {year}"
        ).add_to(folium_map)

        folium.TileLayer(
            tiles=ndbi_year_map['tile_fetcher'].url_format,
            attr=f"NDBI {year}",
            overlay=True,
            show=False,
            name=f"NDBI {year}"
        ).add_to(folium_map)


    folium.TileLayer(
        tiles=ndvi_change_map['tile_fetcher'].url_format,
        attr="NDVI Change",
        overlay=True,
        show=False,
        name="NDVI Change"
    ).add_to(folium_map)

    folium.TileLayer(
        tiles=ndwi_change_map['tile_fetcher'].url_format,
        attr="NDWI Change",
        overlay=True,
        show=False,
        name="NDWI Change"
    ).add_to(folium_map)

    folium.TileLayer(
        tiles=ndbi_change_map['tile_fetcher'].url_format,
        attr="NDBI Change",
        overlay=True,
        show=False,
        name="NDBI Change"
    ).add_to(folium_map)
    

    # Berechnung und Visualisierung der Landbedeckung für Endjahr
    green_map = ndvi_end.gte(0.3).selfMask()  # Grünflächen
    ndwi_map = ndwi_end.gt(0.0).selfMask()  # Wasserflächen
    ndbi_map = ndbi_end.gt(-0.05).selfMask()  # Bebaute Flächen
    unknown_map = ee.Image.constant(1).subtract(ndvi_end.gte(0.3)).subtract(ndwi_end.gt(0.0)).subtract(ndbi_end.gt(-0.05)).selfMask() # Versiegelung

    green_map_layer = green_map.getMapId({'palette': ['#32CD32']})
    ndwi_map_layer = ndwi_map.getMapId({'palette': ['#1E90FF']})
    ndbi_map_layer = ndbi_map.getMapId({'palette': ['#000000']})
    unknown_map_layer = unknown_map.getMapId({'palette': ['#ffc107']})

    folium.TileLayer(
        tiles=green_map_layer['tile_fetcher'].url_format,
        attr="Grünflächen",
        overlay=True,
        name="Grünflächen"
    ).add_to(folium_map)

    folium.TileLayer(
        tiles=ndwi_map_layer['tile_fetcher'].url_format,
        attr="Wasserflächen",
        overlay=True,
        name="Wasserflächen"
    ).add_to(folium_map)

    folium.TileLayer(
        tiles=ndbi_map_layer['tile_fetcher'].url_format,
        attr="Bebaute Flächen",
        overlay=True,
        name="Bebaute Flächen"
    ).add_to(folium_map)    

    folium.TileLayer(
        tiles=unknown_map_layer['tile_fetcher'].url_format,
        attr="Unbekannte Flächen",
        overlay=True,
        name="Unbekannte Flächen"
    ).add_to(folium_map)

    # Layer-Steuerung hinzufügen
    folium.LayerControl().add_to(folium_map)

    # Karte speichern
    f.save(filename)
    print(f"Karte wurde erfolgreich als {filename} gespeichert.")

    return f.render()

# Generiert eine vereinfachte Karte für den Location Export
def generate_export_location_map(name, result, region):
	
    filename = (f"{EXPORT_MAPS_DIR}/{name}.html")
    
    if os.path.exists(filename):
        print(f"Die Datei {filename} existiert bereits.")
        return

    print(f"Die Datei {filename} existiert nicht und wird erstellt.")
    print("Generiere Karte...")
    bounds = calculate_bounds(result["geojson"])
    year = 2024
 
    # Karte initialisieren
    f = folium.Figure(width=500, height=1000)  # 2:1 Seitenverhältnis
    folium_map = folium.Map(location=result["center"], zoom_start=11)
    folium_map.add_to(f)
    folium_map.fit_bounds(bounds)

    # GeoJSON-Region hinzufügen
    folium.GeoJson(result["geojson"], name="Region").add_to(folium_map)

    ndvi_start = get_ndvi(2024, region)
    if ndvi_start is None:
        ndvi_start = get_ndvi(2023, region)
        year = year-1
        
    # NDVI-TileLayer für jedes Jahr zwischen Start- und Endjahr hinzufügen
    ndvi_year_map = ndvi_start.getMapId({'min': 0, 'max': 1, 'palette': ['red', 'yellow', 'green']})
    folium.TileLayer(tiles=ndvi_year_map['tile_fetcher'].url_format,attr=f"NDVI {year}",overlay=True,ame=f"NDVI {year}").add_to(folium_map)

    # Karte speichern
    f.save(filename)
    print(f"Karte wurde erfolgreich als {filename} gespeichert.")

# Speichert eine Map als PNG
def save_map_as_image(map_html_path, output_image_path):

    absolute_map_path = os.path.abspath(map_html_path)

    # Set up Chrome options for headless mode (no GUI)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--disable-gpu")  
    chrome_options.add_argument("--window-size=600x300")  

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1400,1000)


    try:
        driver.get(f"file:///{absolute_map_path}")

        # Warten, bis alle Teile der Folium-Map sichtbar sind
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "folium-map"))
        )

        map_element = driver.find_element(By.CLASS_NAME, "folium-map")

        map_width = map_element.size['width']
        map_height = map_element.size['height']

        driver.set_window_size(map_width, map_height)

        driver.save_screenshot(output_image_path)
        print(f"Screenshot saved as {output_image_path}")
    finally:
        driver.quit()
  
# Erstellt die Übersichtskarte mit allen Locations
def create_big_map():
    # JSON-Dateien
    input_file = "data/standorte.json"
    ndvi_file = "data/ndvi_cache.json"
    output_map = "templates/map_big.html"

    # JSON-Daten laden
    with open(input_file, "r", encoding="utf-8") as f:
        standorte = json.load(f)

    with open(ndvi_file, "r", encoding="utf-8") as f:
        ndvi_data = json.load(f)

    # NDVI-Werte für 2024 in ein Wörterbuch laden
    ndvi_2024 = {}
    for item in ndvi_data:
        if item["Jahr"] == "2024":
            key = (item["Stadt"], item["Land"])
            ndvi_2024[key] = float(item["value"])

    # Erstelle eine Folium-Karte mit einem initialen Mittelpunkt (Deutschland)
    m = folium.Map(location=[51.1657, 10.4515], zoom_start=2)
    folium.TileLayer('cartodbpositron').add_to(m)

    # Füge für jeden Standort einen Marker hinzu
    for standort in standorte:
        stadt = standort["Stadt"]
        land = standort["Land"]
        koordinaten = standort.get("Koordinaten")
        firmenanzahl = len(standort["Firmen"])

        # Farbe des Punktes
        if koordinaten != "Nicht gefunden" and koordinaten is not None:
            ndvi_value = ndvi_2024.get((stadt, land))

            if ndvi_value is not None:
                ndvi_value = round(ndvi_value, 4)

                if ndvi_value > 0.8:
                    color = "green"  
                elif 0.6 < ndvi_value <= 0.8:
                    color = "#9ACD32"  
                elif 0.4 < ndvi_value <= 0.6:
                    color = "gold"  
                elif 0.2 < ndvi_value <= 0.4:
                    color = "orange"  
                else:
                    color = "red"  
            else:
                color = "gray"  # Grau, falls kein NDVI-Wert vorhanden ist

            # Größe des Punktes
            if firmenanzahl >= 10:
                radius = 5
            elif 9 >= firmenanzahl > 7:
                radius = 4    
            elif 7 >= firmenanzahl > 5:
                radius = 3
            elif 5 >= firmenanzahl > 3:
                radius = 2
            else: 
                radius = 1      

            # Firmenliste im Popup
            firmen_html = "<div style='max-height: 100px; overflow-y: auto;'>" + "".join(f"<div>{firma}</div>" for firma in standort["Firmen"]) + "</div>"

            # Button für Standortanalyse
            button_html = f"""
                <div style='margin-top: 10px; text-align: center;'>
                    <a href="/standortanalyse/{stadt}" target="_blank" style="text-decoration: none;">
                        <button style="background-color: #155c98; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">
                            Zur Standortanalyse
                        </button>
                    </a>
                </div>
            """

            # Popup-Inhalt
            popup_html = (
                f"<b>{stadt}, {land}</b><br>"
                f"<b>NDVI 2024: {ndvi_value}</b><br>"
                f"{firmen_html}"
                f"{button_html}"
            )

            # Marker zur Karte hinzufügen
            folium.CircleMarker(
                location=koordinaten,
                radius=radius,  # Radius des Kreises in Pixeln
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

    # Karte speichern
    print("big_map erfolgreich erstellt!")
    m.save(output_map)

#Export PDF für Locations
def generate_location_pdf(location, ndvi_changes, ndwi_changes, ndbi_changes, green_changes, sealed_changes, water_changes, unknown_changes,):
    ##############
    def calculate_percentage_change(value_2018, value_2024):
        if value_2018 is None or value_2024 is None:
            return 0 
        if value_2018 == 0:
            return 0  # Vermeidet Division durch Null
        return ((value_2024 - value_2018) / abs(value_2018)) * 100
    
    def format_percentage(value):
        if value > 0:
            return f"+{value:.2f}%"
        else:
            return f"{value:.2f}%"
    
    def get_companies_for_location(city):
        with open('data/standorte.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        for entry in data:
            if entry["Stadt"].lower() == city.lower():
                return sorted(entry["Firmen"])  
        
        return None  
    
    def safe_format(value, is_percentage=False):
        if value is None:
            return "0.00 %" if is_percentage else "0.00"  
        if is_percentage:
            return f"{value:.2f} %"  
        return f"{value:.5f}"  

    ##############

    export_dir = os.path.join('data', 'exports', 'location')
    os.makedirs(export_dir, exist_ok=True)  
    
    filename = f"{location}_report.pdf"
    file_path = os.path.join(export_dir, filename)

    if os.path.exists(file_path):
        return
    
    # PDF erstellen, wenn noch kein Export für die Location vorliegen sollte
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    margin = 28.35  # 1cm 

    # Header 
    header_height = 50  
    c.setFillColor(HexColor('#155c98'))  
    c.rect(0, height - header_height, width, header_height, fill=True)  

    logo_path = "static/img/bb_logo.png"
    logo_right_margin = 20
    logo_width = 85  
    logo_height = 33  
    logo_x_position = width - logo_width - logo_right_margin
    c.drawImage(logo_path, logo_x_position, height - header_height + 8, width=logo_width, height=logo_height, mask='auto')  

    c.setFont("Helvetica", 20)
    c.setFillColor(colors.white)  
    c.drawString(margin , height - header_height + 15, "Biodiversitätsveränderungen")  
   
    c.setFillColor(colors.black)  
    c.setFont("Helvetica-Bold", 16)  
    c.drawString(margin, height - header_height - 30, f"Informationen zu {location}")

    # Titel "Informationen zu <Standort>" unter dem Header
    c.setFont("Helvetica-Bold", 16)  
    c.drawString(margin, height - header_height - 30, f"Informationen zu {location}")

    # Daten für die Tabelle vorbereiten
    data = [['Jahr', 'NDVI', 'NDWI', 'NDBI', 'Begrünung', 'Versiegelung', 'Wasser', 'Unklar']]  # Kopfzeile
    for i, year in enumerate(range(2017, 2025)):
        data.append([
            str(year),
            safe_format(ndvi_changes[i]),  # Normale Zahl
            safe_format(ndwi_changes[i]),  # Normale Zahl
            safe_format(ndbi_changes[i]),  # Normale Zahl
            safe_format(green_changes[i], is_percentage=True),  # Prozent
            safe_format(sealed_changes[i], is_percentage=True),  # Prozent
            safe_format(water_changes[i], is_percentage=True),  # Prozent
            safe_format(unknown_changes[i], is_percentage=True)  # Prozent
        ])

    # Berechne die Veränderung von 2018 bis 2024 in %
    ndvi_change_percentage = calculate_percentage_change(ndvi_changes[1], ndvi_changes[7])  
    ndwi_change_percentage = calculate_percentage_change(ndwi_changes[1], ndwi_changes[7])  
    ndbi_change_percentage = calculate_percentage_change(ndbi_changes[1], ndbi_changes[7])  
    green_change_percentage = calculate_percentage_change(green_changes[1], green_changes[7])  
    sealed_change_percentage = calculate_percentage_change(sealed_changes[1], sealed_changes[7])
    water_change_percentage = calculate_percentage_change(water_changes[1], water_changes[7])
    unknown_change_percentage = calculate_percentage_change(unknown_changes[1], unknown_changes[7])   

    data.append(['Seit 2018', 
                format_percentage(ndvi_change_percentage), 
                format_percentage(ndwi_change_percentage),
                format_percentage(ndbi_change_percentage),  
                format_percentage(green_change_percentage), 
                format_percentage(sealed_change_percentage),
                format_percentage(water_change_percentage),
                format_percentage(unknown_change_percentage),])

    # Tabelle erstellen
    table = Table(data, colWidths=[63, 63, 63, 63, 63, 63, 63, 63], rowHeights=20)
    table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#155c98')),  
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10)
    ]))

    table_y_position = height - header_height - 60 - len(data) * 20

    # Suche nach der HTML-Karte
    map_html_path = None
    
    for filename in os.listdir(EXPORT_MAPS_DIR):
        if filename.startswith(location.split(",")[0].strip()) and filename.endswith(".html"):
            map_html_path = os.path.join(EXPORT_MAPS_DIR, filename)
            break

    # Speichern der HTML-Karte als Bild
    if map_html_path:
        image_filename = f"{location}_map.png"
        save_map_as_image(map_html_path, image_filename)
        image_width = 500  
        image_height = 250

        # Füge die Karte in das PDF 
        c.drawImage(image_filename, margin, height - header_height - 100 - len(data) * 20, image_width, image_height)
        os.remove(image_filename)  

        table_y_position = height - header_height - 250 - image_height - 20 
    
    # Tabelle linksbündig unter dem Bild
    table.wrapOn(c, width, height)
    table.drawOn(c, margin, table_y_position)  

    # Firmen aus der JSON-Daten abrufen
    companies = get_companies_for_location(location)
    if companies:
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.black)
        c.drawString(margin, table_y_position - 40, "Unternehmen am Standort:")
        c.setFont("Helvetica", 12)

        num_companies = len(companies)
        first_column_companies = companies[:10]  
        second_column_companies = companies[10:]  

        for idx, company in enumerate(first_column_companies, start=1):
            c.drawString(margin, table_y_position - 40 - (idx * 15), f"{idx}. {company}")
        
        if second_column_companies:
            second_column_x_position = margin + 220  
            for idx, company in enumerate(second_column_companies, start=1):
                c.drawString(second_column_x_position, table_y_position - 40 - (idx * 15), f"{idx+10}. {company}")

    c.save()
    return

#Export JSON für Locations
def generate_location_json(location, ndvi_changes, ndwi_changes, ndbi_changes, green_changes, sealed_changes, water_changes, unknown_changes):
    # JSON-Daten erstellen
    years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    
    # Neue Datenstruktur erstellen, bei der jedes Jahr als Schlüssel verwendet wird
    data = {
        "ndvi": {year: ndvi_changes[i] for i, year in enumerate(years)},
        "ndwi": {year: ndwi_changes[i] for i, year in enumerate(years)},
        "ndbi": {year: ndbi_changes[i] for i, year in enumerate(years)},
        "green": {year: green_changes[i] for i, year in enumerate(years)},
        "sealed": {year: sealed_changes[i] for i, year in enumerate(years)},
        "water": {year: water_changes[i] for i, year in enumerate(years)},
        "unknown": {year: unknown_changes[i] for i, year in enumerate(years)},
    }

    json_data = {
        "location": location,
        "data": data
    }
    
    # Datei speichern
    export_dir = os.path.join('data', 'exports', 'location')
    os.makedirs(export_dir, exist_ok=True)  # Verzeichnis erstellen, falls nicht vorhanden
    filename = f"{location}_report.json"
    file_path = os.path.join(export_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)
    
    return file_path

# Company-Export erstellen
def generate_company_pdf(company, data):
    filename = f"{company}_locations_report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Titel
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, height - 50, f"Locations Report for {company}")

    # Locations and NDVI Average for each
    c.setFont("Helvetica", 12)
    y_position = height - 100

    c.drawString(100, y_position, "Location | Average NDVI (2024)")
    y_position -= 20

    for loc in data["locations"]:
        c.drawString(100, y_position, f"{loc['city']} | {loc['ndvi_avg']:.2f}")
        y_position -= 20

    # PDF speichern
    c.save()

    return jsonify({"message": f"PDF for {company} generated successfully!", "file": filename})