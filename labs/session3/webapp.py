"""Local web UI for ingest / ask / report.

Terminals generally don't shape/reorder Arabic (RTL) text correctly, so
running these tools directly in a terminal can show Arabic content
backwards even though the underlying data is correct. A browser renders
bidi text correctly, so this wraps the same functions used by ingest.py,
ask.py, and report.py behind a small local Flask server + single-page UI.

Run:
    python3 webapp.py
Then open http://localhost:5050
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from flask import Flask, jsonify, request, send_from_directory

import ask
import config
import ingest
import report

app = Flask(__name__, static_folder="web", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/ingest/preview")
def ingest_preview():
    try:
        scan = ingest.scan_documents()
    except FileNotFoundError:
        return jsonify({"error": "my_documents/ does not exist. Create it and add your documents first."}), 400

    if not scan["files"]:
        return jsonify({"error": "my_documents/ is empty. Add .pdf/.docx/.txt/.md files first."}), 400

    to_process = scan["to_process"]
    removed = scan["removed_rel_paths"]

    if not to_process and not removed:
        return jsonify({"upToDate": True, "totalFiles": len(scan["files"])})

    estimated_chunks = ingest.count_pending_chunks(to_process) if to_process else 0
    return jsonify(
        {
            "upToDate": False,
            "totalFiles": len(scan["files"]),
            "toProcess": [rel for _, rel, _ in to_process],
            "removed": removed,
            "estimatedChunks": estimated_chunks,
            "estimatedSeconds": estimated_chunks * 7,
        }
    )


@app.route("/api/ingest/run", methods=["POST"])
def ingest_run():
    try:
        scan = ingest.scan_documents()
    except FileNotFoundError:
        return jsonify({"error": "my_documents/ does not exist."}), 400

    if not scan["to_process"] and not scan["removed_rel_paths"]:
        return jsonify({"log": [], "counts": {}, "message": "Nothing to do — already up to date."})

    log = []
    try:
        _, _, structured_llm, vectorstore = ingest.build_resources()
        counts = ingest.run_ingestion(scan, vectorstore, structured_llm, on_progress=log.append)
    except Exception as e:
        return jsonify({"error": str(e), "log": log}), 500

    labeled_counts = {config.CATEGORY_LABELS[c]: n for c, n in counts.items()}
    return jsonify({"log": log, "counts": labeled_counts})


@app.route("/api/ask", methods=["POST"])
def ask_question():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    category_filter = data.get("filter") or None

    if not question:
        return jsonify({"error": "Question is empty."}), 400
    if category_filter and category_filter not in ask.FILTER_COMMANDS:
        return jsonify({"error": f"Unknown category '{category_filter}'."}), 400

    if not config.CHROMA_DIR.exists():
        return jsonify({"error": "No knowledge base yet. Build it first on the Ingest tab."}), 400

    try:
        llm, vectorstore = ask.build_resources()
        result = ask.answer_question(llm, vectorstore, question, category_filter)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)


@app.route("/api/report")
def get_report():
    if not config.CHROMA_DIR.exists():
        return jsonify({"error": "No knowledge base yet. Build it first on the Ingest tab."}), 400

    try:
        metadatas = report.collect_data()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not metadatas:
        return jsonify({"empty": True})

    return jsonify(report.compute_report_data(metadatas))


@app.route("/api/categories")
def get_categories():
    return jsonify(
        [{"value": c, "label": config.CATEGORY_LABELS[c]} for c in config.CATEGORIES]
    )


if __name__ == "__main__":
    print("Starting local web UI at http://localhost:5050")
    app.run(port=5050, debug=False)
