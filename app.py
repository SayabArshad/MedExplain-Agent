import streamlit as st
import re
import json
import PyPDF2
from groq import Groq
from dotenv import load_dotenv
import os

# ---------- Load environment ----------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found in .env file")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ---------- Embedded reference ranges (100+ tests) ----------
ref_dict = {
    'hemoglobin male': {'unit': 'g/dL', 'low': 13.5, 'high': 17.5, 'high_risk': 20.0},
    'hemoglobin female': {'unit': 'g/dL', 'low': 12.0, 'high': 15.5, 'high_risk': 18.0},
    'hematocrit male': {'unit': '%', 'low': 41.0, 'high': 53.0, 'high_risk': 60.0},
    'hematocrit female': {'unit': '%', 'low': 36.0, 'high': 46.0, 'high_risk': 55.0},
    'rbc count male': {'unit': '10^6/uL', 'low': 4.7, 'high': 6.1, 'high_risk': 7.0},
    'rbc count female': {'unit': '10^6/uL', 'low': 4.2, 'high': 5.4, 'high_risk': 6.5},
    'wbc count': {'unit': '10^3/uL', 'low': 4.0, 'high': 11.0, 'high_risk': 20.0},
    'platelets': {'unit': '10^3/uL', 'low': 150.0, 'high': 450.0, 'high_risk': 600.0},
    'mcv': {'unit': 'fL', 'low': 80.0, 'high': 100.0, 'high_risk': 120.0},
    'mch': {'unit': 'pg', 'low': 27.0, 'high': 33.0, 'high_risk': 40.0},
    'mchc': {'unit': 'g/dL', 'low': 32.0, 'high': 36.0, 'high_risk': 40.0},
    'rdw': {'unit': '%', 'low': 11.5, 'high': 14.5, 'high_risk': 18.0},
    'neutrophils': {'unit': '%', 'low': 40.0, 'high': 60.0, 'high_risk': 80.0},
    'lymphocytes': {'unit': '%', 'low': 20.0, 'high': 40.0, 'high_risk': 60.0},
    'monocytes': {'unit': '%', 'low': 2.0, 'high': 8.0, 'high_risk': 15.0},
    'eosinophils': {'unit': '%', 'low': 1.0, 'high': 4.0, 'high_risk': 10.0},
    'basophils': {'unit': '%', 'low': 0.5, 'high': 1.0, 'high_risk': 3.0},
    'glucose fasting': {'unit': 'mg/dL', 'low': 70.0, 'high': 100.0, 'high_risk': 250.0},
    'glucose random': {'unit': 'mg/dL', 'low': 70.0, 'high': 140.0, 'high_risk': 200.0},
    'hba1c': {'unit': '%', 'low': 4.0, 'high': 5.6, 'high_risk': 9.0},
    'insulin fasting': {'unit': 'uIU/mL', 'low': 2.6, 'high': 24.9, 'high_risk': 50.0},
    'c peptide': {'unit': 'ng/mL', 'low': 0.5, 'high': 2.0, 'high_risk': 4.0},
    'sodium': {'unit': 'mmol/L', 'low': 135.0, 'high': 145.0, 'high_risk': 160.0},
    'potassium': {'unit': 'mmol/L', 'low': 3.5, 'high': 5.1, 'high_risk': 6.5},
    'chloride': {'unit': 'mmol/L', 'low': 98.0, 'high': 107.0, 'high_risk': 120.0},
    'co2 bicarbonate': {'unit': 'mmol/L', 'low': 22.0, 'high': 29.0, 'high_risk': 40.0},
    'anion gap': {'unit': 'mmol/L', 'low': 4.0, 'high': 12.0, 'high_risk': 20.0},
    'calcium total': {'unit': 'mg/dL', 'low': 8.5, 'high': 10.2, 'high_risk': 13.0},
    'ionized calcium': {'unit': 'mg/dL', 'low': 4.6, 'high': 5.3, 'high_risk': 6.5},
    'magnesium': {'unit': 'mg/dL', 'low': 1.7, 'high': 2.2, 'high_risk': 3.5},
    'phosphorus': {'unit': 'mg/dL', 'low': 2.5, 'high': 4.5, 'high_risk': 6.0},
    'bun': {'unit': 'mg/dL', 'low': 7.0, 'high': 20.0, 'high_risk': 50.0},
    'creatinine': {'unit': 'mg/dL', 'low': 0.6, 'high': 1.2, 'high_risk': 2.5},
    'bun creatinine ratio': {'unit': 'ratio', 'low': 10.0, 'high': 20.0, 'high_risk': 30.0},
    'uric acid male': {'unit': 'mg/dL', 'low': 3.5, 'high': 7.2, 'high_risk': 10.0},
    'uric acid female': {'unit': 'mg/dL', 'low': 2.5, 'high': 6.0, 'high_risk': 9.0},
    'total protein': {'unit': 'g/dL', 'low': 6.0, 'high': 8.3, 'high_risk': 10.0},
    'albumin': {'unit': 'g/dL', 'low': 3.4, 'high': 5.4, 'high_risk': 6.0},
    'globulin': {'unit': 'g/dL', 'low': 2.0, 'high': 3.5, 'high_risk': 5.0},
    'albumin globulin ratio': {'unit': 'ratio', 'low': 0.8, 'high': 2.0, 'high_risk': 3.0},
    'bilirubin total': {'unit': 'mg/dL', 'low': 0.3, 'high': 1.2, 'high_risk': 3.0},
    'bilirubin direct': {'unit': 'mg/dL', 'low': 0.0, 'high': 0.3, 'high_risk': 1.0},
    'bilirubin indirect': {'unit': 'mg/dL', 'low': 0.2, 'high': 0.9, 'high_risk': 2.0},
    'alp alkaline phosphatase': {'unit': 'U/L', 'low': 44.0, 'high': 147.0, 'high_risk': 300.0},
    'alt sgpt': {'unit': 'U/L', 'low': 10.0, 'high': 40.0, 'high_risk': 100.0},
    'ast sgot': {'unit': 'U/L', 'low': 10.0, 'high': 40.0, 'high_risk': 100.0},
    'ggt': {'unit': 'U/L', 'low': 9.0, 'high': 48.0, 'high_risk': 150.0},
    'ldh': {'unit': 'U/L', 'low': 140.0, 'high': 280.0, 'high_risk': 500.0},
    'cholesterol total': {'unit': 'mg/dL', 'low': 125.0, 'high': 200.0, 'high_risk': 300.0},
    'ldl cholesterol': {'unit': 'mg/dL', 'low': 0.0, 'high': 100.0, 'high_risk': 190.0},
    'hdl cholesterol': {'unit': 'mg/dL', 'low': 40.0, 'high': 60.0, 'high_risk': 100.0},
    'triglycerides': {'unit': 'mg/dL', 'low': 0.0, 'high': 150.0, 'high_risk': 500.0},
    'vldl cholesterol': {'unit': 'mg/dL', 'low': 5.0, 'high': 40.0, 'high_risk': 80.0},
    'tsh': {'unit': 'mIU/L', 'low': 0.4, 'high': 4.0, 'high_risk': 10.0},
    'free t3': {'unit': 'pg/mL', 'low': 2.3, 'high': 4.2, 'high_risk': 6.0},
    'free t4': {'unit': 'ng/dL', 'low': 0.8, 'high': 1.8, 'high_risk': 3.0},
    'total t3': {'unit': 'ng/dL', 'low': 80.0, 'high': 200.0, 'high_risk': 300.0},
    'total t4': {'unit': 'mcg/dL', 'low': 4.5, 'high': 12.0, 'high_risk': 15.0},
    'reverse t3': {'unit': 'ng/dL', 'low': 10.0, 'high': 24.0, 'high_risk': 40.0},
    'thyroglobulin': {'unit': 'ng/mL', 'low': 1.0, 'high': 40.0, 'high_risk': 100.0},
    'anti tpo antibodies': {'unit': 'IU/mL', 'low': 0.0, 'high': 35.0, 'high_risk': 100.0},
    'anti tg antibodies': {'unit': 'IU/mL', 'low': 0.0, 'high': 40.0, 'high_risk': 100.0},
    'vitamin b12': {'unit': 'pg/mL', 'low': 200.0, 'high': 900.0, 'high_risk': 1500.0},
    'folate serum': {'unit': 'ng/mL', 'low': 2.5, 'high': 20.0, 'high_risk': 30.0},
    'folate rbc': {'unit': 'ng/mL', 'low': 150.0, 'high': 600.0, 'high_risk': 800.0},
    'vitamin d 25 oh': {'unit': 'ng/mL', 'low': 20.0, 'high': 50.0, 'high_risk': 100.0},
    'vitamin a retinol': {'unit': 'mcg/dL', 'low': 20.0, 'high': 60.0, 'high_risk': 100.0},
    'vitamin e alpha tocopherol': {'unit': 'mg/L', 'low': 5.0, 'high': 20.0, 'high_risk': 30.0},
    'vitamin c ascorbic acid': {'unit': 'mg/dL', 'low': 0.4, 'high': 2.0, 'high_risk': 3.0},
    'ferritin male': {'unit': 'ng/mL', 'low': 24.0, 'high': 336.0, 'high_risk': 500.0},
    'ferritin female': {'unit': 'ng/mL', 'low': 11.0, 'high': 307.0, 'high_risk': 500.0},
    'iron serum': {'unit': 'mcg/dL', 'low': 50.0, 'high': 170.0, 'high_risk': 250.0},
    'tibc': {'unit': 'mcg/dL', 'low': 250.0, 'high': 450.0, 'high_risk': 600.0},
    'transferrin saturation': {'unit': '%', 'low': 20.0, 'high': 50.0, 'high_risk': 70.0},
    'crp c reactive protein': {'unit': 'mg/L', 'low': 0.0, 'high': 5.0, 'high_risk': 20.0},
    'esr sed rate': {'unit': 'mm/hr', 'low': 0.0, 'high': 20.0, 'high_risk': 50.0},
    'prothrombin time pt': {'unit': 'sec', 'low': 10.0, 'high': 13.0, 'high_risk': 20.0},
    'inr': {'unit': 'ratio', 'low': 0.8, 'high': 1.2, 'high_risk': 2.5},
    'aptt': {'unit': 'sec', 'low': 25.0, 'high': 35.0, 'high_risk': 50.0},
    'fibrinogen': {'unit': 'mg/dL', 'low': 200.0, 'high': 400.0, 'high_risk': 600.0},
    'd dimer': {'unit': 'mcg/mL', 'low': 0.0, 'high': 0.5, 'high_risk': 2.0},
    'troponin i': {'unit': 'ng/mL', 'low': 0.0, 'high': 0.04, 'high_risk': 0.5},
    'troponin t': {'unit': 'ng/mL', 'low': 0.0, 'high': 0.01, 'high_risk': 0.1},
    'ck mb': {'unit': 'ng/mL', 'low': 0.0, 'high': 5.0, 'high_risk': 15.0},
    'ck creatine kinase': {'unit': 'U/L', 'low': 30.0, 'high': 200.0, 'high_risk': 500.0},
    'bnp b type natriuretic peptide': {'unit': 'pg/mL', 'low': 0.0, 'high': 100.0, 'high_risk': 500.0},
    'nt probnp': {'unit': 'pg/mL', 'low': 0.0, 'high': 125.0, 'high_risk': 1000.0},
    'homocysteine': {'unit': 'mcmol/L', 'low': 0.0, 'high': 15.0, 'high_risk': 30.0},
    'psa total': {'unit': 'ng/mL', 'low': 0.0, 'high': 4.0, 'high_risk': 10.0},
    'psa free': {'unit': 'ng/mL', 'low': 0.0, 'high': 0.5, 'high_risk': 1.5},
    'ca 125': {'unit': 'U/mL', 'low': 0.0, 'high': 35.0, 'high_risk': 100.0},
    'ca 19 9': {'unit': 'U/mL', 'low': 0.0, 'high': 37.0, 'high_risk': 100.0},
    'cea': {'unit': 'ng/mL', 'low': 0.0, 'high': 3.0, 'high_risk': 10.0},
    'afp alpha fetoprotein': {'unit': 'ng/mL', 'low': 0.0, 'high': 10.0, 'high_risk': 50.0},
    'beta hcg non pregnant': {'unit': 'mIU/mL', 'low': 0.0, 'high': 5.0, 'high_risk': 10.0},
    'cortisol morning': {'unit': 'mcg/dL', 'low': 5.0, 'high': 25.0, 'high_risk': 40.0},
    'aldosterone standing': {'unit': 'ng/dL', 'low': 4.0, 'high': 31.0, 'high_risk': 60.0},
    'renin standing': {'unit': 'ng/mL/hr', 'low': 0.5, 'high': 6.0, 'high_risk': 10.0},
    'testosterone male': {'unit': 'ng/dL', 'low': 300.0, 'high': 1000.0, 'high_risk': 1500.0},
    'testosterone female': {'unit': 'ng/dL', 'low': 15.0, 'high': 70.0, 'high_risk': 100.0},
    'estradiol female': {'unit': 'pg/mL', 'low': 20.0, 'high': 400.0, 'high_risk': 600.0},
    'progesterone female': {'unit': 'ng/mL', 'low': 0.1, 'high': 20.0, 'high_risk': 30.0},
    'prolactin': {'unit': 'ng/mL', 'low': 4.0, 'high': 23.0, 'high_risk': 50.0},
    'lh': {'unit': 'mIU/mL', 'low': 1.0, 'high': 20.0, 'high_risk': 40.0},
    'fsh': {'unit': 'mIU/mL', 'low': 1.0, 'high': 25.0, 'high_risk': 50.0},
    'psa free total ratio': {'unit': '%', 'low': 0.0, 'high': 25.0, 'high_risk': 50.0},
    'ph arterial blood': {'unit': 'pH', 'low': 7.35, 'high': 7.45, 'high_risk': 7.55},
    'pco2 arterial': {'unit': 'mmHg', 'low': 35.0, 'high': 45.0, 'high_risk': 55.0},
    'po2 arterial': {'unit': 'mmHg', 'low': 75.0, 'high': 100.0, 'high_risk': 60.0},
    'bicarbonate arterial': {'unit': 'mmol/L', 'low': 22.0, 'high': 26.0, 'high_risk': 30.0},
    'lactate arterial': {'unit': 'mmol/L', 'low': 0.5, 'high': 2.0, 'high_risk': 4.0},
    'ammonia': {'unit': 'mcg/dL', 'low': 15.0, 'high': 45.0, 'high_risk': 100.0},
    'myoglobin': {'unit': 'ng/mL', 'low': 0.0, 'high': 85.0, 'high_risk': 200.0},
    'lipase': {'unit': 'U/L', 'low': 10.0, 'high': 60.0, 'high_risk': 120.0},
    'amylase': {'unit': 'U/L', 'low': 30.0, 'high': 110.0, 'high_risk': 200.0},
    'ige immunoglobulin e': {'unit': 'IU/mL', 'low': 0.0, 'high': 100.0, 'high_risk': 500.0},
    'egfr estimated gfr': {'unit': 'mL/min/1.73m2', 'low': 60.0, 'high': 120.0, 'high_risk': 30.0},
    'microalbumin urine': {'unit': 'mg/L', 'low': 0.0, 'high': 30.0, 'high_risk': 100.0},
    'protein urine 24h': {'unit': 'mg/24h', 'low': 0.0, 'high': 150.0, 'high_risk': 300.0},
    'cortisol urine free': {'unit': 'mcg/24h', 'low': 4.0, 'high': 50.0, 'high_risk': 100.0},
    'creatinine clearance': {'unit': 'mL/min', 'low': 80.0, 'high': 120.0, 'high_risk': 50.0},
    'osmolality serum': {'unit': 'mOsm/kg', 'low': 275.0, 'high': 295.0, 'high_risk': 320.0},
    'osmolality urine': {'unit': 'mOsm/kg', 'low': 300.0, 'high': 900.0, 'high_risk': 1200.0},
}
st.success(f"✅ Loaded {len(ref_dict)} reference ranges")

