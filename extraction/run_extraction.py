import os, json, base64, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # reads your .env file automatically

from prompt import EXTRACTION_PROMPT

DATASET_DIR = Path("../dataset")
RESULTS_DIR = Path("../results")
RESULTS_DIR.mkdir(exist_ok=True)

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def call_gemini(image_path):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    ext = image_path.suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    resp = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACTION_PROMPT
        ]
    )
    return resp.text, str(resp.usage_metadata)

def call_claude(image_path):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    b64 = encode_image(image_path)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": EXTRACTION_PROMPT}
            ]
        }]
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, str(resp.usage)

def call_openai(image_path):
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    b64 = encode_image(image_path)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }]
    )
    return resp.choices[0].message.content, str(resp.usage)

def call_openrouter(image_path):
    import openai  # OpenRouter uses the same OpenAI-compatible client, just a different base_url
    client = openai.OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1"
    )
    b64 = encode_image(image_path)
    ext = image_path.suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    resp = client.chat.completions.create(
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",  # confirmed free vision model on OpenRouter
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            ]
        }]
    )
    return resp.choices[0].message.content, str(resp.usage)

# Comment out any model you're not using
MODELS = {
    "gemini": call_gemini,
    "openrouter": call_openrouter,
    # "claude": call_claude,
    # "openai": call_openai,
}

def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except Exception:
        return {"_raw": text, "_parse_error": True}

results_path = RESULTS_DIR / "raw_extractions.json"

# Resume from a previous run if the file already has results, instead of
# starting over from scratch every time
if results_path.exists():
    with open(results_path) as f:
        all_results = json.load(f)
else:
    all_results = {}

for bill_path in sorted(DATASET_DIR.glob("bill_*.*")):
    bill_id = bill_path.stem
    if bill_id not in all_results:
        all_results[bill_id] = {}
    for model_name, fn in MODELS.items():
        if model_name in all_results[bill_id] and "error" not in all_results[bill_id][model_name]:
            print(f"{bill_id} / {model_name}: already done, skipping")
            continue
        max_retries = 3
        for attempt in range(max_retries):
            try:
                raw_text, usage = fn(bill_path)
                parsed = clean_json(raw_text)
                all_results[bill_id][model_name] = {"parsed": parsed, "usage": usage}
                print(f"{bill_id} / {model_name}: OK")
                break
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 20 * (attempt + 1)
                    print(f"{bill_id} / {model_name}: rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                all_results[bill_id][model_name] = {"error": str(e)}
                print(f"{bill_id} / {model_name}: FAILED — {e}")
                break
        else:
            all_results[bill_id][model_name] = {"error": "max retries exceeded"}

        # Save after every single call, not just at the very end — so
        # stopping the script early (Ctrl+C) never loses completed work
        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)

        time.sleep(13)  # stay under Gemini free tier's 5 requests/minute limit

print("\nDone. Results saved to results/raw_extractions.json")