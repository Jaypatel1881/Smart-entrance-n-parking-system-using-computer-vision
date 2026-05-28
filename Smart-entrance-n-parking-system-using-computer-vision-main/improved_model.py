# improved_model.py
import os
import cv2
import torch
import numpy as np
import torchvision.transforms as T
import easyocr
import re
from collections import defaultdict

class CustomPlateNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.features = torch.nn.Sequential(
            torch.nn.Conv2d(3, 32, 3, padding=1), torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),
            torch.nn.Conv2d(32, 64, 3, padding=1), torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),
            torch.nn.Conv2d(64, 128, 3, padding=1), torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),
        )
        self.fc = torch.nn.Sequential(
            torch.nn.Flatten(),
            torch.nn.Linear(128*32*32, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 4)
        )

    def forward(self, x):
        return self.fc(self.features(x))

class ImprovedPlateDetectorOCR:
    def __init__(self, model_path="custom_plate_model.pth", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = T.Compose([T.ToTensor()])
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
        self.model = None
        
        # Valid Indian state codes
        self.valid_states = {
            'AN', 'AP', 'AR', 'AS', 'BR', 'CH', 'CG', 'DD', 'DL', 'DN',
            'GA', 'GJ', 'HP', 'HR', 'JH', 'JK', 'KA', 'KL', 'LA', 'LD',
            'MH', 'ML', 'MN', 'MP', 'MZ', 'NL', 'OD', 'OR', 'PB', 'PY',
            'RJ', 'SK', 'TN', 'TR', 'TS', 'UK', 'UP', 'WB'
        }
        
        if os.path.exists(model_path):
            try:
                self.model = CustomPlateNet().to(self.device)
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                print("[model] Loaded custom_plate_model.pth")
            except Exception as e:
                print("[model] Failed loading custom model:", e)
                self.model = None
        else:
            print("[model] Using enhanced heuristic-based detection")

    def detect_yellow_white_regions(self, image):
        """Detect yellow and white plate regions using color segmentation"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Yellow plate mask (commercial vehicles)
        lower_yellow = np.array([18, 70, 100])
        upper_yellow = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # White plate mask (private vehicles)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 35, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Combine masks
        plate_mask = cv2.bitwise_or(yellow_mask, white_mask)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_CLOSE, kernel)
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_OPEN, kernel)
        
        return plate_mask

    def find_plate_candidates(self, image):
        """Find all potential plate regions using multiple methods"""
        h, w = image.shape[:2]
        candidates = []
        
        # Method 1: Color-based detection
        color_mask = self.detect_yellow_white_regions(image)
        contours1, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours1:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            aspect_ratio = w_box / float(h_box) if h_box > 0 else 0
            
            if (2.0 < aspect_ratio < 6.0 and 
                w_box > 80 and h_box > 20 and
                w_box < w * 0.9 and h_box < h * 0.4):
                
                candidates.append({
                    'bbox': (x, y, x + w_box, y + h_box),
                    'method': 'color',
                    'confidence': 0.8,
                    'area': w_box * h_box
                })
        
        # Method 2: Edge-based detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 200)
        
        # Dilate edges to connect characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        contours2, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours2 = sorted(contours2, key=cv2.contourArea, reverse=True)[:30]
        
        for contour in contours2:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            aspect_ratio = w_box / float(h_box) if h_box > 0 else 0
            area = cv2.contourArea(contour)
            bbox_area = w_box * h_box
            extent = area / bbox_area if bbox_area > 0 else 0
            
            if (2.0 < aspect_ratio < 6.0 and 
                w_box > 80 and h_box > 20 and
                w_box < w * 0.9 and h_box < h * 0.4 and
                extent > 0.5):
                
                candidates.append({
                    'bbox': (x, y, x + w_box, y + h_box),
                    'method': 'edge',
                    'confidence': 0.6,
                    'area': w_box * h_box
                })
        
        # Method 3: Morphological operations
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5)))
        _, thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        contours3, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours3:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            aspect_ratio = w_box / float(h_box) if h_box > 0 else 0
            
            if (2.0 < aspect_ratio < 6.0 and 
                w_box > 80 and h_box > 20 and
                w_box < w * 0.9 and h_box < h * 0.4):
                
                candidates.append({
                    'bbox': (x, y, x + w_box, y + h_box),
                    'method': 'morph',
                    'confidence': 0.7,
                    'area': w_box * h_box
                })
        
        return candidates

    def merge_overlapping_boxes(self, candidates):
        """Merge overlapping bounding boxes"""
        if not candidates:
            return []
        
        # Sort by area (largest first)
        candidates.sort(key=lambda x: x['area'], reverse=True)
        
        merged = []
        used = set()
        
        for i, cand1 in enumerate(candidates):
            if i in used:
                continue
            
            x1, y1, x2, y2 = cand1['bbox']
            overlapping = [cand1]
            
            for j, cand2 in enumerate(candidates[i+1:], start=i+1):
                if j in used:
                    continue
                
                ox1, oy1, ox2, oy2 = cand2['bbox']
                
                # Check overlap
                if not (x2 < ox1 or ox2 < x1 or y2 < oy1 or oy2 < y1):
                    overlap_area = max(0, min(x2, ox2) - max(x1, ox1)) * max(0, min(y2, oy2) - max(y1, oy1))
                    area1 = (x2 - x1) * (y2 - y1)
                    area2 = (ox2 - ox1) * (oy2 - oy1)
                    
                    # If overlap is significant
                    if overlap_area > 0.5 * min(area1, area2):
                        overlapping.append(cand2)
                        used.add(j)
            
            # Merge all overlapping boxes
            all_x1 = min([c['bbox'][0] for c in overlapping])
            all_y1 = min([c['bbox'][1] for c in overlapping])
            all_x2 = max([c['bbox'][2] for c in overlapping])
            all_y2 = max([c['bbox'][3] for c in overlapping])
            
            avg_conf = sum([c['confidence'] for c in overlapping]) / len(overlapping)
            
            merged.append({
                'bbox': (all_x1, all_y1, all_x2, all_y2),
                'confidence': avg_conf * (1 + len(overlapping) * 0.1),  # Boost confidence for merged
                'area': (all_x2 - all_x1) * (all_y2 - all_y1)
            })
            
            used.add(i)
        
        return merged

    def detect_plate_bbox(self, image):
        """Main detection method combining multiple approaches"""
        h, w = image.shape[:2]
        
        if self.model is not None:
            # Use custom model if available
            inp = cv2.resize(image, (256, 256))
            t = self.transform(inp).unsqueeze(0).to(self.device)
            with torch.no_grad():
                out = self.model(t).cpu().numpy()[0]
            
            x1 = int(max(0, out[0]) * w)
            y1 = int(max(0, out[1]) * h)
            x2 = int(min(1, out[2]) * w)
            y2 = int(min(1, out[3]) * h)
            
            if x2 - x1 > 50 and y2 - y1 > 15:
                return [(x1, y1, x2, y2)]
        
        # Find all candidates using multiple methods
        candidates = self.find_plate_candidates(image)
        
        if not candidates:
            return []
        
        # Merge overlapping boxes
        merged = self.merge_overlapping_boxes(candidates)
        
        # Sort by confidence and return top candidates
        merged.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top 5 candidates for OCR testing
        return [c['bbox'] for c in merged[:5]]

    def fix_ocr_errors(self, text, position):
        """Fix OCR errors based on character position in plate"""
        if not text:
            return text
        
        char = text.upper()
        
        # Position 0-1: Must be letters (state code)
        if position in [0, 1]:
            if char.isdigit():
                digit_to_letter = {'0': 'O', '1': 'I', '2': 'Z', '3': 'E', 
                                  '4': 'A', '5': 'S', '6': 'G', '8': 'B', '9': 'P'}
                return digit_to_letter.get(char, char)
        
        # Position 2-3: Must be digits (district code)
        elif position in [2, 3]:
            if char.isalpha():
                letter_to_digit = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 
                                  'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8'}
                return letter_to_digit.get(char, char)
        
        # Position 4-5: Can be letters (vehicle series)
        elif position in [4, 5]:
            if char.isdigit():
                digit_to_letter = {'0': 'O', '1': 'I', '2': 'Z', '3': 'E', 
                                  '5': 'S', '6': 'G', '8': 'B'}
                return digit_to_letter.get(char, char)
        
        # Position 6+: Must be digits (registration number)
        else:
            if char.isalpha():
                letter_to_digit = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 
                                  'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8'}
                return letter_to_digit.get(char, char)
        
        return char

    def clean_plate_text(self, text):
        """Clean and validate plate text"""
        # Remove all non-alphanumeric
        text = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        # Remove brand names (aggressive)
        brands = [
            'MARUTI', 'MARUTISUZUKI', 'SUZUKI', 'HYUNDAI', 'HONDA', 'TATA', 
            'MAHINDRA', 'FORD', 'TOYOTA', 'KIA', 'MG', 'NISSAN', 'RENAULT',
            'VOLKSWAGEN', 'SKODA', 'FIAT', 'CHEVROLET', 'DATSUN', 'JEEP',
            'CIAZ', 'SWIFT', 'BALENO', 'DZIRE', 'CRETA', 'VENUE', 'CITY',
            'JAZZ', 'AMAZE', 'NEXON', 'HARRIER', 'SAFARI', 'PUNCH', 'ALTROZ',
            'SELTOS', 'SONET', 'HECTOR', 'ASTOR', 'INNOVA', 'FORTUNER',
            'IND', 'INDIA', 'BHARAT', 'BH', 'SERIES'
        ]
        
        for brand in sorted(brands, key=len, reverse=True):
            text = text.replace(brand, '')
        
        # Try to find valid plate pattern
        patterns = [
            r'([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{4})',
            r'([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{3})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                state_code = match[0]
                if state_code in self.valid_states:
                    # Found valid pattern
                    plate = ''.join(match)
                    # Apply position-based fixes
                    fixed = ''
                    for i, char in enumerate(plate):
                        fixed += self.fix_ocr_errors(char, i)
                    return fixed
        
        # If no pattern found, try to construct from text
        if len(text) >= 8:
            # Apply position-based fixing
            fixed = ''
            for i, char in enumerate(text[:10]):  # Max 10 chars
                fixed += self.fix_ocr_errors(char, i)
            
            # Check if fixed version matches pattern
            for pattern in patterns:
                match = re.match(pattern, fixed)
                if match and match.group(1) in self.valid_states:
                    return ''.join(match.groups())
        
        return ""

    def preprocess_crop_for_ocr(self, crop):
        """Preprocess crop with multiple methods"""
        methods = []
        
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Resize if too small
        h, w = gray.shape
        if h < 50:
            scale = 50 / h
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Method 1: Simple threshold
        _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(thresh1)
        
        # Method 2: Adaptive threshold
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
        methods.append(adaptive)
        
        # Method 3: CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, thresh2 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(thresh2)
        
        # Method 4: Inverted
        _, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        methods.append(inv)
        
        # Method 5: Original grayscale
        methods.append(gray)
        
        return methods

    def ocr_plate(self, image, box):
        """Run OCR on detected plate region"""
        x1, y1, x2, y2 = box
        
        # Add small padding
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(image.shape[1], x2 + pad)
        y2 = min(image.shape[0], y2 + pad)
        
        crop = image[y1:y2, x1:x2]
        
        if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 30:
            return ""
        
        # Get multiple preprocessed versions
        preprocessed = self.preprocess_crop_for_ocr(crop)
        
        all_texts = []
        
        for prep in preprocessed:
            try:
                results = self.reader.readtext(
                    prep,
                    detail=1,
                    paragraph=False,
                    batch_size=1,
                    workers=0
                )
                
                for bbox, text, conf in results:
                    if conf > 0.1:  # Very lenient threshold
                        all_texts.append((text, conf))
            except:
                continue
        
        if not all_texts:
            return ""
        
        # Try cleaning each detected text
        valid_plates = []
        
        for text, conf in all_texts:
            cleaned = self.clean_plate_text(text)
            if cleaned:
                valid_plates.append((cleaned, conf))
        
        # Try combining texts
        if not valid_plates and len(all_texts) > 1:
            combined = ''.join([t for t, c in all_texts])
            cleaned = self.clean_plate_text(combined)
            if cleaned:
                valid_plates.append((cleaned, 1.0))
        
        if not valid_plates:
            return ""
        
        # Return highest confidence valid plate
        valid_plates.sort(key=lambda x: x[1], reverse=True)
        return valid_plates[0][0]

    def detect_and_ocr(self, image):
        """Main pipeline: detect plates and run OCR"""
        boxes = self.detect_plate_bbox(image)
        
        if not boxes:
            print("[DEBUG] No plate candidates found")
            return []
        
        print(f"[DEBUG] Found {len(boxes)} plate candidates")
        
        results = []
        
        for idx, box in enumerate(boxes):
            print(f"[DEBUG] Testing candidate {idx+1}: {box}")
            text = self.ocr_plate(image, box)
            
            if text:
                print(f"[DEBUG] Candidate {idx+1} yielded: {text}")
                results.append((box, text))
            else:
                print(f"[DEBUG] Candidate {idx+1} failed OCR")
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for box, text in results:
            if text not in seen:
                seen.add(text)
                unique_results.append((box, text))
        
        return unique_results

    def visualize_detection(self, image, results):
        """Helper function to visualize detections"""
        img_copy = image.copy()
        
        for box, text in results:
            x1, y1, x2, y2 = box
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_copy, text, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        return img_copy