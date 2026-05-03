EXTRACTION_PROMPT_TEMPLATE = """
Extract all lab test names and their numeric values from the user's message.
Output as a JSON list of dictionaries with keys: "test_name", "value".
If a test name is abbreviated, expand it to the full common name (e.g., "Hb" -> "Hemoglobin").
If no lab values are found, output an empty list.

User message: {user_input}

JSON output:
"""

EXPLANATION_PROMPT_TEMPLATE = """
Test: {test_name}
Value: {value} {unit}
Reference range: {low_normal}–{high_normal} {unit}
Risk level: {risk_level}

Write a short, compassionate explanation (2-3 sentences) in plain English.
Explain what this value might indicate, without diagnosing.
End with: "Please discuss this result with your doctor."
"""