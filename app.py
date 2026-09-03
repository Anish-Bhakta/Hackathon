import os
import uuid
import base64
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from config import Config
from database.db import fetch_all, execute
from ocr.scanner import scan_image
from extraction.extractor import extract
from extraction.gs1_parser import parse_gs1_digital_link
from extraction.api_lookup import fetch_product_by_barcode
from compliance.checker import validate
from reports.pdf_report import generate
from camera.smart_camera import scan_with_phone_camera

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.REPORT_FOLDER, exist_ok=True)

ALLOWED = {"jpg", "jpeg", "png"}


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@app.errorhandler(413)
def big(e):
    flash("Image is too large. Maximum size is 5 MB.", "danger")
    return redirect(url_for("index"))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/lookup/<barcode>")
def api_lookup(barcode):
    gs1_info = parse_gs1_digital_link(barcode)
    lookup_code = gs1_info.get("gtin") or barcode
    product_info = fetch_product_by_barcode(lookup_code)
    return jsonify({
        "barcode": barcode,
        "gs1_info": gs1_info,
        "product_info": product_info,
    })


@app.post("/api/parse-gs1")
def api_parse_gs1():
    body = request.get_json() or {}
    inp = body.get("input") or ""
    gs1_info = parse_gs1_digital_link(inp)
    return jsonify(gs1_info)


def process_and_save_scan(image_path, barcode_override=""):
    raw_ocr, clean_ocr, detected_barcode = scan_image(image_path)
    barcode = barcode_override or detected_barcode

    data = extract(clean_ocr, barcode)
    fields, summary = validate(data)

    image_name = os.path.basename(image_path)
    customer_care_val = data.get("customer_care") or data.get("consumer_care", "")

    cols = [
        "image_name",
        "product_name",
        "manufacturer_name",
        "manufacturer_address",
        "mrp",
        "net_quantity",
        "batch_number",
        "manufacturing_date",
        "expiry_date",
        "consumer_care",
        "customer_care",
        "country_of_origin",
        "product_description",
        "unit_of_measurement",
        "barcode",
        "gs1_digital_link",
        "image_url",
        "api_source",
        "compliance_score",
        "overall_status",
        "raw_ocr_text",
        "cleaned_ocr_text",
    ]

    vals = [
        image_name,
        data.get("product_name", "")[:500],
        data.get("manufacturer_name", "")[:500],
        data.get("manufacturer_address", "")[:1000],
        data.get("mrp", "")[:100],
        data.get("net_quantity", "")[:100],
        data.get("batch_number", "")[:150],
        data.get("manufacturing_date", "")[:100],
        data.get("expiry_date", "")[:100],
        customer_care_val[:500],
        customer_care_val[:500],
        data.get("country_of_origin", "")[:100],
        data.get("product_description", "")[:1000],
        data.get("unit_of_measurement", "")[:50],
        data.get("barcode", "")[:255],
        data.get("gs1_digital_link", "")[:1000],
        data.get("image_url", "")[:1000],
        data.get("api_source", "")[:100],
        summary["compliance_score"],
        summary["overall_status"],
        raw_ocr,
        clean_ocr,
    ]

    q = f"INSERT INTO inspections ({','.join(cols)}) VALUES ({','.join(['%s']*len(vals))})"
    iid = execute(q, vals)

    for key, x in fields.items():
        execute(
            """
            INSERT INTO inspection_fields
            (inspection_id, field_name, extracted_value, status, confidence, validation_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                iid,
                key,
                str(x["extracted_value"])[:1000],
                x["status"],
                x["confidence"],
                str(x["validation_message"])[:1000],
            ),
        )

    return iid


@app.post("/scan")
def scan():
    direct_barcode = request.form.get("barcode_input", "").strip()
    camera_base64 = request.form.get("camera_image_base64", "").strip()
    f = request.files.get("image")

    image_path = None

    if f and f.filename and allowed(f.filename):
        name = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
        image_path = os.path.join(Config.UPLOAD_FOLDER, name)
        f.save(image_path)

    elif camera_base64:
        try:
            if "," in camera_base64:
                camera_base64 = camera_base64.split(",", 1)[1]
            img_data = base64.b64decode(camera_base64)
            name = f"cam_{uuid.uuid4().hex}.jpg"
            image_path = os.path.join(Config.UPLOAD_FOLDER, name)
            with open(image_path, "wb") as out_f:
                out_f.write(img_data)
        except Exception as e:
            print("Camera snapshot base64 error:", e)

    if not image_path:
        name = f"scan_{uuid.uuid4().hex}.png"
        image_path = os.path.join(Config.UPLOAD_FOLDER, name)
        with open(image_path, "wb") as empty_f:
            empty_f.write(b"")

    try:
        iid = process_and_save_scan(image_path, barcode_override=direct_barcode)
        return redirect(url_for("result", id=iid))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("index"))


@app.get("/smart-scan")
def smart_scan():
    try:
        image_path, barcode = scan_with_phone_camera()
        iid = process_and_save_scan(image_path, barcode_override=barcode)
        return redirect(url_for("result", id=iid))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("index"))


def load_inspection(id):
    ins = fetch_all("SELECT * FROM inspections WHERE id=%s", (id,))
    if not ins:
        return None, []
    fields = fetch_all("SELECT * FROM inspection_fields WHERE inspection_id=%s", (id,))
    return ins[0], fields


@app.get("/result/<int:id>")
def result(id):
    i, f = load_inspection(id)
    if not i:
        return "Inspection record not found", 404
    
    gs1_info = parse_gs1_digital_link(i.get("gs1_digital_link") or i.get("barcode") or "")
    return render_template("result.html", inspection=i, fields=f, gs1_info=gs1_info)


@app.get("/dashboard")
def dashboard():
    rows = fetch_all("SELECT overall_status, compliance_score, created_at FROM inspections")
    total = len(rows)
    avg = round(sum(float(x["compliance_score"]) for x in rows) / total, 2) if total else 0
    stats = {
        "total": total,
        "compliant": sum(x["overall_status"] == "COMPLIANT" for x in rows),
        "non": sum(x["overall_status"] == "NON-COMPLIANT" for x in rows),
        "review": sum(x["overall_status"] == "NEEDS REVIEW" for x in rows),
        "avg": avg,
    }
    recent = fetch_all("SELECT * FROM inspections ORDER BY created_at DESC LIMIT 5")
    return render_template("dashboard.html", stats=stats, recent=recent)


@app.get("/history")
def history():
    inspections = fetch_all("SELECT * FROM inspections ORDER BY created_at DESC")
    return render_template("history.html", inspections=inspections)


@app.get("/inspection/<int:id>")
def inspection(id):
    i, f = load_inspection(id)
    if not i:
        return "Inspection not found", 404
    gs1_info = parse_gs1_digital_link(i.get("gs1_digital_link") or i.get("barcode") or "")
    return render_template("inspection.html", inspection=i, fields=f, gs1_info=gs1_info)


@app.get("/report/<int:id>")
def report(id):
    i, f = load_inspection(id)
    if not i:
        return "Inspection record not found", 404
    path = os.path.join(Config.REPORT_FOLDER, f"inspection_{id}.pdf")
    image_full_path = os.path.join(Config.UPLOAD_FOLDER, i["image_name"]) if i.get("image_name") else ""
    generate(path, i, f, image_full_path)
    return send_file(path, as_attachment=True)


@app.get("/rules")
def rules():
    return render_template("rules.html")


@app.post("/rules/update")
def rules_update():
    flash("Compliance rules updated successfully.", "success")
    return redirect(url_for("rules"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
