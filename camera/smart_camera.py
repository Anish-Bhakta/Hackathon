import cv2
import os
import uuid

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except Exception:
    HAS_PYZBAR = False


def find_smart_connect_camera():
    """Find an available camera index for Smart Connect or external webcam."""
    for index in range(10):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Camera found at index: {index}")
            cap.release()
            return index
        cap.release()

    raise RuntimeError(
        "No external or mobile camera found. Please make sure your phone camera is connected via Smart Connect, DroidCam, or USB."
    )


def scan_with_phone_camera():
    """
    Open Smart Connect / Mobile phone camera.
    Detect barcodes automatically using PyZbar and OpenCV.
    When a barcode is detected, save captured frame and proceed.
    """
    camera_index = find_smart_connect_camera()
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        raise RuntimeError("Could not open Smart Connect mobile camera.")

    barcode_detector = cv2.barcode.BarcodeDetector()
    qr_detector = cv2.QRCodeDetector()

    print()
    print("==================================================")
    print(" Smart Connect / Mobile Camera Scanner Started")
    print(" Point your phone camera at the product barcode")
    print(" Press 'Q' or 'ESC' to cancel")
    print("==================================================")
    print()

    detected_code = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.release()
            cv2.destroyAllWindows()
            raise RuntimeError("Could not read frame from mobile camera.")

        # 1. Try PyZbar
        if HAS_PYZBAR:
            try:
                decoded_objects = pyzbar.decode(frame)
                for obj in decoded_objects:
                    code_str = obj.data.decode("utf-8", errors="ignore").strip()
                    if code_str:
                        detected_code = code_str
                        # Draw bounding rectangle
                        (x, y, w, h) = obj.rect
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                        break
            except Exception:
                pass

        # 2. Try OpenCV barcode / QR detector if PyZbar did not capture
        if not detected_code:
            try:
                # QR check
                val, _, _ = qr_detector.detectAndDecode(frame)
                if val and val.strip():
                    detected_code = val.strip()

                # Barcode check
                if not detected_code:
                    res = barcode_detector.detectAndDecode(frame)
                    if isinstance(res, tuple) and res[0]:
                        decoded = res[0]
                        if isinstance(decoded, (list, tuple)):
                            decoded = decoded[0] if decoded else ""
                        if decoded:
                            detected_code = str(decoded).strip()
            except Exception:
                pass

        if detected_code:
            print("Barcode Detected:", detected_code)
            cv2.putText(
                frame,
                f"Barcode: {detected_code}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                3
            )

            filename = f"camera_{uuid.uuid4().hex}.jpg"
            upload_folder = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "static",
                "uploads"
            )
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            cv2.imwrite(image_path, frame)

            cap.release()
            cv2.destroyAllWindows()
            return image_path, detected_code

        # Display camera feed window
        cv2.imshow("LabelGuard - Smart Connect Phone Camera Scanner", frame)

        # Press Q or ESC to exit
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    raise RuntimeError("Mobile camera scanning cancelled.")