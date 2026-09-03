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

    # 1. Try PyZbar
    if HAS_PYZBAR:
        try:
            decoded_objects = pyzbar.decode(image)
            for obj in decoded_objects:
                code_str = obj.data.decode("utf-8", errors="ignore").strip()
                if code_str:
                    return code_str

            # Grayscale check
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
            val, _, _ = qr_detector.detectAndDecode(img_variant)
            if val and val.strip():
                return val.strip()

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

    barcode = detect_barcode(path)

    # Multi-pass OCR for dark bottles, white text, and white stamp boxes
    ocr_texts = []
    
    img = cv2.imread(path)
    if img is not None:
        # Resize if small
        h, w = img.shape[:2]
        if max(h, w) < 1600:
            scale = 1600 / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Inverted image (essential for white text on dark black bottles)
        inverted = cv2.bitwise_not(gray)

        # Thresholded image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        for target_img in [gray, thresh, inverted]:
            for psm in ["--psm 3", "--psm 6", "--psm 11"]:
                try:
                    t = pytesseract.image_to_string(target_img, lang="eng", config=psm)
                    if t and len(t.strip()) > 10:
                        ocr_texts.append(t.strip())
                except Exception:
                    pass

    combined_text = "\n\n".join(ocr_texts) if ocr_texts else ""
    raw_ocr = ocr_texts[0] if ocr_texts else ""

    clean = re.sub(r"[ \t]+", " ", combined_text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

    # Fallback: Find 8-14 digit GTIN in OCR text if barcode graphic was unreadable
    if not barcode and clean:
        digit_matches = re.findall(r"\b\d{8,14}\b", clean)
        if digit_matches:
            barcode = digit_matches[0]

    if not clean and not barcode:
        raise RuntimeError(
            "No readable barcode or label text was detected in the uploaded image. Please ensure the image is clear or enter the barcode manually."
        )

    return raw_ocr, clean, barcode