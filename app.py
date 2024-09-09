import os
from flask import Flask, request, render_template
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# הגדרת החיבור ל-PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://test:FPHmlbjPfYymNlQIHUgiBUPJuEc3L26z@dpg-crfln63v2p9s73d3pmo0-a.frankfurt-postgres.render.com/fmcvehicleslist')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# מודל לטבלת רכבים רגילים
class Vehicle(db.Model):
    __tablename__ = 'fmc_vehicles_list'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    date_start = db.Column(db.String(10))
    date_end = db.Column(db.String(10))
    kilometer = db.Column(db.Boolean)
    fuel_level = db.Column(db.Boolean)

# מודל לטבלת רכבים חשמליים
class ElectricVehicle(db.Model):
    __tablename__ = 'fmc_vehicles_list_electric'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    date_start = db.Column(db.String(10))
    date_end = db.Column(db.String(10))
    kilometer = db.Column(db.Boolean)
    battery_level = db.Column(db.Boolean)

# CKAN API call function
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
            return data['result']['records']  # החזרת הרשומות מהתוצאה
        else:
            return []
    except Exception as e:
        print(f"Failed to retrieve data: {e}")
        return []

# פונקציה לחיפוש הרכב בדאטהבייס
def search_vehicle_in_db(make, model, is_electric):
    if is_electric:
        result = ElectricVehicle.query.filter_by(make=make, model=model).first()
    else:
        result = Vehicle.query.filter_by(make=make, model=model).first()
    return result

@app.route('/', methods=['GET', 'POST'])
def index():
    records = None
    db_record = None
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        records = fetch_vehicle_data(vehicle_number)  # קבלת נתונים מה-API
        
        if records:
            # נבדוק את סוג הדלק של הרכב הראשון שמצאנו
            model = records[0]['kinuy_mishari']
            make = records[0]['tozeret_nm']
            fuel_type = records[0]['sug_delek_nm']

            # קביעה אם הרכב חשמלי או לא
            is_electric = 'חשמל' in fuel_type

            # חיפוש המידע הנוסף בדאטהבייס
            db_record = search_vehicle_in_db(make, model, is_electric)

    return render_template('index.html', records=records, db_record=db_record)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
