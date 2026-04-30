from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd # CSV read korar jonno

app = Flask(__name__)
CORS(app)

# --- CSV Data Load Logic ---
try:
    # CSV file read kora hochhe
    df = pd.read_csv('medicine_data.csv')
    print("Medical Database Loaded Successfully!")
except Exception as e:
    print(f"Error loading CSV: {e}")
    df = pd.DataFrame() # Khali dataframe jate crash na kore

# --- Chatbot API (Diagnosis) ---
@app.route('/api/chat', methods=['GET'])
def chat_assistant():
    user_msg = request.args.get("message", "").lower()
    
    if not user_msg:
        return jsonify({"status": "error", "message": "No input"}), 400

    # CSV-r 'Symptom' column scan korchi
    found_row = None
    for index, row in df.iterrows():
        if str(row['Symptom']).lower() in user_msg:
            found_row = row
            break

    if found_row is not None:
        return jsonify({
            "status": "success",
            "symptom": found_row['Symptom'],
            "medicine": found_row['Medicine'],
            "dosage": found_row['Dosage'],
            "precaution": found_row['Precaution'],
            "severity": found_row['Severity']
        })
    else:
        return jsonify({"status": "not_found"})

# --- Search Engine API (Specific Medicine Search) ---
@app.route('/api/search', methods=['GET'])
def search_medicine():
    med_name = request.args.get("name", "").lower()
    
    # CSV-r 'Medicine' column-e match khujchi
    match = df[df['Medicine'].str.lower() == med_name]
    
    if not match.empty:
        res = match.iloc[0] # Prothom match-ta nilam
        return jsonify({
            "status": "success",
            "medicine": res['Medicine'],
            "symptom": res['Symptom'],
            "dosage": res['Dosage'],
            "precaution": res['Precaution'],
            "severity": res['Severity']
        })
    else:
        return jsonify({"status": "not_found"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)