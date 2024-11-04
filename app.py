from flask import Flask, render_template, request, jsonify
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'json'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

model = joblib.load('driver_behavior_model.joblib')

scaler = StandardScaler()

def preprocess_and_predict(data):
    try:
        if 'ATTRIBUTES' in data.columns:
            attributes_df = pd.json_normalize(data['ATTRIBUTES'].apply(json.loads))
            data = data.drop(columns=['ATTRIBUTES'])
            data = pd.concat([data, attributes_df], axis=1)

        if 'time' in data.columns:
            data['time'] = pd.to_datetime(data['time'], errors='coerce')

        if 'hdop' in data.columns:
            data = data[data['hdop'] <= 5]
        if 'pdop' in data.columns:
            data = data[data['pdop'] <= 5]

        data = data.sort_values(by='time').reset_index(drop=True)

        data['speed_diff'] = data['SPD'].diff()
        time_diff = data['time'].diff().dt.total_seconds()
        data['acceleration'] = data['speed_diff'] / time_diff.replace({0: np.nan}).fillna(method='bfill')

        acceleration_cap = 10
        data['acceleration'] = data['acceleration'].clip(lower=-acceleration_cap, upper=acceleration_cap)
        data['acceleration'] = data['acceleration'].fillna(0)
        data['deceleration'] = data['acceleration'].apply(lambda x: x if x < 0 else 0)
        data['acceleration'] = data['acceleration'].apply(lambda x: x if x > 0 else 0)

        data['idle_time'] = ((data['SPD'] == 0) & (data['ignition'] == True)).rolling(window=3).sum().ge(2).astype(int)
        data['stop_frequency'] = ((data['SPD'] == 0) & (data['motion'] == False)).rolling(window=3).sum().ge(2).astype(int)

        data['hour'] = data['time'].dt.hour

        numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
        data[numeric_columns] = scaler.fit_transform(data[numeric_columns].fillna(0))

        # Original feature names used for prediction
        features = ['SPD', 'acceleration', 'deceleration', 'stop_frequency', 'idle_time']
        X = data[features].fillna(0)
        predictions = model.predict(X)

        # Map old behavior categories to new display names
        data['behavior_category'] = np.where(predictions == 1, 'high-risk', 'safe')

        aggressive_percentage = (data['behavior_category'] == 'high-risk').mean() * 100

        data['time'] = data['time'].fillna(pd.Timestamp('1970-01-01')).astype(str)

        # Calculate the contributions
        X_df = pd.DataFrame(X, columns=features)
        contributions = calculate_contributions(model, X_df, predictions)

        # Apply display name mapping for output
        display_name_mapping = {
            'SPD': 'high_spd',
            'acceleration': 'hard_acceleration',
            'deceleration': 'deceleration',
            'stop_frequency': 'frequent_stops',
            'idle_time': 'idle_time'
        }
        data_display = data.rename(columns=display_name_mapping)

        return data_display[['time', 'high_spd', 'hard_acceleration', 'deceleration', 'frequent_stops', 'idle_time', 'behavior_category']], aggressive_percentage, contributions

    except Exception as e:
        raise RuntimeError(f"Error during preprocessing and prediction: {str(e)}")


def calculate_contributions(model, X, predictions):
    aggressive_indices = np.where(predictions == 1)[0]
    feature_contributions = {feature: 0 for feature in X.columns}

    for i in aggressive_indices:
        base_prob = model.predict_proba([X.iloc[i]])[0][1]  # Probability of being aggressive
        for feature in X.columns:
            modified_row = X.iloc[i].copy()
            modified_row[feature] = 0  # Set feature to 0 to see its contribution
            modified_prob = model.predict_proba([modified_row])[0][1]
            feature_contributions[feature] += base_prob - modified_prob

    total_contribution = sum(feature_contributions.values())
    feature_contributions = {k: v / total_contribution for k, v in feature_contributions.items()}

    return feature_contributions

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if filename.rsplit('.', 1)[1].lower() == 'csv':
            data = pd.read_csv(file_path)
        elif filename.rsplit('.', 1)[1].lower() == 'json':
            data = pd.read_json(file_path)
        else:
            return jsonify({'status': 'error', 'message': 'Invalid file type'})

        try:
            result, aggressive_percentage, contributions = preprocess_and_predict(data)
            return jsonify({
                'status': 'success',
                'message': 'File uploaded and processed',
                'result': result.to_dict(orient='records'),
                'aggressive_percentage': aggressive_percentage,
                'contributions': contributions
            })
        except RuntimeError as e:
            return jsonify({'status': 'error', 'message': str(e)})

    return jsonify({'status': 'error', 'message': 'Invalid file type'})




# iwant to change the spd to high spd and the acceleration to hard acceleration and stop frequency to frequent stops and engine idling to idle time 
if __name__ == '__main__':
    app.run(debug=True)
