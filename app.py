import os
import sys
sys.path.insert(0,'lib')
import pytz
import secrets
import requests

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime, timedelta

app = Flask(__name__)    

#key

@app.route('/')
def index():
    return 'Hello World'

@app.route('/data/node<int:id_gh>', methods=['GET'])
def getDataNode(id_gh):
    data_sensor = supabase.table('dataNode').select("*").eq("id_gh",id_gh).order("time", desc=True).limit(30).execute()
    data = data_sensor.data
    return jsonify(data)

@app.route('/monitoring/node<int:id_gh>',methods =['GET'])
def data_monitoring(id_gh):
    url = f"{backend_api_url}/data/node{id_gh}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data:  # Pastikan data tidak kosong
            tempData = float(round(data[-1]['temp'], 1))
            humidData = float(round(data[-1]['moist'], 1))
            soilData = float(round(data[-1]['soil'], 1))
            lumenData = float(round(data[-1]['lumen'], 1))
            return jsonify({"temp": tempData,
                            "humid": humidData,
                            "soil": soilData,
                            "lumen": lumenData})
        else:
            return jsonify({"error": "No data found"}), 404
    else:
        # Mengembalikan respons jika gagal mengambil data dari API
        return jsonify({"error": "Failed to fetch data from the API"}), response.status_code

@app.route('/line/node<int:id_gh>', methods = ['GET'])
def getdata(id_gh):
    url = f"{backend_api_url}/data/node{id_gh}"
    response = requests.get(url)
    
    # Memeriksa apakah request berhasil
    if response.status_code == 200:
        data = response.json()
        data = data[0:9]
        data_sensor = []

        for i in range(len(data)):
            original_time = data[i]['time']
            parsed_time = datetime.fromisoformat(original_time)
            adjusted_time = parsed_time + timedelta(hours=7)
            formatted_time = adjusted_time.strftime("%H:%M")
            data_sensor.append({
                'temp': data[i]['temp'],
                'humid':data[i]['moist'],
                'soil': data[i]['soil'],
                'lumen':data[i]['lumen'],
                'time': formatted_time
            })
            
        return jsonify({"data_sensor": data_sensor}), 200
    else:
        return jsonify({"error": "Failed to retrieve data"}), response.status_code
    
@app.route("/overview/gh_home", methods=["GET"])
def get_overview_gh_home():
    base_url = f"{backend_api_url}/data/node"
    total_nodes = 12

    lumen_series = []
    humid_series = []
    soil_series = []
    temp_series = []

    for i in range(1, total_nodes+1):
        url = f"{base_url}{i}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            lumen_series.append(data[-1]['lumen'])
            humid_series.append(data[-1]['moist'])
            soil_series.append(data[-1]['soil'])
            temp_series.append(data[-1]['temp'])
        else:
            lumen_series.append(None)
            humid_series.append(None)
            soil_series.append(None)
            temp_series.append(None)
    
    result = [
        { "type": "lumen", "series": lumen_series },
        { "type": "humid", "series": humid_series },
        { "type": "soil", "series": soil_series },
        { "type": "temp", "series": temp_series }]
    
    return jsonify(result), 200
    

@app.route("/production/average/node<int:id_gh>", methods=['GET'])
def average_production(id_gh):
    data_sensor = supabase.table('dataNode').select("*").eq("id_gh", id_gh).order("time", desc=True).limit(5).execute()
    data = data_sensor.data
    
    formatted_data = {
        "type":"celcius",
        "data":[{"x":item['temp'], 
                 "y":item['lumen']} for item in data]
    }
    
    return jsonify(formatted_data)

@app.route('/api/farmer', methods=['GET'])
def farmer_registered():
    response = supabase.table("farmer").select("*").execute()
    data_farmer = response.data
    return jsonify(data_farmer)

@app.route('/api/login', methods=['POST'])
def login_user():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        farmer = supabase.table("farmer").select("*").eq("email", email).eq("password", password).execute()

        if farmer.data:
            return jsonify({"farmer": farmer.data})
        else:
            return jsonify({"error": "Invalid email or password"}), 401 

    else:
        return jsonify({"error": "Failed to retrieve data"}), 404
        
@app.route('/admin', methods=['GET'])
def admin_petani():
    response = supabase.table("admin").select('*').execute()
    data = response.data
    return jsonify(data)
    
@app.route('/api/login-admin', methods=['POST'])
def login_admin():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')

        admin = supabase.table("admin").select("*").eq("email", email).eq("password", password).execute()

        if admin.data:
            return jsonify({"data_admin": admin.data})
        else:
            return jsonify({"error": "Invalid email or password"}), 401 

    else:
        return jsonify({"error": "Failed to retrieve data"}), 404
        
