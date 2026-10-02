import requests
import json

# --- CONFIGURATION ---
TUNNEL_URL = "http://localhost:5000"

# Endpoints mapped to your specific API structure
BATCH_PREDICT_URL = f"{TUNNEL_URL}/batch_predict"
EXPLAIN_URL = f"{TUNNEL_URL}/explain"
CHECK_DOMAIN_URL = f"{TUNNEL_URL}/check-domain"

# --- THE 15 INDIAN CONTEXT TEST CASES ---
TEST_CASES = [
    # English Cases
    {"text": "URGENT: Your Netflix account has been suspended due to a failed payment. Click here to update your billing details immediately and avoid service interruption: http://netflix-secure-login32.com", "expected": "scam", "lang": "English"},
    {"text": "Congratulations! You have been selected for a work-from-home job. Earn $500 a day just by liking YouTube videos. No experience needed. Contact us on Telegram: @EasyMoneyJobs", "expected": "scam", "lang": "English"},
    {"text": "Your OTP for logging into your Amazon account is 482019. It is valid for 5 minutes. Do not share this OTP with anyone for security reasons.", "expected": "ham", "lang": "English"},
    {"text": "Hi Neha, my company is hiring for remote software engineers (CTC up to 18 LPA). If you are interested, please upload your resume on our official portal here: https://careers.tcs.com/job-invite/10294/", "expected": "ham", "lang": "English"},
    {"text": "Your new HDFC Bank Credit Card ending in 4321 has been dispatched via Bluedart AWB No. 774920194. Track your delivery status here: https://www.bluedart.com/tracking.", "expected": "ham", "lang": "English"},

    # Hindi Cases
    {"text": "बधाई हो! आपको केबीसी (KBC) की तरफ से ₹25,00,000 की लॉटरी लगी है। अपना नकद इनाम पाने के लिए तुरंत इस व्हाट्सएप नंबर पर संपर्क करें: 98765-XXXXX।", "expected": "scam", "lang": "Hindi"},
    {"text": "महत्वपूर्ण सूचना: आपका बिजली बिल अपडेट न होने के कारण आज रात 9:30 बजे पावर काट दी जाएगी। अपनी लाइन चालू रखने के लिए तुरंत हमारे अधिकारी को 8920-XXXXXX पर कॉल करें।", "expected": "scam", "lang": "Hindi"},
    {"text": "प्रिय ग्राहक, आपके बैंक खाते (XXXX1234) में ₹15,000 की राशि क्रेडिट कर दी गई है। आपका वर्तमान बैलेंस ₹18,450 है। - एचडीएफसी बैंक", "expected": "ham", "lang": "Hindi"},
    {"text": "अमित, क्लाइंट मीटिंग का टाइम बदल गया है। कृपया पिछले महीने की सेल्स रिपोर्ट तुरंत अपडेट करें और नीचे दिए गए गूगल ड्राइव लिंक पर शीट शेयर करें: https://forms.gle/xyz123office", "expected": "ham", "lang": "Hindi"},
    {"text": "PM-KISAN योजना: आपकी 17वीं किस्त की ₹2,00,000 की राशि आपके आधार से जुड़े बैंक खाते में भेज दी गई है। भुगतान की स्थिति जांचें: https://pmkisan.gov.in", "expected": "ham", "lang": "Hindi"},

    # Hinglish Cases
    {"text": "Dear Customer, aapka Electricity bill update nahi hone ke karan aaj raat 9:30 baje aapki bijli kaat di jayegi. Turant is number par call karein aur bill pay karein: 888-XXX-XXXX.", "expected": "scam", "lang": "Hinglish"},
    {"text": "ALERT: Aapka Aadhaar card block ho gaya hai. Isko fir se activate karne ke liye niche diye gaye link par click karke apna PAN card details verify karein: http://govt-aadhaar-verify.in", "expected": "scam", "lang": "Hinglish"},
    {"text": "Bhai urgent hai, Sourav ko ₹15,000 bhej de abhi gpay se, uska hospital ka bill pay karna hai. Main tujhe shaam ko cash de dunga pakka. Bhej kar screenshot whatsapp kar de.", "expected": "ham", "lang": "Hinglish"},
    {"text": "Bhai rent ka paisa bhej de jaldi, owner ka phone aa raha hai baar baar. Agar aaj clear nahi kiya toh nikal dega wo. Is account pe gpay kar de: 99XXXXXX@okaxis", "expected": "ham", "lang": "Hinglish"},
    {"text": "Rahul, Amazon prime ka password change kiya hai kya? Mera login nahi ho raha hai yahan. Agar naya password hai toh please share kar de.", "expected": "ham", "lang": "Hinglish"}
]

