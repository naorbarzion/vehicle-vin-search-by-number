import os
import pandas as pd
from flask import Flask, request, render_template
import requests
import logging

app = Flask(__name__)

# הגדרת נתיבי קבצי ה-CSV
ELECTRIC_CSV = "database/fmc_vehicles_list_electric.csv"
REGULAR_CSV = "database/fmc_vehicles_list.csv"

# הגדרת לוגים
logging.basicConfig(level=logging.INFO)

# פונקציה שמבצעת חיפוש ברשומות ה-API של CKAN
def fetch_vehicle_data(vehicle_number):
    url = "https://data.gov.il/api/3/action/datastore_search"
    resource_id = "053cea08-09bc-40ec-8f7a-156f0677aff3"
    params = {"resource_id": resource_id, "q": vehicle_number}

    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("success"):
            return data["result"]["records"]
        else:
            return []
    except Exception as e:
        logging.error(f"Failed to retrieve data from CKAN API: {e}")
        return []

# פונקציה לקריאת נתונים ממסד הנתונים (CSV) לפי סוג הדלק והמודל
def search_vehicle_in_csv(model, fuel_type):
    csv_file = REGULAR_CSV if fuel_type == "בנזין" else ELECTRIC_CSV

    try:
        df = pd.read_csv(csv_file)
        logging.info(f"Successfully read data from {csv_file}")
        logging.info(f"First 5 rows from {csv_file}:\n{df.head()}")
        result = df[df["model"] == model]
        return result if not result.empty else None
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file}: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    records = None
    db_record = None
    error_message = None

    if request.method == "POST":
        try:
            vehicle_number = request.form.get("vehicle_number")
            records = fetch_vehicle_data(vehicle_number)

            if records:
                vehicle_model = records[0]["kinuy_mishari"]
                fuel_type = records[0]["sug_delek_nm"]

                # חיפוש בדאטהבייס לפי סוג הדלק והמודל
                db_record = search_vehicle_in_csv(vehicle_model, fuel_type)

                if db_record is not None:
                    logging.info(f"Found vehicle data for model {vehicle_model} with fuel type {fuel_type}")
                else:
                    logging.info(f"No matching vehicle found for model {vehicle_model} in the {fuel_type} database.")
            else:
                error_message = "לא נמצאו תוצאות ב-API לפי מספר הרכב שניתן."
        except Exception as e:
            error_message = f"תקלה התרחשה: {e}"
            logging.error(f"An error occurred: {e}")

    return render_template("index.html", records=records, db_record=db_record, error_message=error_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
