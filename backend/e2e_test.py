import requests
import time
import random
import string

BASE_URL = "http://localhost:8000/api/v1"

def generate_random_email():
    return f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}@example.com"

def test_e2e_flow():
    email = generate_random_email()
    password = "TestPassword123!"
    full_name = "End-to-End Test User"

    print(f"--- Starting E2E Test ---")
    print(f"Registering user: {email}")

    # 1. Register
    register_payload = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json=register_payload)
        if r.status_code != 201:
            print(f"[ERROR] Registration failed. Status: {r.status_code}, Response: {r.text}")
            return False
        
        print(f"[SUCCESS] Registered user.")
        
        # 2. Login
        login_payload = {
            "email": email,
            "password": password
        }
        
        r = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        if r.status_code != 200:
            print(f"[ERROR] Login failed. Status: {r.status_code}, Response: {r.text}")
            return False
        
        token_data = r.json()
        access_token = token_data.get("access_token")
        if not access_token:
            print(f"[ERROR] Login succeeded but no access token returned.")
            return False
            
        print(f"[SUCCESS] Logged in. Token received.")
        
        # 3. Fetch Profile
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        r = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if r.status_code != 200:
            print(f"[ERROR] Profile fetch failed. Status: {r.status_code}, Response: {r.text}")
            return False
            
        profile_data = r.json()
        print(f"[SUCCESS] Profile fetched: {profile_data}")
        
        print("--- E2E Test Passed Successfully! ---")
        return True
        
    except Exception as e:
        print(f"[FATAL] E2E script exception: {e}")
        return False

if __name__ == "__main__":
    time.sleep(1)
    test_e2e_flow()
