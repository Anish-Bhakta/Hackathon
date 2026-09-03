import cv2
import requests


def detect_barcode(frame):
    """
    Kept for backward compatibility with camera/__init__.py and
    smart_camera.py. Detects and decodes a barcode directly from
    an in-memory frame (as opposed to decode_barcode_from_path,
    which loads from disk).
    """
    detector = cv2.barcode.BarcodeDetector()

    try:
        result = detector.detectAndDecode(frame)

        if len(result) == 4:
            retval, decoded_info, points, straight_code = result

            if decoded_info:
                for value in decoded_info:
                    if value:
                        return value

    except Exception as e:
        print("Barcode error:", e)

    return None


def locate_barcode(image):
    """
    Detect barcode location in the image and return a cropped
    region around it, even if there's extra background/text.
    Falls back to the full image if localization fails.
    """
    detector = cv2.barcode.BarcodeDetector()

    ok, points = detector.detect(image)

    if not ok or points is None:
        return image  # fall back to scanning the whole frame

    # points shape: (num_barcodes, 4, 2) -> take the first barcode found
    pts = points[0]

    x_coords = pts[:, 0]
    y_coords = pts[:, 1]

    x1, x2 = int(max(min(x_coords) - 20, 0)), int(max(x_coords) + 20)
    y1, y2 = int(max(min(y_coords) - 20, 0)), int(max(y_coords) + 20)

    cropped = image[y1:y2, x1:x2]

    if cropped.size == 0:
        return image

    return cropped


def decode_barcode_from_path(path):
    """
    Load an image (upload or camera capture), isolate the barcode
    region if extra background is present, and decode it.
    Returns the barcode string, or "" if nothing found.
    """
    image = cv2.imread(path)

    if image is None:
        return ""

    detector = cv2.barcode.BarcodeDetector()

    # First try decoding the full image directly
    ok, decoded_info, points, _ = detector.detectAndDecode(image)

    if decoded_info:
        for value in decoded_info:
            if value:
                return value.strip()

    # If that failed, isolate the barcode region and retry
    cropped = locate_barcode(image)

    ok, decoded_info, points, _ = detector.detectAndDecode(cropped)

    if decoded_info:
        for value in decoded_info:
            if value:
                return value.strip()

    return ""


def lookup_product(barcode_value):
    """
    Look up product details for a scanned barcode using
    the Open Food Facts API (free, no key required).
    Swap this for a paid/Indian-specific barcode DB later
    if you need better coverage for local packaged goods.
    """
    if not barcode_value:
        return None

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode_value}.json"

    try:
        resp = requests.get(url, timeout=6)
        data = resp.json()
    except Exception as e:
        print("Barcode lookup failed:", e)
        return None

    if data.get("status") != 1:
        return None

    product = data.get("product", {})

    return {
        "barcode": barcode_value,
        "product_name": product.get("product_name", ""),
        "manufacturer_name": product.get("brands", ""),
        "net_quantity": product.get("quantity", ""),
        "country_of_origin": product.get("countries", ""),
        "image_url": product.get("image_url", ""),
    }