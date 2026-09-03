import re
from .gs1_parser import parse_gs1_digital_link
from .api_lookup import fetch_product_by_barcode

FIELDS = [
    "product_name",
    "manufacturer_name",
    "manufacturer_address",
    "mrp",
    "net_quantity",
    "batch_number",
    "manufacturing_date",
    "expiry_date",
    "customer_care",
    "country_of_origin",
    "product_description",
    "unit_of_measurement",
]


def first(pattern, text, flags=re.I):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def is_valid_product_name(value):
    """Reject OCR noise strings as product names."""
    if not value or len(value.strip()) < 3:
        return False

    cleaned = re.sub(r"[^A-Za-z0-9\s]", "", value).strip()
    if len(cleaned) < 3:
        return False

    if re.search(r"(?:CIN|Address|Phone|Mob|Tel|Plot|Gala|Floor|Road|Opp|Opposite|Street|www\.|http|Email)", value, re.I):
        return False

    letters = sum(char.isalpha() for char in cleaned)
    if letters < 3:
        return False

    return letters / len(cleaned) >= 0.5


def extract(text, barcode=""):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    data = {key: "" for key in FIELDS}

    # Extra metadata initialized
    data["barcode"] = barcode or ""
    data["gs1_digital_link"] = ""
    data["is_gs1"] = "False"
    data["image_url"] = ""
    data["api_source"] = ""

    # 1. GS1 Digital Link Parsing
    gs1_info = parse_gs1_digital_link(barcode)
    lookup_barcode = barcode

    if gs1_info.get("is_gs1"):
        data["is_gs1"] = "True"
        data["gs1_digital_link"] = barcode
        if gs1_info.get("gtin"):
            data["barcode"] = gs1_info["gtin"]
            lookup_barcode = gs1_info["gtin"]
        if gs1_info.get("batch_number"):
            data["batch_number"] = gs1_info["batch_number"]
        if gs1_info.get("expiry_date"):
            data["expiry_date"] = gs1_info["expiry_date"]
        if gs1_info.get("manufacturing_date"):
            data["manufacturing_date"] = gs1_info["manufacturing_date"]

    # 2. Product Information API Lookup (Open Food Facts / Fallback Registry)
    if lookup_barcode:
        api_prod = fetch_product_by_barcode(lookup_barcode)
        if api_prod.get("product_found"):
            data["product_name"] = api_prod.get("product_name") or data["product_name"]
            data["manufacturer_name"] = api_prod.get("brand") or data["manufacturer_name"]
            data["country_of_origin"] = api_prod.get("country_of_origin") or data["country_of_origin"]
            if not data["net_quantity"]:
                data["net_quantity"] = api_prod.get("net_quantity") or ""
            data["image_url"] = api_prod.get("image_url") or ""
            data["api_source"] = api_prod.get("api_source") or ""
            if api_prod.get("ingredients") and not data["product_description"]:
                data["product_description"] = f"Ingredients: {api_prod['ingredients']}"

    # 3. Label Text Extraction

    # Manufacturer / Brand Name
    if not data["manufacturer_name"]:
        mfg_by = first(r"(?:Mfd\.\s*by|Manufactured\s+by|Mfg\.\s*by)\s*[:\-]?\s*([^\n]+)", text)
        marketed_by = first(r"(?:Marketed\s+by|Marketed\s+By)\s*[:\-]?\s*([^\n]+)", text)
        data["manufacturer_name"] = mfg_by or marketed_by

    # Manufacturer Address
    if not data["manufacturer_address"]:
        mfg_addr = first(r"(?:Address|Addr\.)\s*[:\-]?\s*([^\n]+)", text)
        data["manufacturer_address"] = mfg_addr

    # Customer Care Details
    if not data["customer_care"]:
        customer_mob = first(r"(\+?91[\s-]?\d{10}|\b[789]\d{9}\b)", text)
        customer_email = first(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
        care_parts = []
        if customer_mob:
            care_parts.append(customer_mob)
        if customer_email:
            care_parts.append(customer_email)
        if care_parts:
            data["customer_care"] = " | ".join(care_parts)
        else:
            data["customer_care"] = first(r"(?:Customer\s*care|Consumer\s*care)[^\n]{0,60}?(\+?\d[\d\s-]{7,}\d)", text)

    # MRP (Price)
    if not data["mrp"]:
        mrp_found = first(r"(?:M\.?R\.?P\.?|MRP)\s*(?:Rs\.?|₹|INR)?\s*(?:\([^)]*\))?\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([0-9]{1,5}(?:\.\d{1,2})?)", text)
        if not mrp_found:
            mrp_found = first(r"(?:Rs\.?|₹)\s*([0-9]{1,5}(?:\.\d{2})?)", text)
        data["mrp"] = mrp_found

    # Net Quantity & Unit
    if not data["net_quantity"]:
        net_qty = first(r"(?:Net\s*(?:Content|Qty|Quantity|Wt|Weight|Vol|Volume)\s*[:\-]?\s*)?(\d+(?:\.\d+)?\s*(?:ml|l|L|g|kg|pcs|FL\.?OZ))", text)
        data["net_quantity"] = net_qty

    if not data["unit_of_measurement"]:
        unit_found = first(r"\d+(?:\.\d+)?\s*(kg|g|mg|ml|l|L|pcs)", text)
        data["unit_of_measurement"] = unit_found

    # Batch Number
    if not data["batch_number"]:
        batch_found = first(r"(?:Batch\s*No\.?|Batch\s*No|Batch|Lot\s*No\.?|Lot)\s*[:\-]?\s*([A-Za-z0-9\-/]{3,15})", text)
        if batch_found and batch_found != "/":
            data["batch_number"] = batch_found

    # Manufacturing Date (MFG)
    if not data["manufacturing_date"]:
        mfd_found = first(r"(?:Mfd\.?|Mfg\.?|Manufacturing|MFD|Packed|Pkg)(?:\s*Dt\.?|\s*Date)?\s*[:\-]?\s*(\d{1,2}[\/\.-]\d{2,4})", text)
        data["manufacturing_date"] = mfd_found

    # Expiry Date
    if not data["expiry_date"]:
        exp_found = first(r"(?:Exp\.?\s*Dt\.?|Expiry|Exp(?:iry)?|Best\s*Before|Use\s*By)\s*[:\-]?\s*(\d{1,2}[\/\.-]\d{2,4})", text)
        data["expiry_date"] = exp_found

    # Fallback date search
    dates = re.findall(r"\b(\d{1,2}[\/\.-]\d{2,4})\b", text)
    if not data["manufacturing_date"] and dates:
        data["manufacturing_date"] = dates[0]
    if not data["expiry_date"] and len(dates) > 1:
        data["expiry_date"] = dates[1]

    # Country of Origin
    if not data["country_of_origin"]:
        origin_found = first(r"(?:MADE\s+IN|Country\s+of\s+Origin\s*[:\-]?)\s*([A-Za-z ]+)", text)
        if origin_found:
            data["country_of_origin"] = origin_found.strip()

    # Product Name / Brand Name
    if not data["product_name"]:
        brand_found = first(r'"([^"]+)"\s*Brand', text)
        if brand_found:
            data["product_name"] = brand_found.title()
        else:
            for line in lines:
                if is_valid_product_name(line):
                    data["product_name"] = line
                    break

    return data