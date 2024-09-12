import os
import pandas as pd
from flask import Flask, request, render_template
import requests
import logging

app = Flask(__name__)

# הגדרת הלוגים
logging.basicConfig(level=logging.INFO)

# פונקציה לקריאת נתונים מה-CSV ולניקוי רווחים מיותרים
def read_vehicle_data_from_csv(csv_file_path):
    try:
        # קריאת הנתונים מה-CSV
        data = pd.read_csv(csv_file_path)
        logging.info(f"Successfully read data from {csv_file_path}")
        
        # הצגת 5 השורות הראשונות בלוג כדי לוודא שהכל תקין
        logging.info(f"First 5 rows from {csv_file_path}:\n{data.head()}")
        
        # ניקוי רווחים מיותרים מכל עמודת המודל
        data['Model'] = data['Model'].str.strip()  # הסרת רווחים לפני ואחרי השם
        return data
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file_path}: {e}")
        return None

# פונקציה לחיפוש המודל ב-CSV המתאים
def search_vehicle_in_csv(model, fuel_type):
    csv_file_path = ''
    if fuel_type == 'חשמל':
        csv_file_path = 'database/fmc_vehicles_list_electric.csv'
    else:
        csv_file_path = 'database/fmc_vehicles_list.csv'
    
    # קריאה לנתוני ה-CSV
    vehicle_data = read_vehicle_data_from_csv(csv_file_path)
    
    if vehicle_data is not None:
        # ניקוי רווחים מהמודל שהתקבל מהמשתמש
        clean_model = model.strip()  # הסרת רווחים מיותרים לפני ואחרי המודל
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
            return data['result']['records']
        else:
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
        try:
            vehicle_number = request.form.get('vehicle_number')
            records = fetch_vehicle_data(vehicle_number)
            
            if records:
                model = records[0]['kinuy_mishari'].strip()  # ניקוי רווחים מהמחרוזת שמגיעה מה-API
                fuel_type = records[0]['sug_delek_nm'].strip()  # סוג דלק - משמש לבחירת ה-CSV המתאים

                # חיפוש ב-CSV לפי המודל וסוג הדלק
                db_record = search_vehicle_in_csv(model, fuel_type)
                
                if db_record is None:
                    error_message = "No matching vehicle found in the database."
            else:
                error_message = "No records found in the CKAN API for the given vehicle number."
        except Exception as e:
            error_message = f"An error occurred: {e}"
            logging.error(f"An error occurred in the index function: {e}")

    return render_template('index.html', records=records, db_record=db_record, error_message=error_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
