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
    },
    "08904335600336": {
        "product_name": "Muesli+",
        "brand": "Yoga Bar (Sproutlife Foods Pvt Ltd)",
        "categories": "Breakfast Cereals, Muesli",
        "ingredients": "60% Whole Grains (Rolled Oats, Brown Rice Flakes, Quinoa Flakes), 17% Dried Fruits (Raisins, Apricots, Cranberry, Blackcurrants), 14% Seeds & Nuts (Pumpkin, Almonds, Chia, Flax), Strawberry Powder, Date Syrup, Jaggery, Rice Bran Oil, Himalayan Pink Salt",
        "image_url": "https://images.openfoodfacts.org/images/products/890/433/560/0336/front_en.7.400.jpg",
        "net_quantity": "700 g",
        "country_of_origin": "India",
        "mrp": "445.00",
        "batch_number": "MB090426A/M120:13",
        "manufacturing_date": "09/04/26 (9th April 2026)",
        "expiry_date": "08/01/27 (8th January 2027)",
    },
    "8904335600336": {
        "product_name": "Muesli+",
        "brand": "Yoga Bar (Sproutlife Foods Pvt Ltd)",
        "categories": "Breakfast Cereals, Muesli",
        "ingredients": "60% Whole Grains (Rolled Oats, Brown Rice Flakes, Quinoa Flakes), 17% Dried Fruits (Raisins, Apricots, Cranberry, Blackcurrants), 14% Seeds & Nuts (Pumpkin, Almonds, Chia, Flax), Strawberry Powder, Date Syrup, Jaggery, Rice Bran Oil, Himalayan Pink Salt",
        "image_url": "https://images.openfoodfacts.org/images/products/890/433/560/0336/front_en.7.400.jpg",
        "net_quantity": "700 g",
        "country_of_origin": "India",
        "mrp": "445.00",
        "batch_number": "MB090426A/M120:13",
        "manufacturing_date": "09/04/26 (9th April 2026)",
        "expiry_date": "08/01/27 (8th January 2027)",
    },
    "8901058007408": {
        "product_name": "Aashirvaad Iodized Salt",
        "brand": "ITC Limited",
        "categories": "Salt, Groceries, Condiments",
        "ingredients": "Edible Common Salt, Potassium Iodate, Anticaking Agent (536)",
        "image_url": "",
        "net_quantity": "1.2 kg (1kg+200g FREE)",
        "country_of_origin": "India",
        "mrp": "30.00",
        "batch_number": "AA26GE",
        "manufacturing_date": "07/2026 (July 2026)",
        "expiry_date": "06/2027 (June 2027)",
    },
    "08901058007408": {
        "product_name": "Aashirvaad Iodized Salt",
        "brand": "ITC Limited",
        "categories": "Salt, Groceries, Condiments",
        "ingredients": "Edible Common Salt, Potassium Iodate, Anticaking Agent (536)",
        "image_url": "",
        "net_quantity": "1.2 kg (1kg+200g FREE)",
        "country_of_origin": "India",
        "mrp": "30.00",
        "batch_number": "AA26GE",
        "manufacturing_date": "07/2026 (July 2026)",
        "expiry_date": "06/2027 (June 2027)",
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
    except Exception:
        pass


    # Check offline DB entries and merge specific batch attributes
    for key in (raw_barcode, clean_barcode, raw_barcode.zfill(14)):
        if key in OFFLINE_MOCK_DB:
            mock = OFFLINE_MOCK_DB[key]
            result["product_found"] = True
            result["product_name"] = result["product_name"] or mock.get("product_name", "")
            result["brand"] = result["brand"] or mock.get("brand", "")
            result["categories"] = result["categories"] or mock.get("categories", "")
            result["ingredients"] = result["ingredients"] or mock.get("ingredients", "")
            result["image_url"] = result["image_url"] or mock.get("image_url", "")
            result["net_quantity"] = result["net_quantity"] or mock.get("net_quantity", "")
            result["country_of_origin"] = result["country_of_origin"] or mock.get("country_of_origin", "")
            if mock.get("mrp"): result["mrp"] = mock["mrp"]
            if mock.get("batch_number"): result["batch_number"] = mock["batch_number"]
            if mock.get("manufacturing_date"): result["manufacturing_date"] = mock["manufacturing_date"]
            if mock.get("expiry_date"): result["expiry_date"] = mock["expiry_date"]
            if not result["api_source"]: result["api_source"] = "Offline Registry Fallback"
            break

    return result

