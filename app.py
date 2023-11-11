from flask import Flask, jsonify, request, render_template
from src.utils import *
from src.preprocess import *
from src.utils import read_df

HOST_IP = '0.0.0.0'
HOST_PORT = 8000

app = Flask(__name__)

@app.route('/get_data', methods=['GET'])
def get_data():
    df = read_df("data/main.csv", n=100)
    data = df[['datetime', 'open', 'high', 'low', 'close']].to_dict('records')
    return jsonify(data)

@app.route('/get_models', methods=['GET'])
def get_models():
    # Placeholder for actual model retrieval logic
    models = ["Model 1", "Model 2", "Model 3"]
    return jsonify(models)

@app.route('/sell_all', methods=['POST'])
def sell_all():
    # Implement the logic to sell all
    # Placeholder response
    return jsonify({"success": True, "message": "Sold all positions"})

@app.route('/opt_out', methods=['POST'])
def opt_out():
    # Implement the logic for opting out
    # Placeholder response
    return jsonify({"success": True, "message": "Opted out successfully"})

@app.route('/set_params', methods=['POST'])
def set_params():
    # Retrieve and set parameters for your model
    params = request.json
    # Placeholder for setting parameters
    return jsonify({"success": True, "message": "Parameters set"})

@app.route('/get_roi_day', methods=['GET'])
def get_roi_day():
    # Placeholder for daily ROI retrieval logic
    daily_roi = "5.2%"
    return jsonify({"daily_roi": daily_roi})

@app.route('/get_roi_month', methods=['GET'])
def get_roi_month():
    # Placeholder for monthly ROI retrieval logic
    monthly_roi = "10.4%"
    return jsonify({"monthly_roi": monthly_roi})

@app.route('/get_roi_all_time', methods=['GET'])
def get_roi_all_time():
    # Placeholder for all-time ROI retrieval logic
    all_time_roi = "150%"
    return jsonify({"all_time_roi": all_time_roi})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)
