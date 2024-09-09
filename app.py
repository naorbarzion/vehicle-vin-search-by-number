import os
from flask import Flask, request, render_template
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# הגדרת החיבור למסד הנתונים (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://test:FPHmlbj1PYymNlQIHUgiBUPJuEc3L26z@dpg-crf1n63v2p9s73d3pmo0-a.frankfurt-postgres.render.com/fmcvehicleslist?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# מודל למסד הנתונים
class Vehicle(db.Model):
    __tablename__ = 'fmc_vehicles_list'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    fuel_level = db.Column(db.Float, nullable=True)
    battery_level = db.Column(db.Float, nullable=True)

# פונקציה שמבצעת חיפוש ברשומות ה-API של CKAN
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
        print(f"Failed to retrieve data from CKAN API: {e}")
        return []

# פונקציה לחיפוש רכב בדאטהבייס לפי מודל בלבד
def search_vehicle_in_db(model):
    try:
        result = Vehicle.query.filter_by(model=model).first()
        return result
    except Exception as e:
        print(f"Database search error: {e}")
        return None

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
                model = records[0]['kinuy_mishari']

                # חיפוש בדאטהבייס
                db_record = search_vehicle_in_db(model)
                
                # בדיקה אם יש קריאת קילומטראז' או סוללה
                if db_record:
                    if db_record.battery_level is not None:
                        print(f"Battery level: {db_record.battery_level}")
                    elif db_record.fuel_level is not None:
                        print(f"Fuel level: {db_record.fuel_level}")
                else:
                    print("No matching vehicle found in the database.")
            else:
                error_message = "No records found in the CKAN API for the given vehicle number."
        except Exception as e:
            error_message = f"An error occurred: {e}"
            print(f"An error occurred in the index function: {e}")

    return render_template('index.html', records=records, db_record=db_record, error_message=error_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
