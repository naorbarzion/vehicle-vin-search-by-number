import pandas as pd
import requests
from flask import Flask, render_template, request
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# הגדרות חיבור ל-PostgreSQL
DB_HOST = "dpg-crfIn63v2p9s73d3pmo0-a.frankfurt-postgres.render.com"  # החלף לפי מה שקיבלת מה-Render
DB_NAME = "fmcvehicleslist"
DB_USER = "test"
DB_PASSWORD = "FPHmIbjIPYymNIQlHUgiBUPJuEc3L26z"

# פונקציה לחיבור ל-PostgreSQL
def connect_to_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# קריאת הנתונים מקובץ ה-Excel
def load_data_from_excel():
    file_path = "./data/fmc vehicles list.xlsx"  # הנתיב לקובץ ה-Excel ששמור בפרויקט
    xls = pd.ExcelFile(file_path)
    
    # קריאת הטאבים של הרכבים הרגילים והחשמליים
    regular_vehicles_df = pd.read_excel(xls, 'fmc vehicles list')
    electric_vehicles_df = pd.read_excel(xls, 'fmc vehicles list electric')
    
    return regular_vehicles_df, electric_vehicles_df

# פונקציה לחיפוש תמיכה בקילומטראז' ודלק ב-PostgreSQL
def check_support_from_db(model, year, fuel_type):
    conn = connect_to_db()
    cur = conn.cursor()

    # יצירת שאילתה בהתאם לסוג הדלק
    if fuel_type == "בנזין":
        query = sql.SQL("""
            SELECT support_kilometer_reading, support_fuel_level
            FROM regular_vehicles
            WHERE model = %s AND year_start <= %s AND year_end >= %s
        """)
    elif fuel_type == "חשמל":
        query = sql.SQL("""
            SELECT support_kilometer_reading, support_fuel_level
            FROM electric_vehicles
            WHERE model = %s AND year_start <= %s AND year_end >= %s
        """)

    cur.execute(query, (model, year, year))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        return {
            'תמיכה בקילומטראז': result[0],
            'תמיכה במפלס דלק': result[1]
        }
    else:
        return None

# קריאה ל-API לפי מספר רכב
def get_vehicle_data_from_api(vehicle_number):
    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id=your_resource_id&q={vehicle_number}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        records = data.get('result', {}).get('records', [])
        return records
    else:
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    api_records = None
    support_data = None  # זה ישמור את נתוני התמיכה בקילומטראז ודלק
    if request.method == "POST":
        vehicle_number = request.form.get("vehicle_number")

        # שלב 1 - קריאה ל-API כדי לקבל את נתוני הרכב
        api_records = get_vehicle_data_from_api(vehicle_number)

        if api_records:
            # שלב 2 - שימוש במודל ושנה מה-API כדי לבדוק תמיכה בקילומטראז ודלק ב-DB
            model = api_records[0]['kinuy_mishari']
            year = api_records[0]['shnat_yitzur']
            fuel_type = api_records[0]['sug_delek_nm']

            support_data = check_support_from_db(model, year, fuel_type)

    return render_template("index.html", api_records=api_records, support_data=support_data)

if __name__ == "__main__":
    app.run(debug=True)
