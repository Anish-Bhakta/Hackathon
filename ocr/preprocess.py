import cv2
def preprocess(path):
    img=cv2.imread(path)
    if img is None: raise ValueError("The uploaded image is corrupt or unreadable.")
    h,w=img.shape[:2]
    if max(h,w)<1500:
        scale=1500/max(h,w); img=cv2.resize(img,None,fx=scale,fy=scale)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    gray=cv2.GaussianBlur(gray,(3,3),0)
    return cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
