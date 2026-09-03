"""
GS1 Digital Link Parser Module
Decodes GS1 Digital Link URIs, 2D QR codes, and GS1 Element Strings (Sunrise 2027 standard).
Extracts GTIN (01), Batch/Lot (10), Expiration Date (17), Mfg Date (11), and Serial Number (21).
"""

import re
from datetime import datetime


def parse_yymmdd(yymmdd_str):
    """Convert YYMMDD date string to YYYY-MM-DD format."""
    if not yymmdd_str or len(yymmdd_str) != 6 or not yymmdd_str.isdigit():
        return yymmdd_str

    try:
        yy = int(yymmdd_str[0:2])
        mm = int(yymmdd_str[2:4])
        dd = int(yymmdd_str[4:6])

        # Standard GS1 century rule: YY < 50 => 20YY, else 19YY
        year = 2000 + yy if yy < 70 else 1900 + yy
        
        # Handle day 00 (end of month indicator in GS1)
        if dd == 0:
            dd = 28 # fallback to valid day

        dt = datetime(year, max(1, min(12, mm)), max(1, min(31, dd)))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return yymmdd_str


def parse_gs1_digital_link(input_str):
    """
    Parses a GS1 Digital Link URL, GS1 QR code string, or GS1 Element String.
    Returns a dictionary of extracted GS1 Application Identifiers (AIs).
    """
    if not input_str or not isinstance(input_str, str):
        return {"is_gs1": False}

    input_str = input_str.strip()
    result = {
        "is_gs1": False,
        "gtin": "",
        "batch_number": "",
        "expiry_date": "",
        "manufacturing_date": "",
        "serial_number": "",
        "raw_input": input_str,
        "ai_map": {},
    }

    # Pattern 1: Standard GS1 URI path structure e.g., /01/09506000134376/10/BATCH123/17/261231
    if "/01/" in input_str or input_str.startswith("http://") or input_str.startswith("https://"):
        result["is_gs1"] = True

        # Extract path-based AIs
        # Regex matches pairs like /01/12345678901234 or /10/LOT123 or /17/261231
        path_matches = re.findall(r"/(\d{2,4})/([^/?#]+)", input_str)
        for ai, val in path_matches:
            result["ai_map"][ai] = val

        # Also extract query parameters if GS1 AIs are passed as query args (e.g. ?10=LOT123&17=261231)
        if "?" in input_str:
            query_part = input_str.split("?", 1)[1].split("#", 1)[0]
            for param in query_part.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    if k.isdigit():
                        result["ai_map"][k] = v

    # Pattern 2: GS1 Parentheses format e.g. (01)08901030300000(10)LOT123(17)261231
    elif "(" in input_str and ")" in input_str:
        matches = re.findall(r"\((\d{2,4})\)([^\(\)]+)", input_str)
        if matches:
            result["is_gs1"] = True
            for ai, val in matches:
                result["ai_map"][ai] = val

    # Pattern 3: Plain GTIN check (if input is 12, 13, or 14 digits)
    elif input_str.isdigit() and len(input_str) in (8, 12, 13, 14):
        result["is_gs1"] = True
        result["gtin"] = input_str.zfill(14)
        result["ai_map"]["01"] = result["gtin"]
        return result

    if not result["is_gs1"] and not result["ai_map"]:
        return result

    # Map standard AIs to target fields
    ai_map = result["ai_map"]

    # 01 = GTIN
    if "01" in ai_map:
        result["gtin"] = ai_map["01"].strip()

    # 10 = Batch / Lot Number
    if "10" in ai_map:
        result["batch_number"] = ai_map["10"].strip()

    # 17 = Expiration Date (YYMMDD)
    if "17" in ai_map:
        result["expiry_date"] = parse_yymmdd(ai_map["17"].strip())

    # 11 = Manufacturing Date (YYMMDD)
    if "11" in ai_map:
        result["manufacturing_date"] = parse_yymmdd(ai_map["11"].strip())

    # 21 = Serial Number
    if "21" in ai_map:
        result["serial_number"] = ai_map["21"].strip()

    return result
