import os
from dotenv import load_dotenv
load_dotenv()

print("Testing Gemini key...")
try:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hello in one word."
    )
    print("  GEMINI OK:", resp.text.strip())
except Exception as e:
    print("  GEMINI FAILED:", e)
    
print("\nTesting OpenAI key...")
try:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello in one word."}]
    )
    print("  OPENAI OK:", resp.choices[0].message.content.strip())
except Exception as e:
    print("  OPENAI FAILED:", e)

print("\nTesting Claude key...")
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say hello in one word."}]
    )
    print("  CLAUDE OK:", resp.content[0].text.strip())
except Exception as e:
    print("  CLAUDE FAILED:", e)
print("\nTesting OpenRouter key...")

try:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
    resp = client.chat.completions.create(
        model="qwen/qwen2.5-vl-72b-instruct:free",
        messages=[{"role": "user", "content": "Say hello in one word."}]
    )
    print("  OPENROUTER OK:", resp.choices[0].message.content.strip())
except Exception as e:
    print("  OPENROUTER FAILED:", e)