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

print("Frontend folder:", FRONTEND_DIR)
print("Files:", os.listdir(FRONTEND_DIR))

# -----------------------------
# Gemini setup (STABLE)
# -----------------------------
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

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
# RULE-BASED MEDICINE LOGIC
# -----------------------------
TIMING_RULES = {
    "levothyroxine": "Take in the morning on an empty stomach",
    "pantoprazole": "Take before breakfast",
    "paracetamol": "Take after food if needed",
    "metformin": "Take with meals",
    "amlodipine": "Take at the same time daily"
}

SAFETY_RULES = [
    (["levothyroxine", "coffee"], "Avoid coffee close to Levothyroxine intake"),
    (["ashwagandha", "levothyroxine"], "This combination may increase stimulation")
]

# -----------------------------
# MEDICINE SAFETY SCANNER (OCR + RULES + AI)
# -----------------------------
@app.route("/scan-medicines", methods=["POST"])
def scan_medicines():
    try:
        manual = request.form.get("manualMedicines", "")
        prescription = request.form.get("prescriptionText", "")

        extracted_text = f"{manual} {prescription}".lower()

        # OCR
        if "image" in request.files:
            image = request.files["image"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                ocr_text = " ".join(ocr_reader.readtext(tmp.name, detail=0))
                extracted_text += " " + ocr_text.lower()

        # Detect medicines
        medicines = []
        for med in TIMING_RULES.keys():
            if med in extracted_text:
                medicines.append(med.capitalize())

        if not medicines:
            return jsonify({"error": "No known medicines detected"})

        # Timing advice
        timing = [
            {"medicine": m, "advice": TIMING_RULES[m.lower()]}
            for m in medicines
        ]

        # Risk score
        score = 100
        if len(medicines) >= 3:
            score -= 20
        if "Levothyroxine" in medicines:
            score -= 10

        risk = "Low Risk" if score >= 80 else "Moderate Risk" if score >= 60 else "High Risk"

        # Safety alerts
        alerts = []
        for combo, msg in SAFETY_RULES:
            if all(c in extracted_text for c in combo):
                alerts.append(msg)
        if not alerts:
            alerts.append("No major safety alerts detected")

        # AI explanation (education only)
        prompt = f"""
Explain the following medicines in simple wellness language:

{", ".join(medicines)}

Rules:
- No diagnosis
- No dosage
- Education only
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
            "riskScore": score,
            "riskLevel": risk,
            "alerts": alerts,
            "aiExplanation": ai_text
        })

    except Exception as e:
        print("🔥 SCANNER ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# -----------------------------
# AYURVEDA + ALLOPATHY SAFETY CHECK
# -----------------------------
def check_reaction(medicine, herb, prakriti, symptoms):
    risk = "Low"
    reasons = []

    med = medicine.lower()
    her = herb.lower()

    if "ashwagandha" in her and "thyroxine" in med:
        reasons.append("Both may increase metabolism and internal heat")
        if prakriti == "Pitta":
            risk = "High"
            reasons.append("Pitta body type is sensitive to excess heat")

    if "Anxiety" in symptoms:
        risk = "High"
        reasons.append("Stimulation may worsen anxiety")

    if not reasons:
        reasons.append("No strong imbalance pattern detected")

    return risk, reasons

@app.route("/check", methods=["POST"])
def check():
    try:
        data = request.get_json(force=True)

        medicine = data.get("medicines", "")
        herb = data.get("herbs", "")
        prakriti = data.get("prakriti", "")
        symptoms = data.get("symptoms", [])

        risk, reasons = check_reaction(medicine, herb, prakriti, symptoms)

        prompt = f"""
You are an Ayurveda–Allopathy wellness guide.

Allopathic medicine: {medicine}
Ayurvedic herb: {herb}
Body type (Prakriti): {prakriti}
Symptoms: {", ".join(symptoms)}

Observed interaction reasons:
{", ".join(reasons)}

Explain wellness impact safely.
No diagnosis. No prescriptions.
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        ai_text = "No response generated."
        if response and response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                ai_text = parts[0].text

        return jsonify({
            "risk": risk,
            "reasons": reasons,
            "response": ai_text
        })

    except Exception as e:
        print("🔥 BACKEND ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# -----------------------------
# HERBAL PLAN
# -----------------------------
@app.route("/generate-herbal-plan", methods=["POST"])
def generate_herbal_plan():
    try:
        data = request.get_json()

        prakriti = data.get("prakriti", "")
        goal = data.get("goal", "")
        lifestyle = data.get("lifestyle", "")
        medicines = data.get("medicines", "")

        prompt = f"""
You are an Ayurvedic wellness expert.

User:
Prakriti: {prakriti}
Goal: {goal}
Lifestyle: {lifestyle}
Medicines: {medicines}

Rules:
- Max 3 herbs
- No diagnosis
- No dosage
- Add lifestyle guidance
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        ai_text = "No response generated."
        if response and response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                ai_text = parts[0].text

        return jsonify({"response": ai_text})

    except Exception as e:
        print("🔥 HERBAL PLAN ERROR:", str(e))
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
