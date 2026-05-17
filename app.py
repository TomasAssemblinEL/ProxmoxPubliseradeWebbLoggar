from pathlib import Path

from flask import Flask, abort, render_template, send_file

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_CATEGORIES = ("VMM1", "VMM2", "MixTank", "Irrigation")

app = Flask(__name__)


def list_text_logs_by_category() -> dict[str, list[str]]:
    """Return sorted .txt log files grouped by fixed categories."""
    grouped_logs: dict[str, list[str]] = {}

    for category in LOG_CATEGORIES:
        category_dir = LOG_DIR / category
        if not category_dir.exists():
            grouped_logs[category] = []
            continue

        files = [
            p.name
            for p in category_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".txt"
        ]
        grouped_logs[category] = sorted(files)

    return grouped_logs


def resolve_log_file(category: str, filename: str) -> Path:
    """Resolve and validate a requested filename against category dir."""
    if category not in LOG_CATEGORIES:
        abort(404)

    if not filename.endswith(".txt"):
        abort(404)

    category_dir = (LOG_DIR / category).resolve()
    candidate = (category_dir / filename).resolve()
    try:
        candidate.relative_to(category_dir)
    except ValueError:
        abort(404)

    if not candidate.exists() or not candidate.is_file():
        abort(404)

    return candidate


@app.route("/")
def index():
    return render_template("index.html", logs_by_category=list_text_logs_by_category())


@app.route("/logs/<category>/<path:filename>")
def view_log(category: str, filename: str):
    log_path = resolve_log_file(category, filename)
    return send_file(log_path, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    for category in LOG_CATEGORIES:
        (LOG_DIR / category).mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=8080)