def run_benchmark():
    print(f"📡 Connecting to Tunnel: {TUNNEL_URL} ...")

    # Extract string texts array for batch payload
    messages_payload = [case["text"] for case in TEST_CASES]

    try:
        # Hitting batch predict endpoint
        response = requests.post(
            BATCH_PREDICT_URL,
            json={"messages": messages_payload},
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        if response.status_code != 200:
            print(f"⚠️ API Error: Status code {response.status_code}")
            print(response.text)
            return

        res_data = response.json()

        # NOTE: Adjust key string parsing if your batch endpoint nests results differently
        # e.g., if response is {"predictions": ["scam", "ham", ...]}
        predictions = res_data.get("predictions", res_data.get("results", []))

        if not predictions or len(predictions) != len(TEST_CASES):
            print("⚠️ API unexpected array output size. Switching evaluation to iterative single predictions...")
            run_fallback_individual()
            return

        # Metrics Tracker
        passed_tests = 0
        total_tests = len(TEST_CASES)
        metrics = {"English": {"correct": 0, "total": 0}, "Hindi": {"correct": 0, "total": 0}, "Hinglish": {"correct": 0, "total": 0}}

        print("\n📝 --- TESTING RESULTS ---")
        for idx, (case, pred) in enumerate(zip(TEST_CASES, predictions), 1):
            if isinstance(pred, dict):
                ai_prediction = str(pred.get("label", "")).lower().strip()
                ai_confidence = pred.get("confidence", 0)
                ai_risk = pred.get("risk_level", "?")
            else:
                ai_prediction = str(pred).lower().strip()
                ai_confidence = 0
                ai_risk = "?"
            expected = case["expected"]
            if expected in ("scam", "spam"):
                is_correct = ai_prediction in ("spam", "scam")
            elif expected in ("ham", "safe"):
                is_correct = ai_prediction in ("ham", "safe")
            else:
                is_correct = ai_prediction == expected

            lang = case["lang"]
            metrics[lang]["total"] += 1

            if is_correct:
                passed_tests += 1
                metrics[lang]["correct"] += 1
                status = "✅ PASS"
            else:
                conf_str = f" [{ai_confidence:.1%}, {ai_risk}]" if ai_confidence else ""
                status = f"❌ FAIL (AI said: {ai_prediction.upper()}{conf_str} | Expected: {case['expected'].upper()})"

            print(f"[{idx}/{total_tests}] Lang: {lang.ljust(8)} | Status: {status}")
            if not is_correct:
                print(f"   ↳ Text snippet: \"{case['text'][:65]}...\"")

        # Scorecard Render
        print("\n" + "="*45)
        print(f"📊 AI PERFORMANCE SCORE: {passed_tests}/{total_tests} ({(passed_tests/total_tests)*100:.1f}%)")
        print("="*45)
        for lang, data in metrics.items():
            acc = (data["correct"] / data["total"]) * 100 if data["total"] > 0 else 0
            print(f"• {lang.ljust(8)} Accuracy: {data['correct']}/{data['total']} ({acc:.1f}%)")
        print("="*45)

    except requests.exceptions.RequestException as e:
        print(f"💥 Network Error: Could not talk to the backend tunnel system. Details:\n{e}")

def run_fallback_individual():
    """Alternative method using your single /predict endpoint if /batch_predict acts up"""
    PREDICT_URL = f"{TUNNEL_URL}/predict"
    passed_tests = 0
    for idx, case in enumerate(TEST_CASES, 1):
        try:
            r = requests.post(PREDICT_URL, json={"message": case["text"]}, timeout=5)
            pred = r.json().get("prediction", r.json().get("label", "unknown"))
            print(f"[{idx}] Individual Pred: {pred} | Expected: {case['expected']}")
        except Exception as e:
            print(f"Failed at row {idx}: {e}")

if __name__ == "__main__":
    run_benchmark()
