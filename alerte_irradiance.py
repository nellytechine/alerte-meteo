import requests
import csv
from datetime import datetime, timedelta
import os

# Lecture de la clé API dans le fichier API.KEY
def load_api_key(filename='API.KEY'):
    try:
        with open(filename, 'r') as f:
            key = f.read().strip()
            if not key:
                raise ValueError("Fichier API.KEY vide")
            return key
    except Exception as e:
        raise RuntimeError(f"Erreur lecture clé API: {e}")

# Récupération de la prévision d'irradiation Météo-France à +24h
def fetch_meteofrance_forecast(api_key, lat=43.109265, lon=0.724808):
    url = f"https://api.meteofrance.com/forecast/hourly?lat={lat}&lon={lon}&model=arome"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur API Météo-France: {resp.status_code} - {resp.text}")
    data = resp.json()
    
    # Trouver la donnée heure la plus proche de +24h UTC
    now = datetime.utcnow()
    target_time = now + timedelta(hours=24)

    forecast_hours = data.get("forecast", [])
    closest_forecast = None
    closest_delta = None
    for hour in forecast_hours:
        dt_str = hour.get("time")  # Ex: "2024-06-04T13:00:00Z"
        dt_obj = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
        delta = abs((dt_obj - target_time).total_seconds())
        if closest_delta is None or delta < closest_delta:
            closest_delta = delta
            closest_forecast = hour
    
    if closest_forecast is None:
        raise RuntimeError("Pas de prévision à +24h trouvée")
    
    irradiance = closest_forecast.get("global_radiation")
    if irradiance is None:
        raise RuntimeError("Clé 'global_radiation' introuvable dans la prévision")
    
    return dt_obj.strftime("%Y-%m-%d"), irradiance

# Récupération moyenne PVGIS pour un jour donné (le lendemain) sur les 20 dernières années
def fetch_pvgis_daily_irradiance(day, month, lat=43.109265, lon=0.724808):
    """
    Appel à PVGIS avec paramètres pour jour entier et base 20 ans.
    On récupère la valeur moyenne journalière du rayonnement global (kWh/m²)
    """
    url = ("https://re.jrc.ec.europa.eu/api/seriescalc?"
           f"lat={lat}&lon={lon}&startyear=2003&endyear=2022&outputformat=json&"
           "browser=1&pvcalculation=1&peakpower=1&loss=0&tracking=0&optimalinclination=0&"
           "usehorizon=1&startmonth={month}&endmonth={month}&startday={day}&endday={day}")

    url = url.format(month=month, day=day)
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur API PVGIS: {resp.status_code}")
    
    data = resp.json()
    
    # Exemple de structure dans 'outputs' -> 'daily_profile' ou 'totals' selon l’API
    # Pour l'API SeriesCalc, recherche la moyenne journalière 'fixed' ou globale

    try:
        # Par exemple, dans 'outputs' → 'totals' → 'fixed'
        daily_totals = data['outputs']['totals']
        avg_daily_irradiance = daily_totals['fixed']  # kWh/m²/jour
    except Exception as e:
        raise RuntimeError(f"Erreur lecture données PVGIS: {e}")

    # Convertir kWh/m² en Wh/m² (x1000) pour être cohérent avec Météo-France (W/m² instantané)
    # Attention: Météo-France => irradiation instantanée (W/m²), PVGIS => énergie journalière (Wh/m²)
    # On peut juste noter l’énergie journalière PVGIS telle quelle pour comparaison approximative.
    return avg_daily_irradiance

def save_to_csv(date_str, irradiance_forecast, irradiance_pvgis, filename='irradiation_compare.csv'):
    header = ["date", "irradiance_forecast_W_m2", "irradiance_pvgis_kWh_m2"]
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(header)
        writer.writerow([date_str, irradiance_forecast, irradiance_pvgis])

def main():
    api_key = load_api_key()
    # 1. Récupérer la prévision Météo-France à +24h
    date_str, irradiance_forecast = fetch_meteofrance_forecast(api_key)

    # Extraire jour et mois pour PVGIS
    dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day = dt_obj.day
    month = dt_obj.month

    # 2. Récupérer la moyenne PVGIS du jour +1
    irradiance_pvgis = fetch_pvgis_daily_irradiance(day, month)

    # 3. Enregistrer dans CSV
    save_to_csv(date_str, irradiance_forecast, irradiance_pvgis)

    print(f"Date = {date_str}")
    print(f"Irradiance Météo-France prévue à +24h : {irradiance_forecast} W/m²")
    print(f"Irradiance moyenne PVGIS sur 20 ans : {irradiance_pvgis:.2f} kWh/m² par jour")
    print("Données sauvegardées dans 'irradiation_compare.csv'")

if __name__=="__main__":
    main()
