from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
import os
import easyocr
import tempfile

load_dotenv()

# -----------------------------
# Flask setup
# -----------------------------
app = Flask(__name__)
CORS(app)

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "healveda-frontend")

# -----------------------------
# Gemini setup
# -----------------------------
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# -----------------------------
# OCR setup
# -----------------------------
ocr_reader = easyocr.Reader(['en'], gpu=False)

# -----------------------------
# FRONTEND ROUTES
# -----------------------------
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/safety")
def safety():
    return send_from_directory(FRONTEND_DIR, "safety.html")

@app.route("/about")
def about():
    return send_from_directory(FRONTEND_DIR, "about.html")

@app.route("/login")
def login():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/herbal-plan")
def herbal_plan():
    return send_from_directory(FRONTEND_DIR, "herbal-plan.html")

@app.route("/lifestyle")
def lifestyle():
    return send_from_directory(FRONTEND_DIR, "lifestyle.html")

@app.route("/scanner")
def scanner():
    return send_from_directory(FRONTEND_DIR, "scanner.html")

@app.route("/chatbot")
def chatbot():
    return send_from_directory(FRONTEND_DIR, "chatbot.html")

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

# -----------------------------
# MEDICINE KNOWLEDGE (LIMITED)
# -----------------------------
TIMING_RULES = {
    "levothyroxine": "Take in the morning on an empty stomach",
    "thyroxine": "Take in the morning on an empty stomach",
    "thyronorm": "Take in the morning on an empty stomach",
    "eltroxin": "Take in the morning on an empty stomach",
    "pantoprazole": "Take before breakfast",
    "paracetamol": "Take after food if needed",
    "metformin": "Take with meals",
    "amlodipine": "Take at the same time daily"
}

# -----------------------------
# MEDICINE SCANNER (FIXED)
# -----------------------------
@app.route("/scan-medicines", methods=["POST"])
def scan_medicines():
    try:
        extracted_text = ""

        # OCR
        if "image" in request.files:
            image = request.files["image"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                ocr_text = " ".join(ocr_reader.readtext(tmp.name, detail=0))
                extracted_text = ocr_text.lower()

        print("📄 OCR TEXT:", extracted_text)

        # -----------------------------
        # Detect medicine-like names
        # -----------------------------
        medicines = set()
        words = extracted_text.replace(",", " ").replace(")", " ").split()

        for i, word in enumerate(words):
            if word in ["tab", "tablet", "cap", "capsule"] and i + 1 < len(words):
                name = words[i + 1]
                if name.isalpha() and len(name) > 3:
                    medicines.add(name.capitalize())

        medicines = list(medicines)

        # -----------------------------
        # Timing advice
        # -----------------------------
        timing = []
        for med in medicines:
            key = med.lower()
            if key in TIMING_RULES:
                timing.append({
                    "medicine": med,
                    "advice": TIMING_RULES[key]
                })
            else:
                timing.append({
                    "medicine": med,
                    "advice": "Follow doctor's instructions (timing not clearly specified)"
                })

        # -----------------------------
        # Fallback (never fail)
        # -----------------------------
        if not medicines:
            return jsonify({
                "medicines": [],
                "timingAdvice": [],
                "riskScore": 50,
                "riskLevel": "Unknown",
                "alerts": [
                    "Medicine name could not be clearly identified.",
                    "Please upload a clearer image or type the medicine name manually."
                ],
                "aiExplanation": (
                    "The prescription text was unclear. "
                    "This can happen due to handwriting, image quality, or brand names."
                )
            })

        # -----------------------------
        # AI explanation
        # -----------------------------
        prompt = f"""
Explain the following medicines in very simple language for a common person:

{", ".join(medicines)}

Rules:
- No diagnosis
- No dosage
- Simple explanation only
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        ai_text = "Explanation unavailable."
        if response and response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                ai_text = parts[0].text

        return jsonify({
            "medicines": medicines,
            "timingAdvice": timing,
            "riskScore": 80,
            "riskLevel": "Informational",
            "alerts": ["Always follow your doctor's instructions."],
            "aiExplanation": ai_text
        })

    except Exception as e:
        print("🔥 SCANNER ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/ping")
def ping():
    return "Heal Veda backend running ✅"

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