@app.route('/production/node<int:id_gh>', methods=['GET'])
def get_production_data(id_gh):
    # Ambil data produksi berdasarkan id_gh
    data_produksi = supabase.table('panen').select("*").eq("id_gh", id_gh).order("waktu_panen", desc=True).execute()
    data = data_produksi.data

    # Cek apakah data ada
    if not data:
        return jsonify({"message": "No production data found for this greenhouse"}), 404

    # Mengembalikan data dalam format JSON
    formatted_data = [
        {
            "id": item['id'],
            "id_gh": item['id_gh'],
            "id_varietas": item['id_varietas'],
            "jumlah_produksi": item['jumlah_produksi'],
            "waktu_panen": item['waktu_panen'],
            "created_at": item['created_at']
        }
        for item in data
    ]

    return jsonify(formatted_data), 200
        
@app.route('/pump/node<int:id_gh>', methods=['GET'])
def get_pump_data(id_gh):
    # Ambil data pompa berdasarkan id_gh
    data_pompa = supabase.table('pompa').select("id, time, status_pompa, id_gh").eq("id_gh", id_gh).order("time", desc=True).execute()
    data = data_pompa.data

    # Cek apakah data ada
    if not data:
        return jsonify({"message": "No pump data found for this greenhouse"}), 404

    # Mengembalikan data dalam format JSON
    formatted_data = [
        {
            "id": item['id'],
            "time": item['time'],
            "status_pompa": item['status_pompa'],
            "id_gh": item['id_gh']
        }
        for item in data
    ]

    return jsonify(formatted_data), 200
   
IDEAL_TEMP_RANGE = (20, 38)   
IDEAL_HUMID_RANGE = (20, 85)  
IDEAL_SOIL_RANGE = (1, 85)   
IDEAL_LUMEN_RANGE = (1, 50000) 

# Variabel untuk menyimpan data outlier secara global
outlier_data = {}

# Fungsi untuk mendeteksi apakah data keluar dari batas ideal
def is_outlier(value, ideal_range):
    return value < ideal_range[0] or value > ideal_range[1]

@app.route('/detect_outliers/node<int:id_gh>', methods=['GET'])
def detect_outliers_node(id_gh):
    global outlier_data

    # Ambil data historis dari Supabase
    data_sensor = supabase.table('dataNode').select("*").eq("id_gh", id_gh).order("time", desc=True).limit(10).execute()
    data = data_sensor.data

    # Variabel sementara untuk menyimpan data outlier per request
    temp_outliers = []
    humid_outliers = []
    soil_outliers = []
    lumen_outliers = []

    # Periksa setiap data sensor dan bandingkan dengan nilai ideal
    for record in data:
        temp = record['temp']
        humid = record['moist']
        soil = record['soil']
        lumen = record['lumen']

        # Jika nilai keluar dari rentang ideal, simpan sebagai outlier
        if is_outlier(temp, IDEAL_TEMP_RANGE):
            temp_outliers.append({
                "id_gh": id_gh,
                "time": record['time'],
                "value": temp
            })

        if is_outlier(humid, IDEAL_HUMID_RANGE):
            humid_outliers.append({
                "id_gh": id_gh,
                "time": record['time'],
                "value": humid
            })

        if is_outlier(soil, IDEAL_SOIL_RANGE):
            soil_outliers.append({
                "id_gh": id_gh,
                "time": record['time'],
                "value": soil
            })

        if is_outlier(lumen, IDEAL_LUMEN_RANGE):
            lumen_outliers.append({
                "id_gh": id_gh,
                "time": record['time'],
                "value": lumen
            })

    # Simpan atau update data outlier di variabel global hanya untuk id_gh yang terdeteksi
    outlier_data[id_gh] = {
        "temp_outliers": temp_outliers,
        "humid_outliers": humid_outliers,
        "soil_outliers": soil_outliers,
        "lumen_outliers": lumen_outliers,
    }

    # Mengembalikan hasil deteksi outlier
    return jsonify({  
        "temp_outliers": temp_outliers,
        "humid_outliers": humid_outliers,
        "soil_outliers": soil_outliers,
        "lumen_outliers": lumen_outliers
    }), 200

# Fungsi untuk mendeteksi apakah data keluar dari batas ideal
def is_outlier(value, ideal_range):
    return value < ideal_range[0] or value > ideal_range[1]

# Mengatur zona waktu Jakarta
jakarta_tz = pytz.timezone('Asia/Jakarta')

# Fungsi untuk mengambil waktu 3 hari yang lalu
def one_days_ago():
    current_time = datetime.now(jakarta_tz)
    one_days_ago = current_time - timedelta(days=1)
    return one_days_ago.isoformat()
    
