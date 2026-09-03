import re
import cv2
import pytesseract
from .preprocess import preprocess
from config import Config

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except Exception:
    HAS_PYZBAR = False


def detect_barcode(path):
    """Detect and decode 1D barcodes and 2D QR codes using PyZbar and OpenCV multi-pass."""
    image = cv2.imread(path)
    if image is None:
        return ""

    # 1. Try PyZbar (Gold standard for EAN13, UPCA, CODE128, QR)
    if HAS_PYZBAR:
        try:
            # Check original image
            decoded_objects = pyzbar.decode(image)
            for obj in decoded_objects:
                code_str = obj.data.decode("utf-8", errors="ignore").strip()
                if code_str:
                    return code_str

            # Try grayscale + threshold
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            decoded_objects = pyzbar.decode(gray)
            for obj in decoded_objects:
                code_str = obj.data.decode("utf-8", errors="ignore").strip()
                if code_str:
                    return code_str
        except Exception:
            pass

    # 2. Try OpenCV QR Code & Barcode Detectors across rotations
    try:
        qr_detector = cv2.QRCodeDetector()
        barcode_detector = cv2.barcode.BarcodeDetector()

        for img_variant in [image, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(image, cv2.ROTATE_180)]:
            # QR check
            val, _, _ = qr_detector.detectAndDecode(img_variant)
            if val and val.strip():
                return val.strip()

            # Barcode check
            result = barcode_detector.detectAndDecode(img_variant)
            if isinstance(result, tuple):
                decoded = result[0]
                if isinstance(decoded, (list, tuple)):
                    decoded = decoded[0] if decoded else ""
                if decoded:
                    return str(decoded).strip()
    except Exception:
        pass

    return ""


def scan_image(path):
    if Config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

    # Barcode & QR Code detection
    barcode = detect_barcode(path)

    # OCR detection
    text = ""
    try:
        text = pytesseract.image_to_string(
            preprocess(path),
            lang="eng",
            config="--psm 6"
        )
    except Exception:
        pass

    clean = re.sub(r"[ \t]+", " ", text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

    # If PyZbar/OpenCV missed barcode, try finding standalone 8-14 digit GTIN/UPC in OCR text
    if not barcode and clean:
        digit_matches = re.findall(r"\b\d{8,14}\b", clean)
        if digit_matches:
            barcode = digit_matches[0]

    # Allow scan to continue if either barcode OR OCR text was detected
    if not clean and not barcode:
        raise RuntimeError(
            "No readable barcode or label text was detected in the uploaded image. Please ensure the image is clear or enter the barcode manually."
        )

    return text, clean, barcode
