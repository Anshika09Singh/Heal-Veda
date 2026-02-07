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

@app.route("/scanner")
def scanner():
    return send_from_directory(FRONTEND_DIR, "scanner.html")

@app.route("/safety")
def safety():
    return send_from_directory(FRONTEND_DIR, "safety.html")

@app.route("/herbal-plan")
def herbal_plan():
    return send_from_directory(FRONTEND_DIR, "herbal-plan.html")

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

# =============================
# MEDICINE TIMING KNOWLEDGE
# =============================
TIMING_RULES = {
    "amoxicillin": "Take after food",
    "paracetamol": "Take after food if needed",
    "pantoprazole": "Take before breakfast",
    "levothyroxine": "Take in the morning on an empty stomach",
    "metformin": "Take with meals"
}

# =============================
# MEDICINE SCANNER (OCR → AI → VECTOR DB)
# =============================
@app.route("/scan-medicines", methods=["POST"])
def scan_medicines():
    try:
        extracted_text = ""

        # -------- OCR --------
        if "image" in request.files:
            image = request.files["image"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                extracted_text = " ".join(
                    ocr_reader.readtext(tmp.name, detail=0)
                ).lower()

        # OCR normalization (VERY IMPORTANT)
        extracted_text = extracted_text.replace("0", "o").replace("5", "s").replace("1", "l")

        print("📄 OCR TEXT:", extracted_text)

        medicines = set()

        # -------- AI MEDICINE EXTRACTION (NO HARDCODING) --------
        if extracted_text.strip():
            prompt = f"""
You are a medical text extractor.

From the prescription text below, extract:
- Medicine name only (no dosage)

Return ONLY the medicine name.

Text:
{extracted_text}
"""
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )

            ai_medicine = response.candidates[0].content.parts[0].text.strip().lower()
            ai_medicine = ai_medicine.replace("mg", "").strip()

            if len(ai_medicine) > 3:
                medicines.add(ai_medicine.capitalize())

        medicines = list(medicines)

        # -------- SAFE FALLBACK --------
        if not medicines:
            return jsonify({
                "medicines": [],
                "timingAdvice": [],
                "riskScore": 50,
                "riskLevel": "Unknown",
                "alerts": ["Medicine names were unclear"],
                "aiExplanation": "Please upload a clearer prescription image."
            })

        # -------- TIMING ADVICE --------
        timing = []
        for med in medicines:
            timing.append({
                "medicine": med,
                "advice": TIMING_RULES.get(
                    med.lower(),
                    "Follow your doctor's instructions"
                )
            })

        # -------- AI EXPLANATION --------
        prompt = f"""
Explain the following medicine in very simple language.
No diagnosis. No dosage.

Medicine:
{", ".join(medicines)}
"""
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        ai_text = response.candidates[0].content.parts[0].text

        # -------- VECTOR DB STORE --------
        store_in_vector_db(
            f"SCANNER | OCR: {extracted_text} | Medicines: {medicines} | AI: {ai_text}",
            source="scanner"
        )

        return jsonify({
            "medicines": medicines,
            "timingAdvice": timing,
            "riskScore": 80,
            "riskLevel": "Informational",
            "alerts": ["Always follow your doctor's advice"],
            "aiExplanation": ai_text
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
Symptoms: {", ".join(data.get("symptoms", []))}

Respond in this format only:

SAFETY RESULT:
Risk Level:
Meaning:

WHY THIS NEEDS ATTENTION:
• Point
• Point

WHAT YOU SHOULD DO:
• Point
• Point

WHAT TO AVOID:
• Point
• Point

FINAL ADVICE:
2 friendly lines.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(
        f"SAFETY | {ai_text}",
        source="safety"
    )

    return jsonify({"response": ai_text})

# =============================
# HERBAL PLAN
# =============================
@app.route("/generate-herbal-plan", methods=["POST"])
def generate_herbal_plan():
    data = request.get_json()

    prompt = f"""
Create a simple herbal wellness plan.

Body Type: {data.get("prakriti")}
Goal: {data.get("goal")}
Lifestyle: {data.get("lifestyle")}
Medicines: {data.get("medicines")}

Use simple language and this format:

RECOMMENDED HERBS:
1. Herb
• What it does:
• How to use:
• Safety note:

DAILY LIFESTYLE GUIDANCE:
Morning:
Daytime:
Evening:

IMPORTANT SAFETY NOTE:
SHORT SUMMARY:
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    ai_text = response.candidates[0].content.parts[0].text

    store_in_vector_db(
        f"HERBAL_PLAN | {ai_text}",
        source="herbal_plan"
    )

    return jsonify({"response": ai_text})

# =============================
# VECTOR DB DEBUG
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