@app.route('/outliers/all', methods=['GET'])
def get_all_outliers():
    global outlier_data

    # Waktu sekarang dan 3 hari yang lalu di zona waktu Jakarta
    one_days_ago_str = one_days_ago()

    all_outliers = {
        "temp_outliers": [],
        "humid_outliers": [],
        "soil_outliers": [],
        "lumen_outliers": []
    }

    # Iterasi untuk setiap id_gh (contoh 1-12)
    gh_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    for id_gh in gh_ids:
        # Ambil data dari Supabase untuk setiap gh berdasarkan id_gh dalam waktu hingga 3 hari yang lalu
        data_sensor = supabase.table('dataNode').select("*").eq("id_gh", id_gh).gt("time", one_days_ago_str).execute()
        data = data_sensor.data

        # Periksa setiap data sensor dan bandingkan dengan nilai ideal
        for record in data:
            temp = record['temp']
            humid = record['moist']
            soil = record['soil']
            lumen = record['lumen']

            # Jika nilai keluar dari rentang ideal, tambahkan sebagai outlier
            if is_outlier(temp, IDEAL_TEMP_RANGE):
                all_outliers["temp_outliers"].append({
                    "id_gh": id_gh,
                    "time": record['time'],
                    "value": temp
                })

            if is_outlier(humid, IDEAL_HUMID_RANGE):
                all_outliers["humid_outliers"].append({
                    "id_gh": id_gh,
                    "time": record['time'],
                    "value": humid
                })

            if is_outlier(soil, IDEAL_SOIL_RANGE):
                all_outliers["soil_outliers"].append({
                    "id_gh": id_gh,
                    "time": record['time'],
                    "value": soil
                })

            if is_outlier(lumen, IDEAL_LUMEN_RANGE):
                all_outliers["lumen_outliers"].append({
                    "id_gh": id_gh,
                    "time": record['time'],
                    "value": lumen
                })

    # Mengembalikan hasil outliers dari semua greenhouse
    return jsonify(all_outliers), 200
        
initial_seasons_humidity = [
    0.5904184, 0.5603031, 0.5928410, 0.6459634,
    0.8201091, 0.9302881, 1.0569065, 1.1487975,
    0.5904184, 1.2205394, 1.2380572, 1.2497575,
    1.2534695, 1.2760664, 1.2809087, 1.2869211,
    1.2983132, 1.3059009, 1.3003153, 1.3194530,
    1.2373641, 0.9771926, 0.7651836, 0.6677435
]

initial_seasons_temperature = [
    1.4227681, 1.4511122, 1.4250896, 1.3401034,
    1.1544908, 1.0556714, 0.9700989, 0.9174781,
    0.8863707, 0.8766794, 0.8720933, 0.8663235,
    0.8480551, 0.8466904, 0.8333904, 0.8204025,
    0.8118632, 0.7925173, 0.7789468, 0.7877064,
    0.8997661, 1.0854691, 1.2540448, 1.3555205
]

initial_seasons_lumen = [
    1.0, 0.9, 0.8, 0.85, 1.2, 1.15, 1.1, 1.05,
    0.95, 1.0, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35,
    1.4, 1.5, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85
]

# Initialize starting values
initial_level_humidity = 65.828728
initial_level_temperature = 25.311178
initial_level_lumen = 2889.0083

