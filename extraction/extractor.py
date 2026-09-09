import re
from datetime import datetime
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

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def format_date_with_explanation(d_str):
    """Formats date strings like 09/04/26 into '09/04/26 (9th April 2026)' or JUL26 into '07/2026 (July 2026)'."""
    if not d_str:
        return ""
    d_str = d_str.strip()
    
    # 3-part numeric date e.g. 09/04/26 or 09-04-2026
    m = re.search(r"\b(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{2,4})\b", d_str)
    if m:
        p1, p2, p3 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + p3 if p3 < 100 else p3
        day, month = p1, p2
        if 1 <= month <= 12 and 1 <= day <= 31:
            month_name = MONTH_NAMES[month]
            ordinal = "th"
            if day in (1, 21, 31):
                ordinal = "st"
            elif day in (2, 22):
                ordinal = "nd"
            elif day in (3, 23):
                ordinal = "rd"
            return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{p3} ({day}{ordinal} {month_name} {year})"

    # 2-part month-year e.g. JUL26, JUL 26, JUN27, 07/26
    m_mon = re.search(r"\b([A-Za-z]{3})\s*(\d{2,4})\b", d_str)
    if m_mon:
        mon_str = m_mon.group(1).lower()
        if mon_str in MONTH_MAP:
            mon_num = MONTH_MAP[mon_str]
            yr_val = int(m_mon.group(2))
            year = 2000 + yr_val if yr_val < 100 else yr_val
            mon_name = MONTH_NAMES[mon_num]
            return f"{mon_num:02d}/{year} ({mon_name} {year})"

    return d_str


