from pathlib import Path
import csv
import datetime
import logging
import re

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv

from gemini_service import (
    GeminiServiceError,
    fetch_medicine_details,
    generate_chat_reply,
    is_gemini_configured,
)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CSV_PATH = BASE_DIR / "medicine_data.csv"
EXPECTED_COLUMNS = ["Symptom", "Medicine", "Dosage", "Precaution", "Severity"]

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)
app.logger.setLevel(logging.INFO)


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def is_header_like_row(row: dict) -> bool:
    values = {normalize_text(row.get(column, "")) for column in EXPECTED_COLUMNS}
    header_values = {normalize_text(column) for column in EXPECTED_COLUMNS}
    return values == header_values or ("severity" in values and "dosage" in values and "medicine" in values)


def load_medical_data() -> list[dict]:
    records = []
    seen = set()

    with CSV_PATH.open(newline='', encoding='utf-8-sig') as csv_file:
        reader = csv.DictReader(csv_file)
        for raw_row in reader:
            row = {column: str(raw_row.get(column, '')).strip() for column in EXPECTED_COLUMNS}

            if is_header_like_row(row):
                continue
            if not row['Symptom'] or not row['Medicine']:
                continue

            row['symptom_key'] = normalize_text(row['Symptom'])
            row['medicine_key'] = normalize_text(row['Medicine'])

            dedupe_key = tuple(row[column] for column in EXPECTED_COLUMNS)
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            records.append(row)

    return records


medical_data = load_medical_data()


def format_record(row: dict) -> dict:
    return {
        'symptom': row['Symptom'],
        'medicine': row['Medicine'],
        'dosage': row['Dosage'],
        'precaution': row['Precaution'],
        'severity': row['Severity'],
    }


def search_symptoms(message: str) -> list[dict]:
    query = normalize_text(message)
    if not query:
        return []

    query_tokens = [token for token in query.split() if token]
    matches = []

    for row in medical_data:
        symptom_key = row['symptom_key']
        medicine_key = row['medicine_key']
        score = 0

        if query == symptom_key:
            score += 120
        if symptom_key and symptom_key in query:
            score += 80
        if any(token in symptom_key for token in query_tokens):
            score += 25
        if any(token in medicine_key for token in query_tokens):
            score += 10

        if score > 0:
            matches.append((score, format_record(row)))

    matches.sort(key=lambda item: (-item[0], item[1]['symptom'], item[1]['medicine']))

    unique_matches = []
    seen = set()
    for _, item in matches:
        key = (item['symptom'], item['medicine'])
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append(item)

    return unique_matches[:5]


def search_medicines(query: str) -> list[dict]:
    query_key = normalize_text(query)
    if not query_key:
        return []

    results = []
    for row in medical_data:
        medicine_key = row['medicine_key']
        score = 0

        if query_key == medicine_key:
            score += 120
        if query_key in medicine_key:
            score += 80
        if all(token in medicine_key for token in query_key.split()):
            score += 30

        if score > 0:
            results.append((score, format_record(row)))

    results.sort(key=lambda item: (-item[0], item[1]['medicine'], item[1]['symptom']))

    unique_results = []
    seen = set()
    for _, item in results:
        key = (item['medicine'], item['symptom'])
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(item)

    return unique_results[:10]


def local_database_available() -> bool:
    return bool(medical_data)


@app.route('/')
def home():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path: str):
    return send_from_directory(FRONTEND_DIR, path)


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify(
        {
            'status': 'ok',
            'records': len(medical_data),
            'local_database_available': local_database_available(),
            'gemini_configured': is_gemini_configured(),
            'server_time': datetime.datetime.now().isoformat(),
        }
    )


@app.route('/api/chat', methods=['GET', 'POST'])
def chat_endpoint():
    payload = request.get_json(silent=True) or {}
    user_message = payload.get('message') if request.method == 'POST' else request.args.get('message', '')
    user_message = (user_message or '').strip()

    if not user_message:
        return jsonify({'status': 'error', 'message': 'Message is empty'}), 400

    matches = search_symptoms(user_message)
    if not matches and is_gemini_configured():
        try:
            gemini_reply = generate_chat_reply(user_message)
            return jsonify(
                {
                    'status': 'success',
                    'reply': gemini_reply['reply'],
                    'results': [],
                    'server_time': datetime.datetime.now().isoformat(),
                    'model': os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'),
                    'source': gemini_reply['source'],
                    'fallback_used': True,
                    'disclaimer': gemini_reply['disclaimer'],
                }
            )
        except GeminiServiceError as exc:
            app.logger.warning('Gemini chat fallback failed: %s', exc)

    if not matches:
        return jsonify(
            {
                'status': 'not_found',
                'reply': 'I could not match those symptoms in the medical database, and the AI fallback is unavailable right now. Please consult a doctor for a proper diagnosis.',
                'results': [],
                'server_time': datetime.datetime.now().isoformat(),
                'model': 'NeuroCure+ Medical AI',
                'source': 'local',
                'fallback_used': False,
            }
        )

    top_match = matches[0]
    reply_lines = [
        f"The closest match is {top_match['symptom']}.",
        f"Suggested medicine: {top_match['medicine']}.",
        f"Dosage: {top_match['dosage']}.",
        f"Precaution: {top_match['precaution']}.",
        f"Severity: {top_match['severity']}."
    ]

    if len(matches) > 1:
        alternatives = ', '.join(match['symptom'] for match in matches[1:4])
        reply_lines.append(f"Other related matches: {alternatives}.")

    return jsonify(
        {
            'status': 'success',
            **top_match,
            'results': matches,
            'reply': ' '.join(reply_lines),
            'server_time': datetime.datetime.now().isoformat(),
            'model': 'NeuroCure+ Medical AI',
            'source': 'local',
            'fallback_used': False,
        }
    )


@app.route('/api/search', methods=['GET'])
def search_medicine():
    medicine_name = request.args.get('name', '').strip()
    if not medicine_name:
        return jsonify({'status': 'error', 'message': 'Medicine name is empty'}), 400

    matches = search_medicines(medicine_name)
    if not matches:
        if is_gemini_configured():
            try:
                gemini_result = fetch_medicine_details(medicine_name)
                result_payload = {
                    'symptom': 'General medicine information generated by Gemini',
                    'medicine': gemini_result['medicine'],
                    'dosage': gemini_result['dosage'],
                    'precaution': gemini_result['summary'],
                    'severity': 'AI Reference',
                    'side_effects': gemini_result['side_effects'],
                    'contraindications': gemini_result['contraindications'],
                    'summary': gemini_result['summary'],
                    'source': gemini_result['source'],
                    'disclaimer': gemini_result['disclaimer'],
                }

                return jsonify(
                    {
                        'status': 'success',
                        'count': 1,
                        'results': [result_payload],
                        'fallback_used': True,
                        **result_payload,
                    }
                )
            except GeminiServiceError as exc:
                app.logger.warning('Gemini medicine fallback failed: %s', exc)

        return jsonify(
            {
                'status': 'not_found',
                'results': [],
                'source': 'local',
                'fallback_used': False,
            }
        )

    return jsonify(
        {
            'status': 'success',
            'count': len(matches),
            'results': matches,
            **matches[0],
            'source': 'local',
            'fallback_used': False,
        }
    )


if __name__ == '__main__':
    print(f"Loaded {len(medical_data)} medical records from {CSV_PATH.name}")
    
    port = int(os.environ.get('PORT', 5000))
    print(f'NeuroCure+ server starting on http://0.0.0.0:{port}')
    
    app.run(host='0.0.0.0', port=port, debug=False)
