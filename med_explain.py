import os
import sys
import json
import re
import pandas as pd
from dotenv import load_dotenv
import PyPDF2
from groq import Groq

os.chdir(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

client = Groq(api_key=GROQ_API_KEY)

# Load reference ranges
ref_df = pd.read_csv("reference_ranges.csv")
ref_dict = {}
for _, row in ref_df.iterrows():
    test_name = row['test_name'].lower().replace('_', ' ')
    ref_dict[test_name] = {
        'unit': row['unit'],
        'low': float(row['low_normal']),
        'high': float(row['high_normal']),
        'high_risk': float(row['high_risk_threshold'])
    }
print(f"Loaded {len(ref_dict)} reference ranges.")

# ----- Alias mapping for common variations -----
aliases = {
    'hemoglobin a1c': 'hba1c',
    'hba1c': 'hba1c',
    'a1c': 'hba1c',
    'glycated hemoglobin': 'hba1c',
    'fasting glucose': 'glucose fasting',
    'random glucose': 'glucose random',
    'ldl': 'ldl cholesterol',
    'hdl': 'hdl cholesterol',
    'triglycerides': 'triglycerides',
    'trig': 'triglycerides',
    'wbc': 'wbc count',
    'rbc': 'rbc count',
    'plt': 'platelets',
    'crp': 'crp c reactive protein',
    'egfr': 'egfr estimated gfr',
    'hemoglobin': 'hemoglobin male',  # will fallback to male version
}

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

def extract_entities(user_text):
    prompt = EXTRACTION_PROMPT.format(user_input=user_text)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful medical AI assistant. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        entities = json.loads(text)
        if not isinstance(entities, list):
            entities = []
        return entities
    except Exception as e:
        print("Error during extraction:", e)
        return []

def classify_risk(test_name, value):
    # first, resolve alias
    clean_name = test_name.lower().replace('_', ' ')
    if clean_name in aliases:
        clean_name = aliases[clean_name]
    if clean_name not in ref_dict:
        # try removing 'male'/'female' suffix if exists
        if clean_name.endswith(' male'):
            clean_name = clean_name.replace(' male', '')
        elif clean_name.endswith(' female'):
            clean_name = clean_name.replace(' female', '')
        if clean_name not in ref_dict:
            return "Unknown (reference not found)"
    ref = ref_dict[clean_name]
    low = ref['low']
    high = ref['high']
    high_risk_th = ref['high_risk']
    try:
        val = float(value)
    except:
        return "Invalid value"
    if val < low * 0.7 or val > high_risk_th:
        return "High Risk"
    elif val < low or val > high:
        return "Moderate Risk"
    else:
        return "Low Risk"

def explain_abnormality(test_name, value, unit, low, high, risk_level):
    prompt = EXPLANATION_PROMPT.format(
        test_name=test_name,
        value=value,
        unit=unit,
        low_normal=low,
        high_normal=high,
        risk_level=risk_level
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate explanation: {e}"

def generate_report(entities):
    results = []
    for item in entities:
        test_name_raw = item.get('test_name', '').lower().strip()
        value_str = str(item.get('value', ''))
        match = re.search(r"(\d+\.?\d*)", value_str)
        if not match:
            continue
        value_num = float(match.group(1))

        # ---- improved lookup with aliases ----
        lookup_name = test_name_raw
        if lookup_name in aliases:
            lookup_name = aliases[lookup_name]
        # also try without spaces/underscores
        lookup_no_space = lookup_name.replace(' ', '').replace('_', '')
        
        ref = None
        if lookup_name in ref_dict:
            ref = ref_dict[lookup_name]
        elif lookup_no_space in ref_dict:
            ref = ref_dict[lookup_no_space]
        else:
            # fallback: partial match (e.g., "hemoglobin" matches "hemoglobin male")
            for key in ref_dict.keys():
                if lookup_name in key or key in lookup_name:
                    ref = ref_dict[key]
                    break
        if ref is None:
            results.append({
                "Test": test_name_raw.title(),
                "Value": value_str,
                "Reference Range": "Not in database",
                "Risk Level": "Unknown",
                "Explanation": f"Test '{test_name_raw}' not found. Please consult a doctor."
            })
            continue

        risk = classify_risk(test_name_raw, value_num)
        if risk != "Low Risk":
            explanation = explain_abnormality(
                test_name_raw.title(),
                value_num,
                ref['unit'],
                ref['low'],
                ref['high'],
                risk
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

def display_report(results):
    if not results:
        print("No lab tests could be extracted.")
        return
    print("\n" + "="*80)
    print("MedExplain – Lab Report Interpretation".center(80))
    print("="*80)
    for res in results:
        print(f"\n📌 {res['Test']}")
        print(f"   Value: {res['Value']}")
        print(f"   Reference: {res['Reference Range']}")
        print(f"   Risk: {res['Risk Level']}")
        print(f"   💬 {res['Explanation']}")
        print("-"*80)
    print("\n⚠️ DISCLAIMER: AI-generated interpretation only. Always consult a doctor.\n")

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text()
    return text

def main():
    print("🧪 MedExplain Agent – Lab Report Interpreter")
    print("1. Paste text")
    print("2. Upload PDF file")
    choice = input("Enter 1 or 2: ")
    user_input = ""
    if choice == '1':
        user_input = input("\nPaste your lab report text:\n")
    elif choice == '2':
        path = input("Enter PDF file path: ")
        try:
            user_input = extract_text_from_pdf(path)
            print("PDF extracted successfully.")
        except Exception as e:
            print("Error reading PDF:", e)
            return
    else:
        print("Invalid choice")
        return

    if not user_input.strip():
        print("No input.")
        return

    print("\n🔍 Extracting test names and values...")
    entities = extract_entities(user_input)
    if not entities:
        print("No lab tests recognized. Try again with clearer format.")
        return

    print("📊 Generating report...")
    report = generate_report(entities)
    display_report(report)

if __name__ == "__main__":
    main()