# ---------- Aliases ----------
aliases = {
    'hemoglobin a1c': 'hba1c', 'hba1c': 'hba1c', 'a1c': 'hba1c',
    'fasting glucose': 'glucose fasting', 'random glucose': 'glucose random',
    'ldl': 'ldl cholesterol', 'hdl': 'hdl cholesterol', 'trig': 'triglycerides',
    'wbc': 'wbc count', 'rbc': 'rbc count', 'plt': 'platelets',
    'crp': 'crp c reactive protein', 'egfr': 'egfr estimated gfr',
    'rdw': 'rdw', 'mcv': 'mcv', 'mch': 'mch', 'mchc': 'mchc',
    'bun': 'bun', 'creatinine': 'creatinine',
    'alt': 'alt sgpt', 'ast': 'ast sgot', 'alp': 'alp alkaline phosphatase',
    'tsh': 'tsh', 't3': 'total t3', 't4': 'total t4',
    'ferritin': 'ferritin male',
    'vitamin d': 'vitamin d 25 oh', 'b12': 'vitamin b12',
    'psa': 'psa total',
}

# ---------- Prompts ----------
EXTRACTION_PROMPT = """
Extract all lab test names and their numeric values from the user's message.
Output as a JSON list of dictionaries with keys: "test_name", "value".
If a test name is abbreviated, expand it to the full common name (e.g., "Hb" -> "Hemoglobin").
If no lab values are found, output an empty list.

User message: {user_input}

JSON output:
"""

