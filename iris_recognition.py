import cv2
import numpy as np
import base64

def decode_image(base64_string):

    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    image_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

def preprocess_image(image):

    height, width = image.shape[:2]
    target_width = 320
    scale = target_width / width
    dim = (target_width, int(height * scale))
    resized_img = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    
    gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)
    
    equalized = cv2.equalizeHist(gray)
    
    return equalized

def extract_features(image, return_annotated=False):

    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    eyes = eye_cascade.detectMultiScale(gray, 1.3, 5)
    
    annotated_img = image.copy()

    for (ex, ey, ew, eh) in eyes:

        cv2.rectangle(annotated_img, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
    
    preprocessed = preprocess_image(image)
    
    orb = cv2.ORB_create(nfeatures=500)
    
    keypoints, descriptors = orb.detectAndCompute(preprocessed, None)
    
    if return_annotated:
        _, buffer = cv2.imencode('.jpg', annotated_img)
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')
        return descriptors, annotated_base64
    
    return descriptors

def verify_user(captured_features, stored_users, threshold=0.75):

    if captured_features is None or len(captured_features) == 0:
        return None, 0
    
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    best_match_user = None
    max_matches = 0
    
    for user_dict in stored_users:
        stored_features = user_dict['features']
        if stored_features is None or len(stored_features) == 0:
            continue
            
        try:
            matches = bf.match(captured_features, stored_features)
            matches = sorted(matches, key=lambda x: x.distance)
            
            good_matches = [m for m in matches if m.distance < 50]
            count = len(good_matches)
            
            if count > max_matches:
                max_matches = count
                best_match_user = user_dict
        except cv2.error:
            continue

    if max_matches >= 30: 
        return best_match_user, max_matches
        
    return None, max_matches