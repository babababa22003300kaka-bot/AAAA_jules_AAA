"""
⚡ Requests Script (req.py)
- Reads 'session.json'
- Completes Apple Account Registration
- Handles Captcha, HashCash, Validation, SMS
"""
import json
import random
import string
import time
import names
import hashlib
import os
from datetime import datetime
from curl_cffi import requests

# --- Configuration ---
PHONE_NUMBER = f"112220{random.randint(1111, 9999)}"
COUNTRY_CODE = "EG"          # For Phone
COUNTRY_ISO3 = "EGY"         # For Address/Prime
COUNTRY_DIAL_CODE = "20"
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

# --- Helper Functions ---
def gen_email():
    name = names.get_first_name().lower()
    return f"{name}{random.randint(1111, 999999)}@gmail.com"

def gen_password():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%")
    rest = "".join(random.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(8))
    pwd_list = list(upper + lower + digit + special + rest)
    random.shuffle(pwd_list)
    return "".join(pwd_list)

def get_random_dob():
    return f"{random.randint(1990, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

def solve_captcha_2captcha(image_base64):
    """Solves Captcha using 2Captcha"""
    if not CAPTCHA_API_KEY:
        print("[!] CAPTCHA_API_KEY is not set in environment variables!")
        return None

    print("[-] Solving Captcha using 2Captcha...")
    url_in = "http://2captcha.com/in.php"
    url_res = "http://2captcha.com/res.php"
    data = {'key': CAPTCHA_API_KEY, 'method': 'base64', 'body': image_base64, 'json': 1}
    try:
        response = requests.post(url_in, data=data)
        if response.json().get('status') == 1:
            captcha_id = response.json().get('request')
            print(f"[+] Captcha ID: {captcha_id}")
            for _ in range(25):
                time.sleep(3)
                resp = requests.get(f"{url_res}?key={CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1")
                if resp.json().get('status') == 1:
                    print(f"[+] Captcha Solved: {resp.json().get('request')}")
                    return resp.json().get('request')
    except Exception as e:
        print(f"[!] Captcha Error: {e}")
    return None

def solve_hashcash(challenge, bits):
    version = 1
    now = datetime.now()
    date_str = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    prefix = f"{version}:{bits}:{date_str}:{challenge}::"

    print(f"[-] Solving HashCash (bits={bits})...")

    for _ in range(5):
        nonce = random.randint(0, 10000000)
        for i in range(100000):
            candidate = f"{prefix}{nonce + i}"
            hash_bytes = hashlib.sha256(candidate.encode()).digest()
            hash_int = int.from_bytes(hash_bytes, 'big')
            if (hash_int >> (256 - bits)) == 0:
                print(f"[+] HashCash Solved! Nonce: {nonce+i}")
                return candidate

    print("[!] HashCash failed - using fallback")
    return f"{prefix}0"

