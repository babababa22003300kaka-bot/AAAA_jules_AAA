"""
🔥 Browser Script (br.py) - CDP Interception + Trigger
===================================================
- Opens browser using SeleniumBase
- Uses Chrome DevTools Protocol (CDP) to monitor Network
- Triggers XHR to force header generation
- Captures REAL X-Apple-I-FD-Client-Info header
- Saves data to 'session.json'
"""
import json
import time
from seleniumbase import SB

# --- Configuration ---
HEADLESS = False

def extract_session_from_browser():
    print("\n" + "="*50)
    print("🌐 PHASE 1: Browser Session Extraction (CDP Method)")
    print("="*50)

    session_data = {
        'fingerprint': None,
        'cookies': {},
        'scnt': None,
        'ssid': None,
        'user_agent': None,
        'language': None,
        'timezone': None,
    }

    # Enable performance logs if supported by the driver environment
    # Note: We rely on standard UC initialization.
    with SB(uc=True, headless=HEADLESS) as sb:
        try:
            # Enable CDP Network domain to ensure traffic is tracked
            try:
                sb.driver.execute_cdp_cmd('Network.enable', {})
                print("[-] CDP Network Monitoring Enabled")
            except:
                print("[!] Warning: Could not enable CDP Network domain")

            print("[-] Opening Apple Account page...")
            sb.uc_open_with_reconnect("https://account.apple.com/account", reconnect_time=4)

            # Helper to check logs for the header
            def check_logs_for_fingerprint():
                try:
                    logs = sb.driver.get_log('performance')
                    for entry in logs:
                        try:
                            message = json.loads(entry['message'])['message']
                            if message['method'] == 'Network.requestWillBeSent':
                                headers = message['params']['request']['headers']
                                # Check for the fingerprint header (case-insensitive)
                                for key, value in headers.items():
                                    if key.lower() == 'x-apple-i-fd-client-info':
                                        return value
                                    if key.lower() == 'scnt':
                                        session_data['scnt'] = value
                                    if key.lower() == 'x-apple-id-session-id':
                                        session_data['ssid'] = value
                        except:
                            continue
                except Exception as e:
                    # performance logs might not be available
                    pass
                return None

            print("[-] Waiting for page to load...")
            sb.sleep(5)

            # --- Trigger Mechanism ---
            # We explicitly send a request. If Apple's fd.js is active,
            # it should inject the header into this request.
            print("[-] Triggering XHR to force fingerprint header...")
            trigger_script = """
            var xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://appleid.apple.com/account/manage/gs/ws/token', true);
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.setRequestHeader('X-Apple-I-Request-Context', 'ca');
            xhr.send();
            """
            sb.execute_script(trigger_script)

            # Loop to check for fingerprint
            print("[-] Monitoring network logs for fingerprint...")
            start_time = time.time()
            while time.time() - start_time < 15: # 15 seconds wait
                # 1. Check CDP/Performance Logs
                fp = check_logs_for_fingerprint()
                if fp:
                    session_data['fingerprint'] = fp
                    print(f"[+] ✅ Captured REAL fingerprint from Network Logs!")
                    break

                # 2. Check Global Variables (Backup)
                try:
                    fp_script = """
                    try {
                        if (window.__APPLE_CLIENT_INFO__) return JSON.stringify(window.__APPLE_CLIENT_INFO__);
                        if (window.AppleIDAuthClientInfo) return JSON.stringify(window.AppleIDAuthClientInfo);
                        return null;
                    } catch(e) { return null; }
                    """
                    fp_val = sb.execute_script(fp_script)
                    if fp_val:
                        session_data['fingerprint'] = fp_val
                        print(f"[+] ✅ Captured fingerprint from Window Object!")
                        break
                except:
                    pass

                time.sleep(1)

                # Retry trigger if needed
                if time.time() - start_time > 8 and not session_data['fingerprint']:
                    print("[-] Re-triggering XHR...")
                    sb.execute_script(trigger_script)

            # Extract Browser Info (Static)
            info_script = """
            return {
                ua: navigator.userAgent,
                lang: navigator.language,
                tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }
            """
            browser_info = sb.execute_script(info_script)
            session_data['user_agent'] = browser_info['ua']
            session_data['language'] = browser_info['lang']
            session_data['timezone'] = browser_info['tz']

            # Extract Cookies
            all_cookies = sb.get_cookies()
            for cookie in all_cookies:
                session_data['cookies'][cookie['name']] = cookie['value']

            # If scnt/ssid missed from logs, get them via XHR fallback
            if not session_data['scnt'] or not session_data['ssid']:
                print("[-] Fetching tokens via XHR fallback...")
                xhr_script_sync = """
                var xhr = new XMLHttpRequest();
                xhr.open('GET', 'https://appleid.apple.com/account/manage/gs/ws/token', false);
                xhr.setRequestHeader('Accept', 'application/json');
                xhr.send();
                return {
                    scnt: xhr.getResponseHeader('scnt'),
                    ssid: xhr.getResponseHeader('X-Apple-ID-Session-Id')
                };
                """
                result = sb.execute_script(xhr_script_sync)
                if result:
                    session_data['scnt'] = session_data['scnt'] or result.get('scnt')
                    session_data['ssid'] = session_data['ssid'] or result.get('ssid')

        except Exception as e:
            print(f"[!] Browser Error: {e}")
            import traceback
            traceback.print_exc()

    return session_data

if __name__ == "__main__":
    data = extract_session_from_browser()

    has_fingerprint = bool(data.get('fingerprint'))
    has_scnt = bool(data.get('scnt'))
    has_ssid = bool(data.get('ssid'))

    print("\n" + "="*50)
    if has_fingerprint and has_scnt and has_ssid:
        with open("session.json", "w") as f:
            json.dump(data, f, indent=4)
        print("[✓] ✅ Complete session saved to 'session.json'")
        print("="*50)
        print(f"  Fingerprint: ✅ REAL")
        print(f"  scnt:        ✓")
        print(f"  ssid:        ✓")
        print(f"  Cookies:     {len(data.get('cookies', {}))}")
        print("\n[*] 🚀 Now run IMMEDIATELY: python req.py")
    else:
        with open("session.json", "w") as f:
            json.dump(data, f, indent=4)
        print("[!] ⚠️ Partial/Failed session saved")
        print("="*50)
        print(f"  Fingerprint: {'✅ REAL' if has_fingerprint else '❌ NOT FOUND'}")
        print(f"  scnt:        {'✓' if has_scnt else 'MISSING'}")
        print(f"  ssid:        {'✓' if has_ssid else 'MISSING'}")
        print("\n[!] ⚠️ Do not run req.py until fingerprint is found.")
