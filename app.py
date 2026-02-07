from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
import os
import easyocr
import tempfile
import json

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
# MEDICINE SCANNER (OCR → AI → VECTOR DB)
# =============================
@app.route("/scan-medicines", methods=["POST"])
def scan_medicines():
    try:
        extracted_text = ""

        # OCR
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

        # 🔥 AI FALLBACK FOR HANDWRITTEN RX
        if not medicines and extracted_text.strip():
            prompt = f"""
You are a medical text extractor.

From the prescription text below, extract:
- medicine_name
- strength
- dosage_instructions

Return ONLY valid JSON in this format:
{{
  "medicine_name": "",
  "strength": "",
  "dosage_instructions": ""
}}

Prescription text:
{extracted_text}
"""

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )

            ai_raw = response.candidates[0].content.parts[0].text.strip()

            try:
                ai_data = json.loads(ai_raw)
            except Exception:
                ai_data = {}

            med_name = ai_data.get("medicine_name", "").strip()
            strength = ai_data.get("strength", "").strip()
            dosage = ai_data.get("dosage_instructions", "").strip()

            if med_name:
                medicines.add(med_name.capitalize())

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

        explanation_prompt = f"""
Explain the following medicines in very simple language.
No diagnosis. No dosage.

Medicines:
{", ".join(medicines)}
"""

        explanation = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=explanation_prompt
        ).candidates[0].content.parts[0].text

        store_in_vector_db(
            f"SCANNER | Medicines: {medicines} | OCR: {extracted_text} | AI: {explanation}",
            source="scanner"
        )

        return jsonify({
            "medicines": medicines,
            "timingAdvice": timing,
            "riskScore": 80,
            "riskLevel": "Informational",
            "alerts": ["Always follow your doctor’s advice"],
            "aiExplanation": explanation
        })

    except Exception as e:
        print("🔥 SCANNER ERROR:", e)
        return jsonify({"error": str(e)}), 500

# =============================
# SAFETY CHECK (SYSTEMATIC)
# =============================
@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)

    prompt = f"""
You are a wellness safety assistant.

Medicine: {data.get("medicines")}
Herb: {data.get("herbs")}
Body Type: {data.get("prakriti")}
Symptoms: {data.get("symptoms")}

FORMAT STRICTLY:

SAFETY RESULT:
Risk Level:
Meaning:

WHY THIS NEEDS ATTENTION:
• Point
• Point

WHAT YOU SHOULD DO:
• Point

WHAT TO AVOID:
• Point

FINAL ADVICE:
2 friendly lines.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(ai_text, source="safety")

    return jsonify({"response": ai_text})

# =============================
# HERBAL PLAN (SYSTEMATIC)
# =============================
@app.route("/generate-herbal-plan", methods=["POST"])
def generate_herbal_plan():
    data = request.get_json()

    prompt = f"""
Generate a SIMPLE herbal wellness plan.

Body Type: {data.get("prakriti")}
Goal: {data.get("goal")}
Lifestyle: {data.get("lifestyle")}
Medicines: {data.get("medicines")}

FORMAT:
RECOMMENDED HERBS
DAILY LIFESTYLE
SAFETY NOTE
SHORT SUMMARY
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(ai_text, source="herbal_plan")

    return jsonify({"response": ai_text})

# =============================
# VECTOR COUNT (VERIFY STORAGE)
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
