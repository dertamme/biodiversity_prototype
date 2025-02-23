#Skript wurde gentuzt, um Doubletten innerhalb der Standorte (z.b. Frankfurt und Frankfurt am Main) zu joinen.
#Kann gelöscht werden.
import json

# Skript entfernt alle doppelten Städte 
def process_standorte_json():
    with open('data/standorte.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    coordinates_dict = {}
    cities_removed = []

    for entry in data[:]:
        coords_tuple = tuple(entry["Koordinaten"])

        if coords_tuple in coordinates_dict:
            first_city = coordinates_dict[coords_tuple]
            first_city["Firmen"].extend(entry["Firmen"])
            cities_removed.append(entry["Stadt"])
            data.remove(entry)
        else:
            coordinates_dict[coords_tuple] = entry

    with open('data/standorte.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    if cities_removed:
        print("Folgende Städte wurden entfernt, da sie doppelte Koordinaten hatten:")
        for city in cities_removed:
            print(city)
    else:
        print("Es wurden keine doppelten Städte gefunden.")

process_standorte_json()
