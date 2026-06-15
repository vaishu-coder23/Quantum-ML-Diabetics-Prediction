from PIL import Image, ImageDraw, ImageFont
import os

def create_dummy_report(output_path='frontend/static/uploads/dummy_report.png'):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Text results
    text = """
    LABORATORY TEST REPORT
    Patient: John Doe
    
    Glucose: 120
    BMI: 28.5
    Age: 45
    Blood Pressure: 130/85
    """
    
    # We'll just draw the text
    d.text((10, 10), text, fill=(0, 0, 0))
    img.save(output_path)
    print(f"Dummy report created at {output_path}")

if __name__ == "__main__":
    create_dummy_report()
