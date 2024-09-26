import os
import pandas as pd
from flask import Flask, request, render_template
import requests
import logging
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

app = Flask(__name__)

# הגדרת הלוגים
logging.basicConfig(level=logging.INFO)

# פונקציה לניקוי רווחים וסימנים מיוחדים ולנרמול המחרוזת
def normalize_model_name(name):
    if isinstance(name, str):
        name = name.replace("-", " ").replace("HYBRID", "").replace("  ", " ")  # הסרת מקפים ו-HYBRID
        return "".join(name.split()).lower()  # הסרת כל הרווחים וקטנים את הכל
    return ""

# פונקציה לקריאת הנתונים מה-CSV ולניקוי הרווחים
def read_vehicle_data_from_csv(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data['Model'] = data['Model'].str.strip()
        data.columns = [col.replace('\r\n', ' ') for col in data.columns]
        logging.info(f"Successfully read data from {csv_file_path}")
        return data
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file_path}: {e}")
        return None

# פונקציה לחיפוש המודל ב-CSV לפי סוג דלק עם Fuzzy Matching חכם
def search_vehicle_in_csv(model, fuel_type):
    if fuel_type == 'חשמל':
        csv_file_path = 'database/fmc_vehicles_list_electric.csv'
    else:
        csv_file_path = 'database/fmc_vehicles_list.csv'
    
    vehicle_data = read_vehicle_data_from_csv(csv_file_path)
    if vehicle_data is not None:
        clean_model = normalize_model_name(model.strip())  # ניקוי המודל
        
        # שימוש ב-Fuzzy Matching כדי למצוא את המודל הקרוב ביותר
        vehicle_models = vehicle_data['Model'].apply(normalize_model_name).tolist()
        closest_match, score = process.extractOne(clean_model, vehicle_models, scorer=fuzz.token_sort_ratio)
        
        # נבדוק אם הציון של ההתאמה מספיק גבוה כדי להיחשב כהתאמה
        if score > 65:  # הורדת הסף מעט כדי לאפשר גמישות
            result = vehicle_data[vehicle_data['Model'].apply(normalize_model_name) == closest_match]
            return result if not result.empty else None
        else:
            logging.info(f"No close match found for {model} in the database.")
            return None
    else:
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
        return data['result']['records'] if data.get('success') else []
    except Exception as e:
        logging.error(f"Failed to retrieve data from CKAN API: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    all_records = []
    all_db_records = []
    unsupported_records = []  # נשמור כאן את הרכבים שלא נתמכים
    supported_count = 0
    unsupported_count = 0
    
    if request.method == 'POST':
        vehicle_numbers = request.form.get('vehicle_number')
        vehicle_numbers_list = [num.strip() for num in vehicle_numbers.split(',') if num.strip()]
        
        for vehicle_number in vehicle_numbers_list:
            records = fetch_vehicle_data(vehicle_number)
            if records:
                model = records[0].get('kinuy_mishari', '').strip()
                fuel_type = records[0].get('sug_delek_nm', '').strip()
                db_record = search_vehicle_in_csv(model, fuel_type)
                all_records.append(records[0])
                if db_record is not None:
                    all_db_records.append(db_record)
                    supported_count += 1
                else:
                    unsupported_records.append(records[0])  # הוספת הרכב לרשימה של הלא נתמכים
                    unsupported_count += 1

    return render_template(
        'index.html', 
        records=all_records, 
        db_records=all_db_records, 
        unsupported_records=unsupported_records,  # טבלה של הרכבים הלא נתמכים
        supported_count=supported_count, 
        unsupported_count=unsupported_count
    )

if __name__ == '__main__':
    app.run(debug=True)
