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
    return resp.json()["access_token"]

def create_expense(extracted):
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    payload = {
        "account_id": "YOUR_EXPENSE_ACCOUNT_ID",  # copy from Zoho Books > Accountant > Chart of Accounts
        "date": extracted["date"],
        "amount": extracted["amount"],
        "vendor_name": extracted["vendor"],
        "reference_number": extracted.get("invoice_number") or "",
        "description": f"GST: {extracted.get('gst_details')}"
    }
    resp = requests.post(
        f"https://books.zoho.in/api/v3/expenses?organization_id={os.environ['ZOHO_ORG_ID']}",
        headers=headers, json=payload
    )
    return resp.json()

if __name__ == "__main__":
    # Example manual test — replace with real extracted values from your results
    example = {"date": "2024-03-14", "amount": 450.00, "vendor": "Sharma General Store",
               "invoice_number": "", "gst_details": "none"}
    print(create_expense(example))