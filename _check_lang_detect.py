"""Quick test for is_english() heuristic in translation.py."""
import sys
sys.path.insert(0, "backend")

from app.services.translation import is_english

CASES = [
    # (text, expected_is_english, label)
    ("Hi mum, just confirming dinner at 7pm tonight at the usual restaurant. See you soon!", True, "Plain English"),
    ("This is PDRM. Your account is under investigation for money laundering. Transfer to safe account now.", True, "English scam"),
    ("Hi, this is your nephew. My phone is rosak, can you transfer RM2000 to this new account?", True, "Manglish (one Malay word)"),
    ("Ini Bank Negara. Akaun anda akan dibekukan. Sila berikan OTP sekarang untuk pengesahan, jangan beritahu sesiapa.", False, "Bahasa Malaysia"),
    ("我是警察,你的银行账户涉及洗钱案件,请立刻把钱转到安全账户,不要告诉任何人,否则马上抓你", False, "Mandarin"),
    ("Hello, this is Sergeant Michael from Bukit Aman.", True, "English w/ Malay place name"),
    ("Saya nak tanya tentang akaun bank anda.", False, "Short Bahasa"),
    ("", True, "Empty"),
    ("12345 67890", True, "Digits only"),
    ("It's me la bro! I need a favour urgently, can you lend me RM5,000?", True, "Manglish (la)"),
]

passed = 0
failed = 0
for text, expected, label in CASES:
    actual = is_english(text)
    ok = actual == expected
    icon = "PASS" if ok else "FAIL"
    snippet = (text[:60] + "...") if len(text) > 60 else text
    print(f"[{icon}] expected={expected} got={actual}  | {label}")
    print(f"        \"{snippet}\"")
    if ok:
        passed += 1
    else:
        failed += 1

print()
print(f"Passed {passed}/{passed + failed}")
sys.exit(0 if failed == 0 else 1)
