import os, requests
from dotenv import load_dotenv
load_dotenv()

def get_access_token():
    resp = requests.post("https://accounts.zoho.in/oauth/v2/token", params={
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        "client_id": os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "grant_type": "refresh_token"
    })
    data = resp.json()
    if "access_token" not in data:
        raise Exception(f"Zoho token refresh failed: {data}")
    return data["access_token"]

def create_expense(extracted):
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    payload = {
        "account_id": "4019194000000033057",  # copy from Zoho Books > Accountant > Chart of Accounts
        "date": extracted["date"],
        "amount": extracted["amount"],
        "vendor_name": extracted["vendor"],
        "reference_number": extracted.get("invoice_number") or "",
        "description": f"GST: {extracted.get('gst_details')}"
    }
    resp = requests.post(
        f"https://www.zohoapis.in/books/v3/expenses?organization_id={os.environ['ZOHO_ORG_ID']}",
        headers=headers, json=payload
    )
    return resp.json()

if __name__ == "__main__":
    import json
    with open("../results/raw_extractions.json") as f:
        results = json.load(f)

    # Pick which bills and which model's output to push — adjust as needed
    bills_to_push = ["bill_01", "bill_02", "bill_03"]
    model_to_use = "gemini"

    for bill_id in bills_to_push:
        parsed = results[bill_id][model_to_use]["parsed"]
        response = create_expense(parsed)
        print(bill_id, "->", response)