@app.route('/predictions_model/node<int:id_gh>')
def index_season(id_gh):
    def predict_humidity(y_t_minus_1, season_index):
        global initial_level_humidity
        season_t_minus_24 = initial_seasons_humidity[season_index]
        y_t = (0.9 * (y_t_minus_1 / season_t_minus_24)) + ((1 - 0.9) * initial_level_humidity)
        initial_level_humidity = y_t
        return y_t

    def predict_temperature(y_t_minus_1, season_index):
        global initial_level_temperature
        season_t_minus_24 = initial_seasons_temperature[season_index]
        y_t = (0.9 * (y_t_minus_1 / season_t_minus_24)) + ((1 - 0.9) * initial_level_temperature)
        initial_level_temperature = y_t
        return y_t
    
    def predict_lumen(y_t_minus_1, season_index):
        global initial_level_lumen
        season_t_minus_24 = initial_seasons_lumen[season_index]
        y_t = (0.9 * (y_t_minus_1 / season_t_minus_24)) + ((1 - 0.9) * initial_level_lumen)
        initial_level_lumen = y_t
        return y_t
    
    # Function to simulate incoming data and predictions
    def simulate_prediction(humidity, temperature, lumen, season_index):
        predicted_humidity = predict_humidity(humidity, season_index)
        predicted_temperature = predict_temperature(temperature, season_index)
        predicted_lumen = predict_lumen(lumen, season_index)

    jakarta_tz = pytz.timezone('Asia/Jakarta')
    current_time = datetime.now(jakarta_tz)
    
    # Dapatkan tanggal sehari yang lalu
    one_day_ago = current_time - timedelta(days=1)
    one_day_ago_str = one_day_ago.strftime('%Y-%m-%d')
    year, month, day = map(int, one_day_ago_str.split('-'))
    
    # Inisialisasi season_index
    season_index = 0
    
    results = []
    
    # Loop dari jam 00 hingga 23
    for hour in range(24):
        # Increment season_index untuk setiap jam
        season_index = hour % 24
    
        # Waktu mulai dan akhir untuk tiap jam
        start_of_hour = jakarta_tz.localize(datetime(year, month, day, hour, 0, 0))
        end_of_hour = jakarta_tz.localize(datetime(year, month, day, hour, 59, 59))
        
        # Konversi ke UTC
        start_of_hour_utc = start_of_hour.astimezone(pytz.utc)
        end_of_hour_utc = end_of_hour.astimezone(pytz.utc)
    
        # Query untuk rentang waktu tiap jam
        response = supabase.table('dataNode') \
                    .select("time, lumen, soil, moist, temp, id_gh") \
                    .eq("id_gh", id_gh) \
                    .order("time", desc=True) \
                    .gte("time", start_of_hour_utc.isoformat()) \
                    .lte("time", end_of_hour_utc.isoformat()) \
                    .limit(1) \
                    .execute()
    
        data = response.data
        if data:
            lumen = data[0]['lumen']
            temperature = data[0]['temp']
            humidity = data[0]['moist']
            
            predicted_humidity = predict_humidity(humidity, season_index)
            predicted_temperature = predict_temperature(temperature, season_index)
            predicted_lumen = predict_lumen(lumen , season_index)
    
            results.append({
                "Hour": hour,
                "Original Humidity": humidity,
                "Original Temperature": temperature,
                "Original Lumen": lumen,
                "Predicted Humidity": predicted_humidity,
                "Predicted Temperature": predicted_temperature,
                "Predicted Lumen": predicted_lumen
            })

    return jsonify(results), 200

@app.route('/check_all_gh', methods=['GET'])
def check_all_greenhouses():
    # Daftar ID greenhouse yang ingin dicek
    gh_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # Contoh ID greenhouse

    notifikasi = []

    for id_gh in gh_ids:
        # Waktu sekarang dan waktu 1 jam yang lalu di zona waktu Jakarta
        current_time = datetime.now(jakarta_tz)
        one_hour_ago = current_time - timedelta(hours=1)

        # Konversi waktu ke format string yang sesuai dengan database (misalnya ISO 8601)
        one_hour_ago_str = one_hour_ago.isoformat()

        # Ambil data dari Supabase untuk setiap gh berdasarkan id_gh dalam waktu 1 jam terakhir
        data_sensor = supabase.table('dataNode').select("*").eq("id_gh", id_gh).gt("time", one_hour_ago_str).execute()
        data = data_sensor.data

        if len(data) == 0:
            # Jika tidak ada data, tambahkan notifikasi
            notifikasi.append(f"Tidak ada data dari greenhouse {id_gh} dalam 1 jam terakhir.")
    
    if len(notifikasi) > 0:
        # Jika ada notifikasi error, return notifikasi tersebut
        return jsonify({
            "notifikasi": notifikasi
        }), 404
    else:
        # Tidak memberikan respon apapun jika semua data berhasil diambil
        return '', 204  # No Content


@app.route('/datetime/node<int:id_gh>', methods=['GET'])
def get_all_data_node(id_gh):
    # Ambil seluruh data historis dari Supabase berdasarkan id_gh tanpa membatasi waktu
    data_sensor = supabase.table('dataNode').select("*").eq("id_gh", id_gh).order("time", desc=True).execute()
    data = data_sensor.data

    # Variabel untuk menyimpan data berdasarkan kategori sensor
    temp_data = []
    humid_data = []
    soil_data = []
    lumen_data = []

    # Iterasi setiap record dan pisahkan berdasarkan jenis data sensor
    for record in data:
        temp_data.append({
            "id_gh": id_gh,
            "time": record['time'],
            "temp_value": record['temp']
        })
        
        humid_data.append({
            "id_gh": id_gh,
            "time": record['time'],
            "moist_value": record['moist']  # 'moist' digunakan sebagai 'humid' dalam database
        })
        
        soil_data.append({
            "id_gh": id_gh,
            "time": record['time'],
            "soil_value": record['soil']
        })
        
        lumen_data.append({
            "id_gh": id_gh,
            "time": record['time'],
            "lumen_value": record['lumen']
        })

    # Mengembalikan data yang dipisah untuk setiap jenis sensor
    return jsonify({
        "temp_data": temp_data,
        "humid_data": humid_data,
        "soil_data": soil_data,
        "lumen_data": lumen_data
    }), 200


if __name__ == "__main__":
    app.run(debug=True)

