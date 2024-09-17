import os
import pandas as pd
from flask import Flask, request, render_template
import requests
import logging

app = Flask(__name__)

# הגדרת הלוגים
logging.basicConfig(level=logging.INFO)

# פונקציה לקריאת הנתונים מה-CSV ולניקוי הרווחים
def read_vehicle_data_from_csv(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data['Model'] = data['Model'].str.strip()
        data.columns = [col.replace('\r\n', ' ') for col in data.columns]
        logging.info(f"Successfully read data from {csv_file_path}")
        logging.info(f"First 5 rows from {csv_file_path}:\n{data.head()}")
        return data
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file_path}: {e}")
        return None

# פונקציה לחיפוש חכם במודל ב-CSV לפי סוג דלק
def smart_search_vehicle_in_csv(model, fuel_type):
    csv_file_path = ''
    if fuel_type == 'חשמל':
        csv_file_path = 'database/fmc_vehicles_list_electric.csv'
    else:
        csv_file_path = 'database/fmc_vehicles_list.csv'
    
    vehicle_data = read_vehicle_data_from_csv(csv_file_path)
    
    if vehicle_data is not None:
        clean_model = model.strip()
        result = vehicle_data[vehicle_data['Model'].str.contains(clean_model, case=False, na=False)]
        
        # אם לא נמצאה תוצאה מלאה, נתחיל לחפש התאמות חלקיות
        if result.empty:
            for i in range(len(clean_model), 0, -1):
                partial_model = clean_model[:i]
                result = vehicle_data[vehicle_data['Model'].str.contains(partial_model, case=False, na=False)]
                if not result.empty:
                    logging.info(f"Found partial match for model {clean_model} as {partial_model} in the {fuel_type} database.")
                    return result
        
        if not result.empty:
            logging.info(f"Found matching vehicle for model {clean_model} in the {fuel_type} database.")
            return result
        else:
            logging.info(f"No matching vehicle found for model {clean_model} in the {fuel_type} database.")
            return None
    else:
        logging.error(f"Could not read data from {csv_file_path}")
        return None

# פונקציה לחיפוש ב-API של CKAN
def fetch_vehicle_data(vehicle_number):
    url = "https://data.gov.il/api/3/action/datastore_search"
    resource_id = "053cea08-09bc-40ec-8f7a-156f0677aff3"

    params = {
        "resource_id": resource_id,
        "q": vehicle_number
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get('success'):
            logging.info(f"Fetched data from CKAN API for vehicle number {vehicle_number}")
            return data['result']['records']
        else:
            logging.warning(f"No data found in CKAN API for vehicle number {vehicle_number}")
            return []
    except Exception as e:
        logging.error(f"Failed to retrieve data from CKAN API: {e}")
        return []

# פונקציה שמקבלת רשימת מספרי רכבים ומבצעת חיפוש לכל אחד
def process_vehicle_numbers(vehicle_numbers):
    results = []
    for vehicle_number in vehicle_numbers:
        records = fetch_vehicle_data(vehicle_number)
        if records:
            model = records[0].get('kinuy_mishari', '').strip()
            fuel_type = records[0].get('sug_delek_nm', '').strip()
            db_record = smart_search_vehicle_in_csv(model, fuel_type)
            results.append({'vehicle_number': vehicle_number, 'records': records, 'db_record': db_record})
        else:
            results.append({'vehicle_number': vehicle_number, 'records': None, 'db_record': None})
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    all_results = None
    error_message = None
    
    if request.method == 'POST':
        vehicle_numbers_raw = request.form.get('vehicle_numbers')
        logging.debug(f"Vehicle numbers entered: {vehicle_numbers_raw}")
        
        # פירוק הקלט למספרי רכבים בודדים על בסיס שורות ורווחים
        vehicle_numbers = [num.strip() for num in vehicle_numbers_raw.splitlines() if num.strip()]
        
        if vehicle_numbers:
            all_results = process_vehicle_numbers(vehicle_numbers)
        else:
            error_message = "לא הוזנו מספרי רכבים תקינים."

    return render_template('index.html', all_results=all_results, error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)
