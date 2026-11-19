import os
import requests
import csv
from datetime import datetime, timedelta

# Chargement de la clé API depuis variable d'environnement
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise Exception("Erreur : variable d'environnement API_KEY non définie")

# Coordonnées du lieu (ici Castelnaudary 43.10713483230613, 0.7244646904930029)
LAT = 43.10713483230613
LON = 0.7244646904930029

def get_forecast():
    url = f"https://api.meteofrance.com/forecast/hourly?lat={LAT}&lon={LON}&model=arome"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erreur API {response.status_code}: {response.text}")
    return response.json()

def extract_irradiance_24h(data):
    now = datetime.utcnow()
    target_time = now + timedelta(hours=24)

    forecast_hours = data.get("forecast", [])
    irradiance_value = None

    # Parcourir les heures pour trouver celle proche de +24h
    for hour in forecast_hours:
        time_str = hour.get("time")
        # Exemple format: "2024-06-04T12:00:00Z"
        time_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
        delta = abs((time_obj - target_time).total_seconds())
        # On accepte une plage +/- 3600s (= 1h) autour de +24h
        if delta <= 3600:
            irradiance_value = hour.get("global_radiation")  # clé pour irradiance solaire (W/m2)
            return time_str, irradiance_value

    return None, None

def save_to_csv(timestamp, irradiance, filename="irradiance_24h.csv"):
    # On écrit en mode ajout pour conserver l’historique
    header = ["timestamp", "irradiance_w_m2"]

    # Vérifier si le fichier existe déjà
    try:
        with open(filename, "r", newline="") as csvfile:
            pass
        file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(header)
        writer.writerow([timestamp, irradiance])

def main():
    data = get_forecast()
    timestamp, irradiance = extract_irradiance_24h(data)

    if irradiance is None:
        print("Irradiance à 24h non trouvée dans la prévision.")
    else:
        print(f"Irradiance à {timestamp} : {irradiance} W/m²")
        save_to_csv(timestamp, irradiance)
        print("Donnée enregistrée dans le fichier CSV.")

if __name__ == "__main__":
    main()
