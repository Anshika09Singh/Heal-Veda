from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
import os
import easyocr
import tempfile

# =============================
# VECTOR DB IMPORTS
# =============================
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime

load_dotenv()

# =============================
# FLASK SETUP
# =============================
app = Flask(__name__)
CORS(app)

# =============================
# PATHS
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "healveda-frontend")

# =============================
# GEMINI SETUP
# =============================
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# =============================
# OCR SETUP
# =============================
ocr_reader = easyocr.Reader(['en'], gpu=False)

# =============================
# VECTOR DATABASE (SEMANTIC MEMORY)
# =============================
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.Client()

vector_collection = chroma_client.get_or_create_collection(
    name="healveda_semantic_memory"
)

def store_in_vector_db(text, source):
    if not text.strip():
        return

    embedding = embedding_model.encode(text).tolist()

    vector_collection.add(
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"source": source}],
        ids=[f"{source}_{datetime.now().timestamp()}"]
    )

    print(f"✅ Stored in Vector DB | Source: {source}")

# =============================
# FRONTEND ROUTES
# =============================
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

# =============================
# MEDICINE KNOWLEDGE
# =============================
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

# =============================
# MEDICINE SCANNER
# =============================
@app.route("/scan-medicines", methods=["POST"])
def scan_medicines():
    try:
        extracted_text = ""

        if "image" in request.files:
            image = request.files["image"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                extracted_text = " ".join(
                    ocr_reader.readtext(tmp.name, detail=0)
                ).lower()

        print("📄 OCR TEXT:", extracted_text)

        medicines = set()
        words = extracted_text.replace(",", " ").replace(")", " ").split()

        for i, word in enumerate(words):
            if word in ["tab", "tablet", "cap", "capsule"] and i + 1 < len(words):
                name = words[i + 1]
                if name.isalpha() and len(name) > 3:
                    medicines.add(name.capitalize())

        for key in TIMING_RULES:
            if key in extracted_text:
                medicines.add(key.capitalize())

        medicines = list(medicines)

        if not medicines:
            return jsonify({
                "medicines": [],
                "timingAdvice": [],
                "riskScore": 50,
                "riskLevel": "Unknown",
                "alerts": ["Medicine names unclear"],
                "aiExplanation": "Please upload a clearer prescription image."
            })

        timing = [{
            "medicine": m,
            "advice": TIMING_RULES.get(m.lower(), "Follow doctor's instructions")
        } for m in medicines]

        prompt = f"""
Explain the following medicines in very simple language.
No diagnosis. No dosage.

Medicines:
{", ".join(medicines)}
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        ai_text = response.candidates[0].content.parts[0].text

        store_in_vector_db(
            f"SCANNER | Medicines: {medicines} | AI: {ai_text}",
            source="scanner"
        )

        return jsonify({
            "medicines": medicines,
            "timingAdvice": timing,
            "riskScore": 80,
            "riskLevel": "Informational",
            "alerts": ["Always follow your doctor’s advice"],
            "aiExplanation": ai_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# SAFETY CHECK (SYSTEMATIC)
# =============================
@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)

    medicine = data.get("medicines", "")
    herb = data.get("herbs", "")
    prakriti = data.get("prakriti", "")
    symptoms = data.get("symptoms", [])

    prompt = f"""
You are a wellness safety assistant.
Explain everything for a common person.

User details:
- Medicine: {medicine}
- Herb: {herb}
- Body type: {prakriti}
- Symptoms: {", ".join(symptoms)}

IMPORTANT RULES:
- No diagnosis
- No dosage
- No scary words
- Simple English
- Bullet points only

FORMAT STRICTLY LIKE THIS:

SAFETY RESULT:
Risk Level: Low / Moderate / High
Meaning: One simple line

WHY THIS NEEDS ATTENTION:
• Point 1
• Point 2

WHAT YOU SHOULD DO:
• Action 1
• Action 2

WHAT TO AVOID:
• Avoid 1
• Avoid 2

FINAL ADVICE:
2 friendly reassuring lines.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(
        f"SAFETY | {medicine} + {herb} | {prakriti} | {symptoms} | {ai_text}",
        source="safety"
    )

    return jsonify({"response": ai_text})

# =============================
# HERBAL PLAN (SYSTEMATIC)
# =============================
@app.route("/generate-herbal-plan", methods=["POST"])
def generate_herbal_plan():
    data = request.get_json()

    prakriti = data.get("prakriti", "")
    goal = data.get("goal", "")
    lifestyle = data.get("lifestyle", "")
    medicines = data.get("medicines", "")

    prompt = f"""
You are a wellness assistant.
Explain everything so a normal person can understand.

User details:
- Body type: {prakriti}
- Goal: {goal}
- Lifestyle: {lifestyle}
- Current medicines: {medicines}

IMPORTANT RULES:
- No diagnosis
- No dosage
- No Ayurveda jargon
- Simple English

FORMAT STRICTLY LIKE THIS:

RECOMMENDED HERBS:
1. Herb name
• What it does:
• Why it is suggested for me:
• How to use (form only):
• Safety note:

2. Herb name
• What it does:
• Why it is suggested for me:
• How to use:
• Safety note:

DAILY LIFESTYLE GUIDANCE:
Morning:
• Point

Daytime:
• Point

Evening:
• Point

IMPORTANT SAFETY NOTE:
2 simple lines.

SHORT SUMMARY:
2 reassuring lines.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(
        f"HERBAL_PLAN | {prakriti} | {goal} | {lifestyle} | {ai_text}",
        source="herbal_plan"
    )

    return jsonify({"response": ai_text})

# =============================
# VECTOR COUNT (DEBUG)
# =============================
@app.route("/vector-count")
def vector_count():
    return jsonify({"total_vectors": vector_collection.count()})

# =============================
# HEALTH CHECK
# =============================
@app.route("/ping")
def ping():
    return "Heal Veda backend running ✅"

# =============================
# RUN SERVER
# =============================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
