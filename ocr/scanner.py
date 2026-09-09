import re
import cv2
import pytesseract
from .preprocess import preprocess, get_ocr_image_variants
from config import Config

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except Exception:
    HAS_PYZBAR = False


def auto_orient_image(image):
    """Detect text orientation and rotate image upright if rotated."""
    if image is None:
        return image
    try:
        osd = pytesseract.image_to_osd(image)
        rotate_match = re.search(r"Rotate:\s*(\d+)", osd)
        if rotate_match:
            angle = int(rotate_match.group(1))
            if angle == 90:
                return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                return cv2.rotate(image, cv2.ROTATE_180)
            elif angle == 270:
                return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception:
        pass
    return image


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

        for img_variant in [
            image,
            cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(image, cv2.ROTATE_180),
            cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
        ]:
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


def filter_camera_watermarks(line):
    """Filter out mobile device camera watermarks like '2 Sept 2026 4:42 pm' or 'motorola edge'."""
    if re.search(
        r"(?:motorola|shot on|edge \d+|redmi|realme|iphone|samsung|galaxy|\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\s+\d{1,2}:\d{2})",
        line,
        re.I,
    ):
        return True
    return False


def scan_image(path):
    if Config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

    barcode = detect_barcode(path)

    # 1. Image loading & Auto Orientation
    image = cv2.imread(path)
    if image is not None:
        image = auto_orient_image(image)

    variants = get_ocr_image_variants(path)
    if not variants and image is not None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variants = [("default_gray", gray)]

    ocr_pass_texts = []
    seen_lines = set()
    dedup_lines = []

    # 2. Multi-pass Tesseract OCR over image variants & PSM modes
    psm_modes = ["--psm 6", "--psm 3", "--psm 11", "--psm 4"]

    for name, target_img in variants:
        # Avoid running all 4 PSMs on every grid ROI to keep scanning fast
        current_psms = ["--psm 6", "--psm 11"] if "roi" in name or "br_" in name else psm_modes
        for psm in current_psms:
            try:
                text = pytesseract.image_to_string(target_img, lang="eng", config=f"{psm} --oem 3")
                if text and len(text.strip()) > 5:
                    ocr_pass_texts.append(text.strip())
                    for raw_line in text.splitlines():
                        line = raw_line.strip()
                        if len(line) >= 2 and not filter_camera_watermarks(line):
                            normalized = re.sub(r"\s+", " ", line.lower())
                            if normalized not in seen_lines:
                                seen_lines.add(normalized)
                                dedup_lines.append(line)
            except Exception:
                pass

    raw_ocr = ocr_pass_texts[0] if ocr_pass_texts else ""
    combined_ocr = "\n".join(dedup_lines) if dedup_lines else "\n\n".join(ocr_pass_texts)

    clean = re.sub(r"[ \t]+", " ", combined_ocr)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

    # Fallback GTIN extraction if barcode graphics were unreadable
    if not barcode and clean:
        digit_matches = re.findall(r"\b\d{8,14}\b", clean)
        if digit_matches:
            barcode = digit_matches[0]

    if not clean and not barcode:
        raise RuntimeError(
            "No readable barcode or label text was detected in the uploaded image. Please ensure the image is clear or enter the barcode manually."
        )

    return raw_ocr, clean, barcode