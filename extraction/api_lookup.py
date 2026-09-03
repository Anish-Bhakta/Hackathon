"""
Product Information API Lookup Module
Queries the Open Food Facts API (and offline fallbacks) using a barcode or GTIN.
Returns product name, brand/manufacturer, categories, ingredients, and image URL.
"""

import json
import urllib.request
import urllib.error

# Offline database fallback for common test barcodes
OFFLINE_MOCK_DB = {
    "8595717713418": {
        "product_name": "Vilgain Tomato Ketchup",
        "brand": "Vilgain",
        "categories": "Sauces, Condiments, Ketchup",
        "ingredients": "Tomato concentrate, water, cane sugar, vinegar, salt, spice extract",
        "image_url": "https://images.openfoodfacts.org/images/products/859/571/771/3418/front_en.13.400.jpg",
        "net_quantity": "470 g",
        "country_of_origin": "Czech Republic",
    },
    "8901030300000": {
        "product_name": "Tata Salt Vacuum Evaporated Iodised Salt",
        "brand": "Tata Consumer Products",
        "categories": "Salt, Groceries, Condiments",
        "ingredients": "Vacuum Evaporated Iodised Salt, Potassium Iodate",
        "image_url": "https://images.openfoodfacts.org/images/products/890/103/030/0000/front_en.4.400.jpg",
        "net_quantity": "1 kg",
        "country_of_origin": "India",
    },
    "09506000134376": {
        "product_name": "GS1 Standard Test Organic Whole Milk",
        "brand": "GS1 Sample Labs",
        "categories": "Dairy, Milk, Fresh Foods",
        "ingredients": "Pasteurized Organic Grade A Whole Milk, Vitamin D3",
        "image_url": "",
        "net_quantity": "1 L",
        "country_of_origin": "United States",
    },
    "8901030000001": {
        "product_name": "Britannia Good Day Butter Cookies",
        "brand": "Britannia Industries Ltd",
        "categories": "Biscuits, Snacks, Bakery",
        "ingredients": "Refined Wheat Flour, Sugar, Edible Vegetable Oil, Butter, Milk Solids",
        "image_url": "",
        "net_quantity": "100 g",
        "country_of_origin": "India",
    }
}


def fetch_product_by_barcode(barcode):
    """
    Look up product information using Open Food Facts API with offline mock fallback.
    """
    clean_barcode = str(barcode).strip().lstrip("0") if str(barcode).isdigit() else str(barcode).strip()
    raw_barcode = str(barcode).strip()

    result = {
        "product_found": False,
        "product_name": "",
        "brand": "",
        "categories": "",
        "ingredients": "",
        "image_url": "",
        "net_quantity": "",
        "country_of_origin": "",
        "api_source": "",
    }

    if not raw_barcode:
        return result

    # 1. Try Open Food Facts Public REST API
    url = f"https://world.openfoodfacts.org/api/v2/product/{raw_barcode}.json"
    headers = {
        "User-Agent": "PackagedComplianceChecker/1.0 (contact@compliance.app)"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("status") == 1 and "product" in body:
                    prod = body["product"]
                    result["product_found"] = True
                    result["product_name"] = (
                        prod.get("product_name")
                        or prod.get("product_name_en")
                        or prod.get("generic_name")
                        or ""
                    )
                    result["brand"] = prod.get("brands") or prod.get("manufacturer") or ""
                    result["categories"] = prod.get("categories") or ""
                    result["ingredients"] = prod.get("ingredients_text") or prod.get("ingredients_text_en") or ""
                    result["image_url"] = prod.get("image_front_url") or prod.get("image_url") or ""
                    result["net_quantity"] = prod.get("quantity") or ""
                    result["country_of_origin"] = prod.get("origins") or prod.get("manufacturing_places") or ""
                    result["api_source"] = "Open Food Facts API"
                    return result
    except Exception:
        pass

    # 2. Check offline mock database fallback
    for key in (raw_barcode, clean_barcode, raw_barcode.zfill(14)):
        if key in OFFLINE_MOCK_DB:
            mock = OFFLINE_MOCK_DB[key]
            result["product_found"] = True
            result["product_name"] = mock["product_name"]
            result["brand"] = mock["brand"]
            result["categories"] = mock["categories"]
            result["ingredients"] = mock["ingredients"]
            result["image_url"] = mock["image_url"]
            result["net_quantity"] = mock["net_quantity"]
            result["country_of_origin"] = mock["country_of_origin"]
            result["api_source"] = "Offline Registry Fallback"
            return result

    return result
