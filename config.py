import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY","dev-change-me")
    DEBUG=os.getenv("FLASK_DEBUG","False").lower()=="true"
    DB_HOST=os.getenv("DB_HOST","localhost"); DB_USER=os.getenv("DB_USER","root")
    DB_PASSWORD=os.getenv("DB_PASSWORD",""); DB_NAME=os.getenv("DB_NAME","packaged_compliance")
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH",5242880))
    TESSERACT_CMD=os.getenv("TESSERACT_CMD","")
    UPLOAD_FOLDER="static/uploads"; REPORT_FOLDER="generated_reports"