EXPLANATION_PROMPT = """
Test: {test_name}
Value: {value} {unit}
Reference range: {low_normal}–{high_normal} {unit}
Risk level: {risk_level}

Write a short, compassionate explanation (2-3 sentences) in plain English.
Explain what this value might indicate, without diagnosing.
End with: "Please discuss this result with your doctor."
"""

# ---------- Helper functions ----------
def extract_entities(user_text):
    prompt = EXTRACTION_PROMPT.format(user_input=user_text)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a JSON generator. Output ONLY valid JSON. No extra text, no markdown, no commentary."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        
        # Clean markdown and extract JSON
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # If still not starting with [ or {, try regex to find JSON array
        if text and text[0] not in ['[', '{']:
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            else:
                st.warning("LLM returned non-JSON output. Raw content:")
                st.code(text[:500])
                return []
        
        entities = json.loads(text)
        if not isinstance(entities, list):
            entities = []
        return entities
    except Exception as e:
        st.error(f"Extraction error: {e}")
        if 'response' in locals():
            st.text("Raw response preview:")
            st.code(response.choices[0].message.content[:500])
        return []

def classify_risk(test_name, value):
    clean_name = test_name.lower().replace('_', ' ')
    if clean_name in aliases:
        clean_name = aliases[clean_name]
    if clean_name not in ref_dict:
        # try removing male/female suffix
        if clean_name.endswith(' male'):
            clean_name = clean_name.replace(' male', '')
        elif clean_name.endswith(' female'):
            clean_name = clean_name.replace(' female', '')
        if clean_name not in ref_dict:
            return "Unknown"
    ref = ref_dict[clean_name]
    low = ref['low']
    high = ref['high']
    high_risk_th = ref['high_risk']
    try:
        val = float(value)
    except:
        return "Invalid"
    if val < low * 0.7 or val > high_risk_th:
        return "High Risk"
    elif val < low or val > high:
        return "Moderate Risk"
    else:
        return "Low Risk"