def complete_registration(session_data):
    """
    Uses session data from JSON to complete registration
    """
    print("\n" + "="*50)
    print("⚡ PHASE 2: Completing Registration with Requests")
    print("="*50)

    if not session_data.get('scnt') or not session_data.get('ssid'):
        print("[!] Missing scnt or ssid in session data! Cannot continue.")
        return False

    # Create Session
    session = requests.Session(impersonate="firefox")

    # Add Cookies
    for name, value in session_data['cookies'].items():
        session.cookies.set(name, value)
    print(f"[+] Loaded {len(session_data['cookies'])} cookies")

    # Generate Identity
    EMAIL = gen_email()
    PASSWORD = gen_password()
    FIRST_NAME = names.get_first_name()
    LAST_NAME = names.get_last_name()
    BIRTHDAY = get_random_dob()

    print(f"\n📧 Email: {EMAIL}")
    print(f"🔐 Password: {PASSWORD}")
    print(f"👤 Name: {FIRST_NAME} {LAST_NAME}")
    print(f"📅 Birthday: {BIRTHDAY}")
    print(f"📱 Phone: +{COUNTRY_DIAL_CODE} {PHONE_NUMBER}")

    # Headers
    common_headers = {
        "User-Agent": session_data['user_agent'],
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Origin": "https://appleid.apple.com",
        "Referer": "https://appleid.apple.com/",
        "X-Apple-I-Request-Context": "account",
        "X-Apple-I-TimeZone": "Africa/Cairo",
        "X-Apple-I-FD-Client-Info": session_data['fingerprint'],
        "X-Apple-Widget-Key": "af1139274f266b22b68c2a3e7ad932cb3c0bbe854e13a79af78dcc73136882c3",
        "scnt": session_data['scnt'],
        "X-Apple-ID-Session-Id": session_data['ssid']
    }

    time.sleep(random.uniform(1, 2))

    # --- Step 1: HashCash ---
    print("\n[-] 1. Getting HashCash challenge...")
    hc_headers = {
        'Host': 'appleid.apple.com',
        'User-Agent': session_data['user_agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://account.apple.com/',
    }
    params = {
        'roleType': 'Agent',
        'lv': '0.3.19',
        'widgetKey': 'af1139274f266b22b68c2a3e7ad932cb3c0bbe854e13a79af78dcc73136882c3',
        'v': '3',
        'appContext': 'account',
    }

    try:
        r_hc = session.get('https://appleid.apple.com/widget/account/', params=params, headers=hc_headers)
        challenge = r_hc.headers.get('X-Apple-HC-Challenge')
        bits = int(r_hc.headers.get('X-Apple-HC-Bits', '12'))

        if challenge:
            HASH_CASH = solve_hashcash(challenge, bits)
            print(f"[+] HashCash: {HASH_CASH[:30]}...")
        else:
            print("[!] No HashCash challenge received")
            HASH_CASH = None
    except Exception as e:
        print(f"[!] HashCash error: {e}")
        HASH_CASH = None

    time.sleep(random.uniform(1, 2))

    # --- Step 2: Captcha ---
    print("\n[-] 2. Getting Captcha...")
    r_cap = session.post("https://appleid.apple.com/captcha", headers=common_headers, json={"type": "IMAGE"})

    if 'scnt' in r_cap.headers:
        common_headers["scnt"] = r_cap.headers['scnt']
        print(f"[+] Rotated scnt: {common_headers['scnt'][:20]}...")

    cap_data = r_cap.json()
    if 'payload' not in cap_data:
        print("[!] Captcha payload missing!")
        return False

    captcha_answer = solve_captcha_2captcha(cap_data['payload']['content'])
    if not captcha_answer:
        print("[!] Failed to solve captcha!")
        return False

    time.sleep(random.uniform(1, 2))

    # --- Step 3: Prime Session ---
    print(f"\n[-] 3. Priming session for {COUNTRY_ISO3}...")
    prime_url = f"https://appleid.apple.com/account?countryCode={COUNTRY_ISO3}"
    r_prime = session.get(prime_url, headers=common_headers)
    print(f"[+] Prime Response: {r_prime.status_code}")

    if 'scnt' in r_prime.headers:
        common_headers["scnt"] = r_prime.headers['scnt']

    time.sleep(random.uniform(1, 2))

    # --- Step 4: Validate Email ---
    print("\n[-] 4. Validating Email...")
    r_val = session.post("https://appleid.apple.com/account/validation/appleid",
                         headers=common_headers, json={"emailAddress": EMAIL})
    print(f"[+] Email Validation: {r_val.status_code}")

    if 'scnt' in r_val.headers:
        common_headers["scnt"] = r_val.headers['scnt']

    time.sleep(random.uniform(1, 2))

    # --- Step 5: Validate Password ---
    print("\n[-] 5. Validating Password...")
    r_pwd = session.post("https://appleid.apple.com/account/validate/password",
                         headers=common_headers,
                         json={"accountName": EMAIL, "password": PASSWORD,
                               "firstName": FIRST_NAME, "lastName": LAST_NAME, "updating": False})
    print(f"[+] Password Validation: {r_pwd.status_code}")

    if 'scnt' in r_pwd.headers:
        common_headers["scnt"] = r_pwd.headers['scnt']

    time.sleep(random.uniform(1, 2))

    # --- Step 6: Full Account Validation ---
    print("\n[-] 6. Full Account Validation...")

    full_data = {
        "account": {
            "name": EMAIL,
            "password": PASSWORD,
            "person": {
                "birthday": BIRTHDAY,
                "name": {"firstName": FIRST_NAME.upper(), "lastName": LAST_NAME.upper()},
                "primaryAddress": {"country": COUNTRY_ISO3}
            },
            "preferences": {
                "marketingPreferences": {"appleNews": False, "appleUpdates": True, "iTunesUpdates": True},
                "preferredLanguage": "ar_SA"
            },
            "verificationInfo": {"answer": "", "id": ""}
        },
        "captcha": {
            "answer": captcha_answer,
            "id": cap_data.get('id'),
            "token": cap_data.get('token')
        },
        "phoneNumberVerification": {
            "mode": "sms",
            "phoneNumber": {
                "countryCode": COUNTRY_CODE,
                "countryDialCode": COUNTRY_DIAL_CODE,
                "id": 1,
                "nonFTEU": True,
                "number": PHONE_NUMBER
            }
        },
        "privacyPolicyChecked": True
    }

    validation_headers = common_headers.copy()
    if HASH_CASH:
        validation_headers["X-APPLE-HC"] = HASH_CASH

    r_full = session.post("https://appleid.apple.com/account/validate",
                          headers=validation_headers, json=full_data)
    print(f"[+] Full Validation Status: {r_full.status_code}")

    if r_full.status_code == 200:
        print("\n" + "="*50)
        print("✅ SUCCESS! Account Validated!")
        print("="*50)

        if 'scnt' in r_full.headers:
            common_headers["scnt"] = r_full.headers['scnt']

        # --- Step 7: Request SMS ---
        print("\n[-] 7. Requesting SMS...")
        phone_req_data = {
            "account": {"name": EMAIL, "person": {"name": {"firstName": FIRST_NAME.upper(), "lastName": LAST_NAME.upper()}}},
            "countryCode": COUNTRY_CODE,
            "phoneNumber": {"id": 1, "number": PHONE_NUMBER, "countryCode": COUNTRY_CODE, "countryDialCode": COUNTRY_DIAL_CODE},
            "mode": "sms"
        }

        r_sms = session.post("https://appleid.apple.com/account/verification",
                             headers=common_headers, json=phone_req_data)
        print(f"[+] SMS Request Status: {r_sms.status_code}")

        if r_sms.status_code == 200:
            print("\n📱 SMS Sent! Check your phone.")
            print(f"\n📧 Email: {EMAIL}")
            print(f"🔐 Password: {PASSWORD}")
            return True
        else:
            print(f"[!] SMS Failed: {r_sms.text[:200]}")
    else:
        print(f"\n[!] Validation Failed!")
        print(f"[!] Error: {r_full.text}")

    return False

if __name__ == "__main__":
    try:
        with open("session.json", "r") as f:
            session_data = json.load(f)
            complete_registration(session_data)
    except FileNotFoundError:
        print("[!] 'session.json' not found. Run br.py first!")
    except Exception as e:
        print(f"[!] Error: {e}")
