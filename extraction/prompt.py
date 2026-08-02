EXTRACTION_PROMPT = """You are looking at a photo of a handwritten or semi-handwritten
Indian bill/receipt. Extract the following fields and return ONLY valid JSON
(no markdown, no explanation) with exactly these keys:

{
  "vendor": "shop or business name, or null if unreadable",
  "invoice_number": "bill/invoice number if present, else null",
  "date": "date in YYYY-MM-DD format if determinable, else the raw text you see, else null",
  "amount": "total amount as a number (no currency symbol), or null",
  "currency": "currency code, e.g. INR, or null",
  "gst_details": "any tax/GST info visible as free text, or null"
}

If a field is not visible or you cannot read it confidently, use null rather than guessing.
"""