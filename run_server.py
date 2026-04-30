import os

from server import app, medical_data


def main() -> None:
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Loaded {len(medical_data)} medical records from medicine_data.csv")

    try:
        from waitress import serve

        print(f"NeuroCure+ server starting with Waitress on http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        print("Waitress is not installed; falling back to the Flask development server.")
        print(f"NeuroCure+ server starting on http://{host}:{port}")
        app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
