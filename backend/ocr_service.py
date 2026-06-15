try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception as e:
    import traceback
    EASYOCR_AVAILABLE = False
    print(f"WARNING: EasyOCR/Torch unavailable. OCR feature disabled. Error: {e}")
    traceback.print_exc()

import re
import os
import google.generativeai as genai

class OCRService:
    def __init__(self, api_key=None):
        self.reader = None
        self.api_key = api_key
        if api_key:
            # Using gemini-2.5-flash which is the current state-of-the-art in this repo environment
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None

    def _get_reader(self):
        if not EASYOCR_AVAILABLE:
            return None
        if self.reader is None:
            print("Loading OCR Model (EasyOCR)...")
            self.reader = easyocr.Reader(['en'], gpu=False)
        return self.reader

    def generate_summary(self, full_text, image_path=None, language='English'):
        if not self.model:
            return "Analysis unavailable. Gemini API not configured.", "Unknown", [], "Unknown"

        # If OCR text is missing or indicates failure, try Multimodal analysis
        is_ocr_failed = not full_text or "OCR unavailable" in full_text
        
        if is_ocr_failed and image_path and os.path.exists(image_path):
            print(f"Local OCR failed or unavailable. Using Gemini Multimodal Vision fallback for {image_path}...")
            return self._generate_multimodal_summary(image_path, language=language)

        lang_note = f"IMPORTANT: Respond entirely in {language}." if language != 'English' else ""
        prompt = (
            f"{lang_note} "
            "Analyze the following medical report text extracted via OCR. Your job is to extract ANY disease findings or health risks. "
            "1. provide a clear 3-4 sentence clinical summary of the findings in simple terms. "
            "2. Identify the specific disease or medical condition mentioned. "
            "3. Suggest 2-3 potential medications or follow-up steps. "
            "4. Determine the patient's risk level based on the findings: 'Low', 'Moderate', or 'High'. "
            "Format ONLY as a VALID JSON object (no extra text) with keys: 'summary', 'primary_disease', 'medicines' (list), 'risk_level'."
            f"\n\nReport Text: {full_text}"
        )

        try:
            response = self.model.generate_content(prompt)
            return self._parse_gemini_json(response.text)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                return "The AI Intelligence engine is cooling down (Rate Limit). Please wait 60 seconds and try again.", "Quota Exceeded", [], "Unknown"
            return f"Error analyzing report: {error_msg}", "Analysis Error", [], "Unknown"

    def _generate_multimodal_summary(self, image_path, language='English'):
        try:
            # Upload file to Gemini or send as bytes (bytes is usually simpler for small images)
            import PIL.Image
            img = PIL.Image.open(image_path)
            lang_note = f"IMPORTANT: Respond entirely in {language}." if language != 'English' else ""
            prompt = (
                f"{lang_note} "
                "You are an expert medical diagnostic assistant. Your task is to analyze ANY healthcare or clinical lab report image provided. "
                "1. Provide a clear 3-4 sentence clinical summary of the findings in simple terms. "
                "2. Identify the specific primary disease, medical condition, or health risk mentioned in the report. "
                "3. Suggest 2-3 potential medications, lifestyle changes, or clinical follow-up steps. "
                "4. Categorize the patient's immediate health risk based on the clinical biomarkers and findings: 'Low', 'Moderate', or 'High'. "
                "Format ONLY as a VALID JSON object (no extra text) with keys: 'summary', 'primary_disease', 'medicines' (list), 'risk_level'."
            )
            
            import time
            # Retry up to 3 times with backoff for quota limits
            for attempt in range(3):
                try:
                    response = self.model.generate_content([prompt, img])
                    return self._parse_gemini_json(response.text)
                except Exception as e:
                    error_msg = str(e)
                    if ("429" in error_msg or "quota" in error_msg.lower()) and attempt < 2:
                        print(f"Vision API Quota hit, retrying in {2 ** attempt}s...")
                        time.sleep(2 ** attempt)
                        continue
                    if "429" in error_msg or "quota" in error_msg.lower():
                        return "The Vision Intelligence engine is cooling down (Quota Exceeded). Please wait a moment and try again.", "Quota Exceeded", [], "Unknown"
                    return f"Vision Analysis Error: {error_msg}", "Analysis Error", [], "High"
        except Exception as e:
            return f"System Error: {str(e)}", "System Error", [], "Unknown"

    def _parse_gemini_json(self, text):
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                import json
                analysis = json.loads(json_match.group(0))
                return analysis.get('summary'), analysis.get('primary_disease'), analysis.get('medicines', []), analysis.get('risk_level', 'Unknown')
            return text, "Complex Findings", [], "High"
        except Exception:
            return text, "Parsing Error", [], "Unknown"

    def extract_features(self, image_path):
        reader = self._get_reader()
        if reader is None:
            return {}, "OCR unavailable (EasyOCR/Torch not installed correctly)."
        
        try:
            results = reader.readtext(image_path)
            full_text = " ".join([res[1] for res in results])
            print(f"OCR Extracted Text: {full_text}")

            # Basic RegEx for dashboard auto-fill (Phase 2 compatibility)
            patterns = {
                'Glucose': r'(?:Glucose|Sugar|HbA1c)[:\s]+(\d+\.?\d*)',
                'BloodPressure': r'(?:BP|Blood Pressure)[:\s]+(?:(\d+)/?(\d+)?)',
                'BMI': r'(?:BMI|Body Mass Index)[:\s]+(\d+\.?\d*)',
                'Age': r'(?:Age|Yrs)[:\s]+(\d+)'
            }
            
            extracted = {}
            for feature, pattern in patterns.items():
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    extracted[feature] = match.group(1)
                else:
                    extracted[feature] = None
                    
            return extracted, full_text
        except Exception as e:
            print(f"EXTRACT ERROR: {e}")
            return {}, f"OCR error: {str(e)}"

if __name__ == "__main__":
    ocr = OCRService()
    print("OCR Service initialized.")
