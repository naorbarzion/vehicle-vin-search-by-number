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
        # קריאת הנתונים מה-CSV והסרת רווחים לפני ואחרי המודל
        data = pd.read_csv(csv_file_path)
        data['Model'] = data['Model'].str.strip()
        
        # תיקון שמות עמודות אם יש בעיה עם תווים כמו \r\n
        data.columns = [col.replace('\r\n', ' ') for col in data.columns]

        logging.info(f"Successfully read data from {csv_file_path}")
        logging.info(f"First 5 rows from {csv_file_path}:\n{data.head()}")
        
        return data
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file_path}: {e}")
        return None

# פונקציה לחיפוש המודל ב-CSV לפי סוג דלק
def search_vehicle_in_csv(model, fuel_type):
    csv_file_path = ''
    if fuel_type == 'חשמל':
        csv_file_path = 'database/fmc_vehicles_list_electric.csv'
    else:
        csv_file_path = 'database/fmc_vehicles_list.csv'
    
    vehicle_data = read_vehicle_data_from_csv(csv_file_path)
    
    if vehicle_data is not None:
        clean_model = model.strip()  # ניקוי רווחים מיותרים לפני ואחרי המודל
        result = vehicle_data[vehicle_data['Model'].str.contains(clean_model, case=False, na=False)]
        
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

@app.route('/', methods=['GET', 'POST'])
def index():
    records = None
    db_record = None
    error_message = None
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        logging.debug(f"Vehicle number entered: {vehicle_number}")
        
        # קריאה ל-API
        records = fetch_vehicle_data(vehicle_number)
        
        if records:
            model = records[0].get('kinuy_mishari', '').strip()
            fuel_type = records[0].get('sug_delek_nm', '').strip()
            
            # חיפוש המודל ב-CSV לפי סוג דלק
            db_record = search_vehicle_in_csv(model, fuel_type)
    
    return render_template('index.html', records=records, db_record=db_record, error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)
