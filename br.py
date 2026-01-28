"""
🔥 Browser Script (br.py)
- Opens browser using SeleniumBase
- Extracts Fingerprint, Cookies, scnt, ssid
- Saves data to 'session.json'
"""
import json
import time
from seleniumbase import SB

# --- Configuration ---
HEADLESS = False  # Keep False to generate proper fingerprint

def extract_session_from_browser():
    """
    Opens browser and extracts:
    - X-Apple-I-FD-Client-Info (Fingerprint)
    - Cookies
    - scnt
    - X-Apple-ID-Session-Id
    """
    print("\n" + "="*50)
    print("🌐 PHASE 1: Browser Session Extraction")
    print("="*50)

    session_data = {
        'fingerprint': None,
        'cookies': {},
        'scnt': None,
        'ssid': None,
        'user_agent': None,
        'language': None,
        'timezone': None,
        'screen_width': None,
        'screen_height': None
    }

    with SB(uc=True, headless=HEADLESS) as sb:
        try:
            print("[-] Opening Apple Account page...")
            sb.uc_open_with_reconnect("https://account.apple.com/account", reconnect_time=4)
            sb.sleep(5)

            # Extract Browser Info
            info_script = """
            return {
                ua: navigator.userAgent,
                lang: navigator.language,
                tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
                w: screen.width,
                h: screen.height
            }
            """
            browser_info = sb.execute_script(info_script)
            session_data['user_agent'] = browser_info['ua']
            session_data['language'] = browser_info['lang']
            session_data['timezone'] = browser_info['tz']
            session_data['screen_width'] = browser_info['w']
            session_data['screen_height'] = browser_info['h']

            print(f"[+] User-Agent: {session_data['user_agent'][:50]}...")
            print(f"[+] Language: {session_data['language']}")
            print(f"[+] Timezone: {session_data['timezone']}")

            # Wait for iframe to load
            print("[-] Waiting for iframe to load...")
            sb.sleep(3)

            # Extract Cookies
            all_cookies = sb.get_cookies()
            for cookie in all_cookies:
                session_data['cookies'][cookie['name']] = cookie['value']
            print(f"[+] Extracted {len(session_data['cookies'])} cookies")

            # Extract Fingerprint with retries
            print("[-] Extracting fingerprint from page...")
            fingerprint_script = """
            try {
                if (window.__APPLE_CLIENT_INFO__) return JSON.stringify(window.__APPLE_CLIENT_INFO__);
                if (window.AppleIDAuthClientInfo) return JSON.stringify(window.AppleIDAuthClientInfo);
                return null;
            } catch(e) {
                return null;
            }
            """

            # Attempt to get fingerprint multiple times
            for _ in range(5):
                fp = sb.execute_script(fingerprint_script)
                if fp:
                    session_data['fingerprint'] = fp
                    print(f"[+] Found fingerprint in page context!")
                    break
                print("[-] Waiting for fingerprint generation...")
                sb.sleep(2)

            # Switch to iframe to ensure it's loaded
            iframe = "iframe#aid-create-widget-iFrame"
            if sb.is_element_visible(iframe):
                sb.switch_to_frame(iframe)
                print("[+] Switched to iframe")
                sb.sleep(2)

            # Extract cookies again
            all_cookies = sb.get_cookies()
            for cookie in all_cookies:
                session_data['cookies'][cookie['name']] = cookie['value']

            sb.switch_to_default_content()

            # XHR Request to get scnt and ssid
            print("[-] Making XHR request to get tokens...")
            xhr_script = """
            return new Promise((resolve, reject) => {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', 'https://appleid.apple.com/account/manage/gs/ws/token', true);
                xhr.setRequestHeader('Accept', 'application/json');
                xhr.setRequestHeader('X-Apple-I-Request-Context', 'ca');
                xhr.onload = function() {
                    resolve({
                        scnt: xhr.getResponseHeader('scnt'),
                        ssid: xhr.getResponseHeader('X-Apple-ID-Session-Id'),
                        status: xhr.status
                    });
                };
                xhr.onerror = function() {
                    reject('XHR failed');
                };
                xhr.send();
            });
            """

            try:
                result = sb.execute_async_script(xhr_script)
                if result:
                    session_data['scnt'] = result.get('scnt')
                    session_data['ssid'] = result.get('ssid')
                    print(f"[+] Got scnt: {session_data['scnt'][:20] if session_data['scnt'] else 'None'}...")
                    print(f"[+] Got ssid: {session_data['ssid'][:20] if session_data['ssid'] else 'None'}...")
            except Exception as e:
                print(f"[!] XHR Error: {e}")

            if not session_data['fingerprint']:
                print("[!] CRITICAL: Could not extract real fingerprint from browser!")
                print("[!] Stopping to avoid account ban.")
                return session_data

        except Exception as e:
            print(f"[!] Browser Error: {e}")
            import traceback
            traceback.print_exc()

    return session_data

if __name__ == "__main__":
    data = extract_session_from_browser()
    if data.get('fingerprint') and data.get('scnt'):
        with open("session.json", "w") as f:
            json.dump(data, f, indent=4)
        print("\n[✓] Session data saved to 'session.json'")
    else:
        print("\n[!] Failed to extract complete session data. JSON not saved.")