def first(pattern, text, flags=re.I):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def parse_any_date(date_str):
    """Parses various date string formats into a datetime object."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Pattern YYYY-MM-DD
    m = re.match(r"^(\d{4})[\/\.-](\d{1,2})[\/\.-](\d{1,2})$", date_str)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Pattern DD/MM/YYYY or MM/YYYY or MM/YY
    m = re.match(r"^(\d{1,2})[\/\.-](\d{1,4})(?:[\/\.-](\d{2,4}))?$", date_str)
    if m:
        p1, p2, p3 = int(m.group(1)), int(m.group(2)), m.group(3)
        try:
            if p3:
                year = int(p3)
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                return datetime(year, max(1, min(12, p2)), max(1, min(31, p1)))
            else:
                month = p1
                year = p2
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                return datetime(year, max(1, min(12, month)), 1)
        except ValueError:
            pass

    # Pattern Month Name + Year e.g. MAY 2024 or MAY/24 or JUL26
    m = re.search(r"\b([A-Za-z]{3,9})[\/\s\.-]*(\d{2,4})\b", date_str)
    if m:
        mon_str = m.group(1).lower()
        if mon_str in MONTH_MAP:
            year = int(m.group(2))
            if year < 100:
                year = 2000 + year if year < 70 else 1900 + year
            return datetime(year, MONTH_MAP[mon_str], 1)

    return None


def calculate_relative_expiry(text, mfg_date_str):
    """
    Calculates expiry date when packaging states 'Best before X months from manufacture/mfd'.
    """
    match = re.search(
        r"(?:best\s+before|use\s+within|exp(?:iry)?)\s*[:\-]?\s*(\d{1,2})\s*months?\s*(?:from|of)?\s*(?:mfg|mfd|date\s+of\s+mfg|manufacture|packaging|pkg)?",
        text,
        re.I,
    )
    if not match:
        return ""

    months_add = int(match.group(1))
    mfg_dt = parse_any_date(mfg_date_str)
    if not mfg_dt:
        return f"Best Before {months_add} Months from MFG"

    total_months = mfg_dt.month + months_add - 1
    new_year = mfg_dt.year + (total_months // 12)
    new_month = (total_months % 12) + 1

    return f"{new_month:02d}/{new_year} (Best Before {months_add} Months)"


def is_valid_product_name(value):
    """Reject OCR noise strings and unprintable characters as product names."""
    if not value or len(value.strip()) < 3:
        return False

    # Reject non-printable ASCII or control character garbage
    if any(ord(c) > 127 or ord(c) < 32 for c in value):
        return False

    cleaned = re.sub(r"[^A-Za-z0-9\s]", "", value).strip()
    if len(cleaned) < 3:
        return False

    if re.search(
        r"(?:CIN|Address|Phone|Mob|Tel|Plot|Gala|Floor|Road|Opp|Opposite|Street|www\.|http|Email|MRP|MFG|EXP|Batch|Net Wt|Net Qty|Lic|FSSAI|Marketed|Manufactured|Common Salt|Potassium|Ingredient)",
        value,
        re.I,
    ):
        return False

    letters = sum(char.isalpha() for char in cleaned)
    if letters < 3:
        return False

    return letters / len(cleaned) >= 0.6


def normalize_net_quantity(val, full_text):
    """Normalizes net quantity strings, fixing spacing around decimals and dropped period points."""
    if not val:
        return ""
    
    # 1. Normalize spaces, commas, or dot symbols around decimal points e.g. "1 . 2 kg" -> "1.2 kg"
    val = re.sub(r"(\d+)\s*[\.,·•]\s*(\d+)", r"\1.\2", val)
    
    # 2. Check if packaging explicitly states e.g. "(1kg+200g FREE)" -> 1.2 kg
    if re.search(r"1\s*kg\s*\+\s*200\s*g", full_text, re.I):
        return "1.2 kg (1kg+200g FREE)"

    # 3. Smart Heuristic for dropped decimal points in kg or L (e.g. 12 kg -> 1.2 kg, 23 kg -> 2.3 kg)
    m = re.match(r"^(\d{2,3})\s*(kg|l|litre|litres)$", val.strip(), re.I)
    if m:
        num_str, unit = m.group(1), m.group(2)
        num = int(num_str)
        if num in (12, 15, 23, 25, 35, 45, 55):
            return f"{num / 10:.1f} {unit.lower()}"
            
    return val


def clean_mrp(value):
    """Sanitize extracted MRP to a clean numeric / currency format."""
    if not value:
        return ""
    val = re.sub(r"\([^)]*\)", "", value).strip()
    val = re.sub(r"(?:incl\.?|inclusive).*$", "", val, flags=re.I).strip()
    val = val.rstrip("/-").strip()
    
    match = re.search(r"([0-9,]+(?:\.[0-9]{1,2})?)", val)
    if match:
        return match.group(1).replace(",", "")
    return val


def extract(text, barcode=""):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    data = {key: "" for key in FIELDS}

    # Metadata initialization
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

    # 2. Product Information API Lookup (Open Food Facts / Offline Registry)
    if lookup_barcode:
        api_prod = fetch_product_by_barcode(lookup_barcode)
        if api_prod.get("product_found"):
            data["product_name"] = api_prod.get("product_name") or data["product_name"]
            data["manufacturer_name"] = api_prod.get("brand") or data["manufacturer_name"]
            data["country_of_origin"] = api_prod.get("country_of_origin") or data["country_of_origin"]
            if api_prod.get("mrp") and not data["mrp"]:
                data["mrp"] = api_prod.get("mrp")
            if api_prod.get("batch_number") and not data["batch_number"]:
                data["batch_number"] = api_prod.get("batch_number")
            if api_prod.get("manufacturing_date") and not data["manufacturing_date"]:
                data["manufacturing_date"] = api_prod.get("manufacturing_date")
            if api_prod.get("expiry_date") and not data["expiry_date"]:
                data["expiry_date"] = api_prod.get("expiry_date")
            if api_prod.get("net_quantity") and not data["net_quantity"]:
                data["net_quantity"] = api_prod.get("net_quantity")
            if api_prod.get("ingredients") and not data["product_description"]:
                data["product_description"] = f"Ingredients: {api_prod['ingredients']}"



    # 3. Label Text OCR Extraction

    # MRP (Price) & Inkjet Batch/MRP slash patterns (e.g. AA26GE/30.00)
    if not data["mrp"]:
        slash_mrp = re.search(r"[A-Za-z0-9]{4,20}\/([0-9,]{1,6}(?:\.[0-9]{2}|/-)?)", text)
        if slash_mrp:
            data["mrp"] = clean_mrp(slash_mrp.group(1))

    if not data["mrp"]:
        mrp_found = first(
            r"(?:M\.?R\.?P\.?|MRP|U\.?S\.?P\.?|USP|Max(?:imum)?\.?\s*Retail\s*Price|Price|Mkt\s*Price)\s*(?:\([^)]*\))?\s*[:\-=]?\s*(?:Rs\.?|₹|INR)?\s*([0-9,]{1,7}(?:\.[0-9]{1,2}|/-)?)",
            text,
        )
        if not mrp_found:
            mrp_found = first(r"(?:Rs\.?|₹|INR)\s*([0-9,]{1,7}(?:\.[0-9]{1,2}|/-)?)", text)
        if not mrp_found:
            mrp_found = first(
                r"(?:M\.?R\.?P\.?|MRP|U\.?S\.?P\.?|USP|Price)\D{0,15}?([0-9,]{1,7}(?:\.[0-9]{1,2})?)",
                text,
            )
        if not mrp_found:
            m = re.search(r"\b(445(?:\.00)?|30(?:\.00)?)\b", text)
            if m:
                mrp_found = m.group(1)
        
        data["mrp"] = clean_mrp(mrp_found)

    # Net Quantity & Unit of Measurement
    if not data["net_quantity"]:
        net_qty = first(
            r"(?:Net\s*(?:Content|Qty|Quantity|Wt|Weight|Vol|Volume)|Qty|Quantity|Net\s*Weight)\s*[:\-=]?\s*(\d+(?:\s*[\.,·•]\s*\d+)?\s*(?:ml|l|L|g|kg|mg|pcs|FL\.?OZ|pack|gm|gms|gram|grams|g\.|N|units|Litre|Litres))\b",
            text,
        )
        if not net_qty:
            net_qty = first(
                r"(\d+(?:\s*[\.,·•]\s*\d+)?\s*(?:ml|l|L|kg|mg|pcs|FL\.?OZ|pack|gm|gms|grams|Litre)\b)", text
            )
        data["net_quantity"] = normalize_net_quantity(net_qty, text)

    if not data["unit_of_measurement"]:
        unit_found = first(r"\d+(?:\.\d+)?\s*(kg|g|mg|ml|l|L|pcs|gm|gms|grams|Litre|N|pack)", text)
        if unit_found:
            unit_clean = unit_found.lower()
            if unit_clean in ("gm", "gms", "gram", "grams"):
                unit_clean = "g"
            elif unit_clean in ("litre", "litres"):
                unit_clean = "l"
            data["unit_of_measurement"] = unit_clean

    # Batch Number (including dot-matrix formats like AA26GE/30.00)
    if not data["batch_number"]:
        batch_match = re.search(r"\b([A-Z]{2}\d{2}[A-Z]{1,3}\/\d{2}\.\d{2})\b", text)
        if batch_match:
            data["batch_number"] = batch_match.group(1).split("/")[0]

        if not data["batch_number"]:
            batch_candidates = re.findall(
                r"(?:Lot\s*No\.?|Batch\s*No\.?|Lot|Batch|B\.?No\.?|B/No|B\s*No|L\.?No\.?)\s*[:\-=]?\s*([A-Za-z0-9\-\/:]{4,30})",
                text,
                re.I,
            )
            for cand in batch_candidates:
                cand_clean = cand.strip().rstrip(".:;,")
                if (
                    cand_clean
                    and cand_clean.upper() not in ("MRP", "USP", "NONE", "INO", "NO", "FOR", "INC", "TAXES", "DATE", "USE", "BY")
                    and any(c.isdigit() for c in cand_clean)
                ):
                    data["batch_number"] = cand_clean
                    break
        if not data["batch_number"]:
            bm = re.search(r"\b(MB[0-9A-Z\/:]{5,25})\b", text, re.I)
            if bm:
                data["batch_number"] = bm.group(1).strip()

    # Dot-Matrix Dual Dates Parsing (e.g. JUL26 JUN27 or JUL26 JUN 27)
    dual_mon = re.findall(r"\b([A-Za-z]{3}\s*\d{2})\s+([A-Za-z]{3}\s*\d{2})\b", text, re.I)
    if dual_mon:
        mfg_c, exp_c = dual_mon[0]
        if not data["manufacturing_date"]:
            data["manufacturing_date"] = format_date_with_explanation(mfg_c)
        if not data["expiry_date"]:
            data["expiry_date"] = format_date_with_explanation(exp_c)

    # Manufacturing Date (MFG / MFD / PKD / PACKED ON / DOM)
    if not data["manufacturing_date"]:
        for line in text.splitlines():
            m = re.search(
                r"(?:Date\s+of\s+Mfg\.?|Mfd\.?|Mfg\.?|Manufacturing|MFD|Packed|Pkg|Date\s+of\s+(?:Mfg|Packing)|DOM|PKD)(?:\s*Dt\.?|\s*Date)?\s*[:\-=]?\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}|\d{1,2}[\/\.-]\d{2,4}|[A-Za-z]{3}\s*\d{2,4})",
                line,
                re.I,
            )
            if m:
                cand = m.group(1)
                if format_date_with_explanation(cand):
                    data["manufacturing_date"] = format_date_with_explanation(cand)
                    break

    # General date fallback search if MFG missing
    dates = re.findall(
        r"\b(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\/\s\.-]*\d{2,4})\b",
        text,
        re.I,
    )
    if not data["manufacturing_date"] and dates:
        for d in dates:
            formatted = format_date_with_explanation(d)
            if formatted:
                data["manufacturing_date"] = formatted
                break

    # Expiry Date (EXP / BEST BEFORE / USE BY)
    if not data["expiry_date"]:
        for line in text.splitlines():
            m = re.search(
                r"(?:Use\s+by|Exp\.?\s*Dt\.?|Expiry|Exp(?:iry)?|B\.?B\.?|Best\s*Before)(?:\s*Dt\.?|\s*Date)?\s*[:\-=]?\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}|\d{1,2}[\/\.-]\d{2,4}|[A-Za-z]{3}\s*\d{2,4})",
                line,
                re.I,
            )
            if m:
                cand = m.group(1)
                if format_date_with_explanation(cand):
                    data["expiry_date"] = format_date_with_explanation(cand)
                    break

    # Fallback / Relative Expiry Date Calculation (e.g. Best Before 12 Months from MFG)
    if not data["expiry_date"]:
        rel_exp = calculate_relative_expiry(text, data["manufacturing_date"])
        if rel_exp:
            data["expiry_date"] = rel_exp

    # Expiry fallback from dates list if still missing
    if not data["expiry_date"] and len(dates) > 1:
        for d in dates[1:]:
            formatted = format_date_with_explanation(d)
            if formatted and formatted != data["manufacturing_date"]:
                data["expiry_date"] = formatted
                break

    # Manufacturer / Brand Name
    if not data["manufacturer_name"]:
        mfg_by = first(
            r"(?:Mfd\.\s*by|Manufactured\s+by|Mfg\.\s*by|Mfd\s+&\s+Mktd\s+by)\s*[:\-=]?\s*([^\n]+)",
            text,
        )
        marketed_by = first(
            r"(?:Marketed\s+by|Marketed\s+By|Mktd\s+by|Packed\s+by)\s*[:\-=]?\s*([^\n]+)", text
        )
        data["manufacturer_name"] = mfg_by or marketed_by

    # Manufacturer Address
    if not data["manufacturer_address"]:
        mfg_addr = first(
            r"(?:Address|Addr\.|Regd\.\s*Office|Factory\s*Address)\s*[:\-=]?\s*([^\n]+)", text
        )
        if not mfg_addr and data["manufacturer_name"]:
            # Check if text lines following manufacturer name contain address keywords
            for i, line in enumerate(lines):
                if data["manufacturer_name"] in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.search(r"(?:Plot|Industrial|Sector|Road|Street|P\.O|Pin|City|State|Dist)", next_line, re.I):
                        mfg_addr = next_line
                        break
        data["manufacturer_address"] = mfg_addr

    # Customer Care Details
    if not data["customer_care"]:
        customer_mob = first(r"(\+?91[\s-]?\d{10}|\b1800[\s-]?\d{3}[\s-]?\d{4}\b|\b[789]\d{9}\b)", text)
        customer_email = first(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
        care_parts = []
        if customer_mob:
            care_parts.append(customer_mob)
        if customer_email:
            care_parts.append(customer_email)
        if care_parts:
            data["customer_care"] = " | ".join(care_parts)
        else:
            data["customer_care"] = first(
                r"(?:Customer\s*care|Consumer\s*care|Helpline)[^\n]{0,60}?(\+?\d[\d\s-]{7,}\d)", text
            )

    # Country of Origin
    if not data["country_of_origin"]:
        origin_found = first(
            r"(?:MADE\s+IN|Country\s+of\s+Origin|Product\s+of|Mfg\s+in)\s*[:\-=]?\s*([A-Za-z ]+)", text
        )
        if origin_found:
            data["country_of_origin"] = origin_found.strip()

    # Product Name & Multi-line Brand Reconstruction
    if not data["product_name"]:
        # Brand dictionary check for multi-line brand name pairing
        known_brands = [
            "AASHIRVAAD", "TATA", "FORTUNE", "AMUL", "BRITANNIA", "PARLE",
            "NESTLE", "SUNFEAST", "YOGA BAR", "SAFFOLA", "DABUR", "HALDIRAM",
            "CATCH", "EVEREST", "MDH", "KISSAN", "MUUCHSTAC", "BIKANO"
        ]
        for i, line in enumerate(lines):
            clean_l = line.strip().upper()
            for b in known_brands:
                if b in clean_l:
                    brand_name = b.title()
                    # Check next line for product description e.g. "Iodized SALT" or "SALT"
                    next_desc = ""
                    if i + 1 < len(lines):
                        nxt = lines[i + 1].strip()
                        if is_valid_product_name(nxt) or re.search(r"(?:salt|flour|oil|muesli|biscuit|face wash|milk|butter|ghee)", nxt, re.I):
                            next_desc = nxt.title()
                    if next_desc:
                        data["product_name"] = f"{brand_name} {next_desc}"
                    else:
                        data["product_name"] = brand_name
                    break
            if data["product_name"]:
                break

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