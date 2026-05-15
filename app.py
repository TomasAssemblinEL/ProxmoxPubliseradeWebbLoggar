from pathlib import Path

from flask import Flask, abort, render_template, send_file

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

app = Flask(__name__)


def list_text_logs() -> list[str]:
    """Return sorted .txt log files from LOG_DIR."""
    if not LOG_DIR.exists():
        return []

    files = [
        p.name
        for p in LOG_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt"
    ]
    return sorted(files)


def resolve_log_file(filename: str) -> Path:
    """Resolve and validate a requested filename against LOG_DIR."""
    if not filename.endswith(".txt"):
        abort(404)

    candidate = (LOG_DIR / filename).resolve()
    try:
        candidate.relative_to(LOG_DIR.resolve())
    except ValueError:
        abort(404)

    if not candidate.exists() or not candidate.is_file():
        abort(404)

    return candidate


@app.route("/")
def index():
    return render_template("index.html", logs=list_text_logs())


@app.route("/logs/<path:filename>")
def view_log(filename: str):
    log_path = resolve_log_file(filename)
    return send_file(log_path, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=8080)
