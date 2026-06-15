from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
import datetime

class PDFService:
    def __init__(self, output_dir='static/reports'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_report(self, user_data, risk_score, model_used, filename=None, explanation=None):
        if filename is None:
            filename = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Background Header
        c.setFillColor(colors.HexColor("#6366f1"))
        c.rect(0, height - 100, width, 100, fill=1)
        
        # Header Text
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 60, "Medical Analysis Report")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, f"Quantum-Classical Hybrid System | Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Patient & Device Info Section
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 140, "Assessment Summary")
        c.line(50, height - 145, 200, height - 145)

        # Risk Score with Color Indicator
        risk_color = "#10b981" # Emerald
        risk_text = "LOW RISK"
        if risk_score > 70:
            risk_color = "#ef4444" # Red
            risk_text = "HIGH RISK"
        elif risk_score > 30:
            risk_color = "#f59e0b" # Amber
            risk_text = "MODERATE RISK"
            
        c.setFillColor(colors.HexColor(risk_color))
        c.rect(width - 250, height - 200, 200, 60, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width - 150, height - 175, f"{risk_score:.1f}%")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width - 150, height - 192, risk_text)

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 11)
        curr_y = height - 170
        c.drawString(50, curr_y, f"Primary Model: {model_used}")
        curr_y -= 20
        c.drawString(50, curr_y, "Status: Analysis Complete")

        # Feature Analysis Table
        curr_y -= 60
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, curr_y, "Clinical Parameter Analysis")
        c.line(50, curr_y - 5, 250, curr_y - 5)
        curr_y -= 30
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(70, curr_y, "PARAMETER")
        c.drawString(250, curr_y, "VALUE")
        c.line(50, curr_y - 5, width - 50, curr_y - 5)
        curr_y -= 20
        c.setFont("Helvetica", 10)
        
        for key, val in user_data.items():
            if curr_y < 100:
                c.showPage()
                curr_y = height - 50
            c.drawString(70, curr_y, str(key))
            c.drawString(250, curr_y, str(val))
            curr_y -= 20

        # AI Reasoning (LIME) Section
        if explanation and curr_y > 150:
            curr_y -= 30
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, curr_y, "AI Reasoning (LIME Analysis)")
            c.line(50, curr_y - 5, 250, curr_y - 5)
            curr_y -= 25
            
            c.setFont("Helvetica", 10)
            sorted_exp = sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)
            for feature, weight in sorted_exp[:3]: # Show top 3 factors
                impact = "Increases Risk" if weight > 0 else "Decreases Risk"
                color = colors.red if weight > 0 else colors.green
                
                c.setFillColor(colors.black)
                c.drawString(70, curr_y, f"• {feature}:")
                c.setFillColor(color)
                c.drawString(200, curr_y, impact)
                curr_y -= 20

        # Footer / Disclaimer
        c.setFillColor(colors.lightgrey)
        c.rect(0, 0, width, 60, fill=1)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, 40, "Disclaimer: This is an AI-generated assessment based on Quantum-Classical Hybrid Analysis.")
        c.drawCentredString(width/2, 30, "This is not a clinical diagnosis. Please consult a qualified doctor for medical advice.")

        c.save()
        return filename, filepath

if __name__ == "__main__":
    pdf = PDFService()
    pdf.generate_report({'BMI': 25, 'Age': 45}, 45.5, "Quantum-VQC")
    print("Sample PDF generated.")
