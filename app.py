import os
from flask import Flask, request, render_template
import requests
from flask_sqlalchemy import SQLAlchemy
import csv

app = Flask(__name__)

# הגדרת החיבור למסד הנתונים (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://test:FPHmlbj1PYymNlQIHUgiBUPJuEc3L26z@dpg-crf1n63v2p9s73d3pmo0-a.frankfurt-postgres.render.com/fmcvehicleslist?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# מודל למסד הנתונים (לרכבי בנזין)
class Vehicle(db.Model):
    __tablename__ = 'fmc_vehicles_list'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    fuel_level = db.Column(db.Float, nullable=True)
    kilometer = db.Column(db.Boolean, nullable=True)  # האם תומך בקילומטראז'

# מודל למסד הנתונים (לרכבי חשמל)
class ElectricVehicle(db.Model):
    __tablename__ = 'fmc_vehicles_list_electric'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    battery_level = db.Column(db.Float, nullable=True)
    kilometer = db.Column(db.Boolean, nullable=True)  # האם תומך בקילומטראז'

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

# פונקציה לחיפוש רכב רגיל בדאטהבייס לפי מודל
def search_regular_vehicle_in_db(model):
    try:
        result = Vehicle.query.filter_by(model=model).first()
        return result
    except Exception as e:
        print(f"Database search error (regular vehicle): {e}")
        return None

# פונקציה לחיפוש רכב חשמלי בדאטהבייס לפי מודל
def search_electric_vehicle_in_db(model):
    try:
        result = ElectricVehicle.query.filter_by(model=model).first()
        return result
    except Exception as e:
        print(f"Database search error (electric vehicle): {e}")
        return None

# פונקציה ליצירת הטבלאות במידה והן לא קיימות
def create_tables_if_not_exist():
    try:
        db.create_all()  # זה יוצר את הטבלאות אם הן לא קיימות
        print("Tables checked and created if not exist.")
    except Exception as e:
        print(f"Error while creating tables: {e}")

# פונקציה ליבוא נתונים מתוך קובץ CSV
def import_data_from_csv():
    try:
        if not Vehicle.query.first():  # אם אין נתונים, נייבא מה-CSV
            with open('database/fmc_vehicles_list.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    vehicle = Vehicle(
                        make=row['Make'],
                        model=row['Model'],
                        fuel_level=None,  # אם יש עמודת fuel_level ב-CSV, עדכן כאן
                        kilometer=(row['Kilometer'] == '+')  # נבדוק אם יש תמיכה בקילומטראז'
                    )
                    db.session.add(vehicle)
                db.session.commit()

        if not ElectricVehicle.query.first():  # אם אין נתונים, נייבא מה-CSV של רכבי חשמל
            with open('database/fmc_vehicles_list_electric.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ev = ElectricVehicle(
                        make=row['Make'],
                        model=row['Model'],
                        battery_level=None,  # אם יש עמודת battery_level ב-CSV, עדכן כאן
                        kilometer=(row['Kilometer'] == '+')  # נבדוק אם יש תמיכה בקילומטראז'
                    )
                    db.session.add(ev)
                db.session.commit()

        print("Data imported successfully from CSV.")
    except Exception as e:
        print(f"Error while importing data from CSV: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    records = None
    db_record = None
    error_message = None

    # נוודא שהטבלאות קיימות ונייבא נתונים אם צריך
    create_tables_if_not_exist()
    import_data_from_csv()

    if request.method == 'POST':
        try:
            vehicle_number = request.form.get('vehicle_number')
            records = fetch_vehicle_data(vehicle_number)
            
            if records:
                model = records[0]['kinuy_mishari']

                # חיפוש בדאטהבייס לפי סוג רכב (חשמלי או רגיל)
                db_record = search_electric_vehicle_in_db(model)
                if not db_record:  # אם לא מצאנו ברכבים החשמליים, נחפש ברכבי בנזין
                    db_record = search_regular_vehicle_in_db(model)

                # בדיקה אם יש קריאת קילומטראז', סוללה או דלק
                if db_record:
                    if hasattr(db_record, 'battery_level') and db_record.battery_level is not None:
                        print(f"Battery level: {db_record.battery_level}")
                    elif hasattr(db_record, 'fuel_level') and db_record.fuel_level is not None:
                        print(f"Fuel level: {db_record.fuel_level}")
                    else:
                        print("Kilometer support:", db_record.kilometer)
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