def explain_abnormality(test_name, value, unit, low, high, risk_level):
    prompt = EXPLANATION_PROMPT.format(
        test_name=test_name, value=value, unit=unit,
        low_normal=low, high_normal=high, risk_level=risk_level
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Explanation error: {e}"

def generate_report(entities):
    results = []
    for item in entities:
        test_name_raw = item.get('test_name', '').lower().strip()
        value_str = str(item.get('value', ''))
        match = re.search(r"(\d+\.?\d*)", value_str)
        if not match:
            continue
        value_num = float(match.group(1))

        lookup_name = test_name_raw
        if lookup_name in aliases:
            lookup_name = aliases[lookup_name]
        lookup_no_space = lookup_name.replace(' ', '').replace('_', '')
        
        ref = None
        if lookup_name in ref_dict:
            ref = ref_dict[lookup_name]
        elif lookup_no_space in ref_dict:
            ref = ref_dict[lookup_no_space]
        else:
            # fuzzy match: if any key contains the lookup_name or vice versa
            for key in ref_dict.keys():
                if lookup_name in key or key in lookup_name:
                    ref = ref_dict[key]
                    break
        if ref is None:
            results.append({
                "Test": test_name_raw.title(),
                "Value": value_str,
                "Reference Range": "Not found",
                "Risk Level": "Unknown",
                "Explanation": f"Test '{test_name_raw}' not in database."
            })
            continue

        risk = classify_risk(test_name_raw, value_num)
        if risk != "Low Risk":
            explanation = explain_abnormality(
                test_name_raw.title(), value_num, ref['unit'],
                ref['low'], ref['high'], risk
            )
        else:
            explanation = "Value is within normal range. No immediate concern."
        results.append({
            "Test": test_name_raw.title(),
            "Value": f"{value_num} {ref['unit']}",
            "Reference Range": f"{ref['low']}–{ref['high']} {ref['unit']}",
            "Risk Level": risk,
            "Explanation": explanation
        })
    return results

def extract_text_from_pdf(pdf_file):
    text = ""
    reader = PyPDF2.PdfReader(pdf_file)
    for page in reader.pages:
        text += page.extract_text()
    return text

# ---------- Streamlit UI ----------
st.set_page_config(page_title="MedExplain", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f7ff; }
    .stApp { background: linear-gradient(135deg, #e6f0fa 0%, #d4e4f0 100%); }
    .report-card { background-color: white; border-radius: 15px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-left: 8px solid #2c7da0; }
    .risk-high { color: #d62828; font-weight: bold; background-color: #ffe0e0; padding: 4px 8px; border-radius: 20px; display: inline-block; }
    .risk-moderate { color: #e9c46a; font-weight: bold; background-color: #fff3d4; padding: 4px 8px; border-radius: 20px; display: inline-block; }
    .risk-low { color: #2a9d8f; font-weight: bold; background-color: #e0f5f2; padding: 4px 8px; border-radius: 20px; display: inline-block; }
    .logo-text { font-size: 2.5rem; font-weight: bold; color: #1f4e6e; text-align: center; }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown('<div class="logo-text">🩺 MedExplain 🧪</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #2c7da0;'>AI-powered Laboratory Test Interpreter</p>", unsafe_allow_html=True)

st.markdown("---")

input_method = st.radio("Select input method:", ["Paste text", "Upload PDF"], horizontal=True)

user_input = ""
if input_method == "Paste text":
    user_input = st.text_area("Enter your lab results:", height=150, placeholder="Example:\nHbA1c 8.1%\nHemoglobin 10.2 g/dL\nLDL 130 mg/dL")
else:
    uploaded_file = st.file_uploader("Upload a PDF lab report", type="pdf")
    if uploaded_file:
        with st.spinner("Extracting text from PDF..."):
            user_input = extract_text_from_pdf(uploaded_file)
        st.success("Text extracted!")

if st.button("🔬 Interpret Results", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Please provide some lab results.")
    else:
        with st.spinner("Analyzing with AI..."):
            entities = extract_entities(user_input)
            if not entities:
                st.error("No lab test names recognized. Please check your input format.")
            else:
                report = generate_report(entities)
                if not report:
                    st.warning("No matching reference ranges found. Try a different test name.")
                else:
                    st.success(f"✅ Interpretation complete for {len(report)} test(s)")
                    for entry in report:
                        risk_class = ""
                        if "High" in entry["Risk Level"]:
                            risk_class = "risk-high"
                        elif "Moderate" in entry["Risk Level"]:
                            risk_class = "risk-moderate"
                        elif "Low" in entry["Risk Level"]:
                            risk_class = "risk-low"
                        with st.container():
                            st.markdown(f'<div class="report-card">', unsafe_allow_html=True)
                            col1, col2 = st.columns([2,1])
                            with col1:
                                st.markdown(f"**🧪 {entry['Test']}**")
                                st.write(f"**Value:** {entry['Value']}")
                                st.write(f"**Reference:** {entry['Reference Range']}")
                            with col2:
                                st.markdown(f'<span class="{risk_class}">⚠️ {entry["Risk Level"]}</span>', unsafe_allow_html=True)
                            st.write(f"**💬 Explanation:** {entry['Explanation']}")
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.markdown("---")
                    st.warning("⚠️ **Medical Disclaimer:** This is an AI-generated interpretation only. It is not a substitute for professional medical advice. Always consult a qualified healthcare provider.")

st.markdown("---")
st.caption("MedExplain v1.0 – Built with Streamlit & Groq for educational purposes")