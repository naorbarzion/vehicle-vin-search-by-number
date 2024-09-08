import os
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

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
            return data['result']['records']
        else:
            return []
    except Exception as e:
        print(f"Failed to retrieve data: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    records = None
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        records = fetch_vehicle_data(vehicle_number)
    
    return render_template('index.html', records=records)

if __name__ == '__main__':
    # Listen on the appropriate port
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
