import json
import time
import requests

BASE_URL = "http://localhost:8000"

def run_e2e_pipeline_test():
    print("🚀 Starting End-to-End Live HTTP Integration Test Suite...\n")
    
    # Generate a completely unique email using a timestamp for a clean database execution run
    unique_id = int(time.time())
    test_email = f"senior_tester_{unique_id}@eng.com"
    test_password = "SecurePassword123!"
    
    # -----------------------------------------------------------------
    # STEP 1: Register User Account
    # -----------------------------------------------------------------
    register_url = f"{BASE_URL}/api/auth/register/"
    user_payload = {
        "email": test_email,
        "password": test_password
    }
    
    print(f"1️⃣ Issuing POST to {register_url}...")
    reg_response = requests.post(register_url, json=user_payload)
    print(f"   Status Code: {reg_response.status_code}")
    print(f"   Payload: {json.dumps(reg_response.json(), indent=2)}\n")
    
    if reg_response.status_code != 201:
        print("❌ Registration failed! Terminating test loop.")
        return

    # -----------------------------------------------------------------
    # STEP 2: Custom Authenticate & Fetch JWT
    # -----------------------------------------------------------------
    login_url = f"{BASE_URL}/api/auth/login/"
    login_payload = {
        "email": test_email,  # 💡 Clean explicit matching to your email field parameters
        "password": test_password
    }
    
    print(f"2️⃣ Exchanging credentials for JWT at {login_url}...")
    login_response = requests.post(login_url, json=login_payload)
    print(f"   Status Code: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"❌ Login failed! Details: {login_response.text}")
        return
        
    tokens = login_response.json()
    access_token = tokens["access"]
    print(f"   Access Token Acquired (Truncated): {access_token[:30]}...\n")
    
    # -----------------------------------------------------------------
    # STEP 3: Execute Guardrailed Query Request
    # -----------------------------------------------------------------
    query_url = f"{BASE_URL}/api/query/"
    query_payload = {
        "question": "Show all product names and categories"
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"3️⃣ Transmitting Guardrailed Query Request to {query_url}...")
    query_response = requests.post(query_url, json=query_payload, headers=headers)
    print(f"   Status Code: {query_response.status_code}")
    print(f"   Final Runtime Payload State:")
    print(json.dumps(query_response.json(), indent=2))
    print("\n==================================================================")
    print("🏁 Pipeline Integration Check Complete.")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_pipeline_test()

