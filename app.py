from pathlib import Path
from time import time
from datetime import date, datetime, timedelta
import csv
from io import StringIO
import os

from flask import Flask, Response, abort, render_template, send_file, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOGWEB_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "mixtank.db"
LOG_DIR = BASE_DIR / "logs"
LOG_CATEGORIES = ("VMM1", "VMM2", "MixTank", "Irrigation")
LOG_DAYS_WINDOW = 5

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class MixtankMeasurement(db.Model):
    __tablename__ = "measurements"
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False, index=True)
    ph = db.Column(db.Float, nullable=False)
    temp = db.Column(db.Float, nullable=False)
    ec = db.Column(db.Float, nullable=False)
    tillsatt_ph_minus_ml = db.Column(db.Float, nullable=False, default=0)
    tillsatt_goding_ml = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Measurement {self.datum} PH={self.ph}>"


# Create database tables on app startup
with app.app_context():
    db.create_all()


def list_text_logs_by_category() -> dict[str, list[str]]:
    """Return sorted .txt log files from the last N days per category."""
    grouped_logs: dict[str, list[str]] = {}
    cutoff_timestamp = time() - (LOG_DAYS_WINDOW * 24 * 60 * 60)

    for category in LOG_CATEGORIES:
        category_dir = LOG_DIR / category
        if not category_dir.exists():
            grouped_logs[category] = []
            continue

        files = []
        for p in category_dir.iterdir():
            if not p.is_file() or p.suffix.lower() != ".txt":
                continue

            if p.stat().st_mtime < cutoff_timestamp:
                continue

            files.append(p.name)

        grouped_logs[category] = sorted(files)

    return grouped_logs


def cleanup_old_logs() -> None:
    """Delete .txt log files older than the configured day window."""
    cutoff_timestamp = time() - (LOG_DAYS_WINDOW * 24 * 60 * 60)

    for category in LOG_CATEGORIES:
        category_dir = LOG_DIR / category
        if not category_dir.exists():
            continue

        for p in category_dir.iterdir():
            if not p.is_file() or p.suffix.lower() != ".txt":
                continue

            if p.stat().st_mtime >= cutoff_timestamp:
                continue

            p.unlink(missing_ok=True)


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
    return render_template("portal.html")


@app.route("/loggar")
def logs_index():
    return render_template("index.html", logs_by_category=list_text_logs_by_category())


@app.route("/logs/<category>/<path:filename>")
def view_log(category: str, filename: str):
    log_path = resolve_log_file(category, filename)
    return send_file(log_path, mimetype="text/plain; charset=utf-8")


@app.route("/mixtank", methods=["GET", "POST"])
def mixtank_index():
    if request.method == "POST":
        try:
            measurement = MixtankMeasurement(
                datum=datetime.strptime(request.form["datum"], "%Y-%m-%d").date(),
                ph=float(request.form["ph"]),
                temp=float(request.form["temp"]),
                ec=float(request.form["ec"]),
                tillsatt_ph_minus_ml=float(request.form.get("tillsatt_ph_minus_ml", 0)),
                tillsatt_goding_ml=float(request.form.get("tillsatt_goding_ml", 0)),
            )
            db.session.add(measurement)
            db.session.commit()
            return redirect(url_for("mixtank_index"))
        except (ValueError, KeyError) as e:
            abort(400)

    measurements = MixtankMeasurement.query.order_by(MixtankMeasurement.datum.desc()).all()

    cutoff_date = date.today() - timedelta(days=29)
    chart_measurements = (
        MixtankMeasurement.query
        .filter(MixtankMeasurement.datum >= cutoff_date)
        .order_by(MixtankMeasurement.datum.asc())
        .all()
    )
    chart_data = {
        "labels": [m.datum.isoformat() for m in chart_measurements],
        "ph": [m.ph for m in chart_measurements],
        "temp": [m.temp for m in chart_measurements],
        "ec": [m.ec for m in chart_measurements],
    }

    return render_template("mixtank.html", measurements=measurements, chart_data=chart_data)


@app.route("/mixtank/<int:measurement_id>/delete", methods=["POST"])
def mixtank_delete_measurement(measurement_id: int):
    measurement = db.session.get(MixtankMeasurement, measurement_id)
    if measurement is None:
        abort(404)

    db.session.delete(measurement)
    db.session.commit()
    return redirect(url_for("mixtank_index"))


@app.route("/mixtank/export.csv")
def mixtank_export_csv():
    days_param = request.args.get("days", default="", type=str).strip()
    query = MixtankMeasurement.query

    if days_param:
        try:
            days = int(days_param)
        except ValueError:
            abort(400)

        if days <= 0:
            abort(400)

        cutoff_date = date.today() - timedelta(days=days - 1)
        query = query.filter(MixtankMeasurement.datum >= cutoff_date)

    measurements = query.order_by(MixtankMeasurement.datum.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "datum",
        "ph",
        "temp_c",
        "ec",
        "tillsatt_ph_minus_ml",
        "tillsatt_goding_ml",
        "skapad_tid",
    ])

    for m in measurements:
        writer.writerow([
            m.datum.isoformat(),
            m.ph,
            m.temp,
            m.ec,
            m.tillsatt_ph_minus_ml,
            m.tillsatt_goding_ml,
            m.created_at.isoformat() if m.created_at else "",
        ])

    csv_data = output.getvalue()
    output.close()

    filename = "mixtank-measurements.csv"
    if days_param:
        filename = f"mixtank-measurements-last-{days_param}-days.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    for category in LOG_CATEGORIES:
        (LOG_DIR / category).mkdir(exist_ok=True)
    cleanup_old_logs()
    app.run(host="0.0.0.0", port=8080)
