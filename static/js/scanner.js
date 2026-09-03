/**
 * Barcode & Product Label Scanner Front-End Script
 * Captures camera snapshot frame on scan to extract Barcode + Label Text (MFG, Price, Expiry, Net Qty).
 */

let html5QrcodeScanner = null;
let currentCameraId = null;

function populateCameraDevices() {
  Html5Qrcode.getCameras().then(devices => {
    const select = document.getElementById("camera-select");
    if (!select) return;

    if (devices && devices.length) {
      select.innerHTML = "";
      devices.forEach((device, index) => {
        const option = document.createElement("option");
        option.value = device.id;

        let label = device.label || `Camera ${index + 1}`;
        if (label.toLowerCase().includes("smart") || label.toLowerCase().includes("connect") || label.toLowerCase().includes("phone") || label.toLowerCase().includes("droid")) {
          label = `📱 ${label} (External / Phone)`;
        } else {
          label = `📷 ${label}`;
        }
        option.text = label;
        select.appendChild(option);
      });

      select.classList.remove("d-none");

      if (!currentCameraId) {
        currentCameraId = devices[0].id;
      }
      select.value = currentCameraId;

      select.onchange = (e) => {
        currentCameraId = e.target.value;
        restartCameraWithId(currentCameraId);
      };
    }
  }).catch(err => {
    console.warn("Could not enumerate camera devices:", err);
  });
}

function initWebScanner() {
  const readerElement = document.getElementById("reader");
  if (!readerElement) return;

  if (html5QrcodeScanner) return;

  populateCameraDevices();

  html5QrcodeScanner = new Html5Qrcode("reader");
  const config = { fps: 10, qrbox: { width: 260, height: 260 }, aspectRatio: 1.0 };

  const cameraConstraint = currentCameraId ? currentCameraId : { facingMode: "environment" };

  html5QrcodeScanner.start(
    cameraConstraint,
    config,
    onScanSuccess,
    onScanFailure
  ).catch(err => {
    console.warn("Camera start failed:", err);
    const feedback = document.getElementById("camera-status");
    if (feedback) {
      feedback.innerHTML = `<div class="alert alert-warning py-2 small mb-0"><i class="bi bi-camera-video-off me-1"></i> Camera access unavailable. Please select camera above or upload a label photo.</div>`;
    }
  });
}

function restartCameraWithId(deviceId) {
  if (html5QrcodeScanner) {
    html5QrcodeScanner.stop().then(() => {
      html5QrcodeScanner.clear();
      html5QrcodeScanner = null;
      currentCameraId = deviceId;
      initWebScanner();
    }).catch(() => {
      html5QrcodeScanner = null;
      currentCameraId = deviceId;
      initWebScanner();
    });
  } else {
    currentCameraId = deviceId;
    initWebScanner();
  }
}

function stopWebScanner() {
  if (html5QrcodeScanner) {
    html5QrcodeScanner.stop().then(() => {
      html5QrcodeScanner.clear();
      html5QrcodeScanner = null;
    }).catch(err => console.error("Error stopping scanner:", err));
  }
}

function captureCameraSnapshot() {
  try {
    const video = document.querySelector("#reader video");
    if (!video) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.92);
  } catch (e) {
    return null;
  }
}

function onScanSuccess(decodedText) {
  console.log(`Barcode scanned: ${decodedText}`);

  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.15);
  } catch (e) {}

  // Capture current video frame for OCR text extraction (MFG, Price, Expiry, Net Qty)
  const snapshotData = captureCameraSnapshot();
  if (snapshotData) {
    const base64Input = document.getElementById("camera_image_base64");
    if (base64Input) base64Input.value = snapshotData;
  }

  const input = document.getElementById("barcode_input");
  if (input) input.value = decodedText;

  const feedback = document.getElementById("camera-status");
  if (feedback) {
    feedback.innerHTML = `<div class="alert alert-success py-2 mb-0"><i class="bi bi-check-circle me-1"></i> Barcode & Label Scanned: <strong>${decodedText}</strong>. Extracting price, mfg & expiry dates...</div>`;
  }

  stopWebScanner();
  const form = document.getElementById("scanForm");
  if (form) setTimeout(() => form.submit(), 450);
}

function onScanFailure() {}

function fillSampleBarcode(code) {
  const input = document.getElementById("barcode_input");
  if (input) input.value = code;
  const directInput = document.getElementById("direct_code");
  if (directInput) directInput.value = code;
}

function scanUploadedFile(file) {
  if (!file) return;

  const html5QrCode = new Html5Qrcode("reader");
  html5QrCode.scanFile(file, true)
    .then(decodedText => {
      console.log("Client-side image scan success:", decodedText);
      const input = document.getElementById("barcode_input");
      if (input) input.value = decodedText;

      const uploadStatus = document.getElementById("upload-status");
      if (uploadStatus) {
        uploadStatus.innerHTML = `<div class="alert alert-success py-2 mt-2 mb-0"><i class="bi bi-check-circle me-1"></i> Barcode detected in image: <strong>${decodedText}</strong></div>`;
      }
    })
    .catch(err => {
      console.log("Client-side scan did not find barcode, backend will run OCR & PyZbar:", err);
    });
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("image");
  const previewImg = document.getElementById("preview");
  const dropZone = document.getElementById("drop");

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        scanUploadedFile(file);
        if (previewImg) {
          const reader = new FileReader();
          reader.onload = (evt) => {
            previewImg.src = evt.target.result;
            previewImg.classList.remove("d-none");
          };
          reader.readAsDataURL(file);
        }
      }
    });
  }

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        const file = e.dataTransfer.files[0];
        scanUploadedFile(file);
        if (previewImg) {
          const reader = new FileReader();
          reader.onload = (evt) => {
            previewImg.src = evt.target.result;
            previewImg.classList.remove("d-none");
          };
          reader.readAsDataURL(file);
        }
      }
    });
  }
});
