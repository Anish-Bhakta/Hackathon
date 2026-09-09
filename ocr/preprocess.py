import cv2
import numpy as np


def sharpen_image(gray):
    """Sharpen gray image to make fine text & numbers crisp."""
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(gray, -1, kernel)


def preprocess_clahe(gray):
    """Apply Contrast Limited Adaptive Histogram Equalization for low-contrast text."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def preprocess(path):
    """
    Primary preprocessor. Reads an image, resizes if small, sharpens,
    enhances contrast, and returns an Otsu-thresholded binary image.
    """
    img = cv2.imread(path)
    if img is None:
        raise ValueError("The uploaded image is corrupt or unreadable.")
    
    h, w = img.shape[:2]
    if max(h, w) < 1800:
        scale = 1800 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = preprocess_clahe(gray)
    gray = sharpen_image(gray)
    
    # Bilateral blur removes background noise while preserving sharp text edges
    denoised = cv2.bilateralFilter(gray, 7, 75, 75)
    return cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def get_ocr_image_variants(path):
    """
    Generates multiple preprocessed image variants specifically optimized
    for extracting text from dark packaging, white text boxes, metallic prints,
    dot-matrix printed dates/batch codes, and vertically rotated text.
    """
    img = cv2.imread(path)
    if img is None:
        return []

    h, w = img.shape[:2]
    # Ensure high resolution (at least 2200px on long edge)
    scale = max(1.0, 2200.0 / max(h, w))
    img_scaled = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    sh, sw = img_scaled.shape[:2]

    gray = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2GRAY)
    
    # Kernel definitions
    kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    kernel_dot = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))

    # Variant 1: Original Grayscale sharpened
    gray_sharp = sharpen_image(gray)

    # Variant 2: CLAHE Contrast Enhanced
    clahe_img = preprocess_clahe(gray)
    clahe_sharp = sharpen_image(clahe_img)

    # Variant 3: Dot Matrix Closing & Dilation (Bridges inkjet dots into continuous text)
    closed = cv2.morphologyEx(clahe_sharp, cv2.MORPH_CLOSE, kernel_dot)
    dilated_dot = cv2.dilate(closed, kernel_dilate, iterations=1)
    denoised = cv2.bilateralFilter(dilated_dot, 7, 75, 75)
    otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Variant 4: Inverted Otsu Thresholding (White text on dark/black packaging)
    inverted_otsu = cv2.bitwise_not(otsu)

    # Variant 5: Adaptive Gaussian Thresholding (Handles uneven lighting, glare & dot matrix)
    adaptive = cv2.adaptiveThreshold(
        clahe_sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )

    # Variant 6: Morphological Top-Hat (extracts small bright text on dark background)
    kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_tophat)
    tophat_thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    variants = []

    # 1. Morphological White/Light Box Container Detection (MRP, Batch, Mfg & Expiry table)
    _, thresh_light = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    kernel_merge = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    closed_light = cv2.morphologyEx(thresh_light, cv2.MORPH_CLOSE, kernel_merge)
    contours, _ = cv2.findContours(closed_light, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for idx, c in enumerate(contours):
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area > (sw * sh * 0.03) and bw > int(sw * 0.25) and bh > int(sh * 0.15):
            box_crop = gray[max(0, y-10):min(sh, y+bh+10), max(0, x-10):min(sw, x+bw+10)]
            box_3x = cv2.resize(box_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            box_clahe = preprocess_clahe(box_3x)
            box_sharp = sharpen_image(box_clahe)
            box_adaptive = cv2.adaptiveThreshold(
                box_sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
            )
            variants.append((f"white_box_adaptive_{idx}", box_adaptive))
            variants.append((f"white_box_sharp_{idx}", box_sharp))

    # 2. Quadrant Crops & 90/270 Degree Rotated Variants for Inkjet & Rotated Side Text
    # Bottom-Right Quadrant (where date/batch/MRP are usually printed)
    br_crop = gray[int(sh * 0.25):sh, int(sw * 0.30):sw]
    if br_crop.size > 0:
        br_large = cv2.resize(br_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        br_clahe = preprocess_clahe(br_large)
        br_sharp = sharpen_image(br_clahe)
        br_adaptive = cv2.adaptiveThreshold(
            br_sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )
        br_dilated = cv2.dilate(br_sharp, kernel_dilate, iterations=1)

        variants.append(("br_sharp", br_sharp))
        variants.append(("br_adaptive", br_adaptive))
        variants.append(("br_dilated", br_dilated))

        # ROTATED VARIANTS for vertical inkjet text printed at 90° or 270°
        br_rot90 = cv2.rotate(br_sharp, cv2.ROTATE_90_CLOCKWISE)
        br_rot270 = cv2.rotate(br_sharp, cv2.ROTATE_90_COUNTERCLOCKWISE)
        br_dilated_rot90 = cv2.rotate(br_dilated, cv2.ROTATE_90_CLOCKWISE)
        br_dilated_rot270 = cv2.rotate(br_dilated, cv2.ROTATE_90_COUNTERCLOCKWISE)

        variants.append(("br_rot90", br_rot90))
        variants.append(("br_rot270", br_rot270))
        variants.append(("br_dilated_rot90", br_dilated_rot90))
        variants.append(("br_dilated_rot270", br_dilated_rot270))

    # Right-Side Half Crop for vertical side-margin prints
    right_crop = gray[0:sh, int(sw * 0.40):sw]
    if right_crop.size > 0:
        right_large = cv2.resize(right_crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        right_sharp = sharpen_image(preprocess_clahe(right_large))
        variants.append(("right_rot90", cv2.rotate(right_sharp, cv2.ROTATE_90_CLOCKWISE)))
        variants.append(("right_rot270", cv2.rotate(right_sharp, cv2.ROTATE_90_COUNTERCLOCKWISE)))

    # 3. Full-Image Variants
    variants.extend([
        ("gray_sharp", gray_sharp),
        ("clahe_sharp", clahe_sharp),
        ("adaptive", adaptive),
        ("otsu", otsu),
        ("dilated_dot", dilated_dot),
        ("inverted_otsu", inverted_otsu),
        ("tophat", tophat_thresh),
        ("full_rot90", cv2.rotate(gray_sharp, cv2.ROTATE_90_CLOCKWISE)),
        ("full_rot270", cv2.rotate(gray_sharp, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ])

    return variants




