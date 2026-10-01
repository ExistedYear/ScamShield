"""
manual_test.py — Comprehensive model testing across all categories.

Run with:
    cd smishing_detector && python manual_test.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predictor import SmishingPredictor

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model.pt")

# Format: (category, expected_label, message)
# expected_label: "spam" or "ham"
TEST_CASES = [

    # ── English SPAM (phishing) ───────────────────────────────────────────────
    ("EN-SPAM", "spam", "URGENT: Your bank account has been suspended. Click http://verify-bank.xyz/login to reactivate immediately."),
    ("EN-SPAM", "spam", "Congratulations! You've won a $10,000 Amazon gift card. Claim now: http://prize-claim.top/win?id=8821"),
    ("EN-SPAM", "spam", "Your package could not be delivered. Pay $2.99 customs fee at http://dhl-fee.net/track or it will be returned."),
    ("EN-SPAM", "spam", "HMRC: You have a tax refund of £842.50 pending. Claim at http://hmrc-refund.co/apply before it expires."),
    ("EN-SPAM", "spam", "Your Netflix account will be suspended. Update payment details: http://netflix-billing.info/update"),
    ("EN-SPAM", "spam", "Your SBI account is blocked due to KYC mismatch. Verify now: http://sbi-kyc-verify.net/update or lose access."),
    ("EN-SPAM", "spam", "CONGRATULATIONS! You have been selected as the lucky winner of our Rs.5,00,000 lottery. Call: 9800012345"),
    ("EN-SPAM", "spam", "Your PAN card has been deactivated. Reactivate at http://pan-reactivate.online/verify with your Aadhaar."),

    # ── English HAM (legit) ───────────────────────────────────────────────────
    ("EN-HAM", "ham", "Your Amazon order of Wireless Headphones has been shipped. Expected delivery: Friday, May 31."),
    ("EN-HAM", "ham", "HDFC Bank: Your a/c XX4521 credited Rs.25,000 on 30-May. Avl Bal: Rs.1,42,356. -HDFC Bank"),
    ("EN-HAM", "ham", "Your Airtel recharge of Rs.239 is successful. Validity: 28 days. Data: 1.5GB/day."),
    ("EN-HAM", "ham", "Your OTP for SBI net banking login is 847261. Valid for 10 minutes. Do not share with anyone."),
    ("EN-HAM", "ham", "Dear Customer, your IRCTC ticket PNR 4892731 for 31-May (New Delhi to Mumbai) is confirmed."),
    ("EN-HAM", "ham", "PhonePe: Rs.500 received from Rahul Kumar on 30-May at 3:45 PM. UPI Ref: 4893721019."),
    ("EN-HAM", "ham", "Flipkart: Your order #OD11234 has been delivered. Rate your experience at flipkart.com/orders"),
    ("EN-HAM", "ham", "Zepto: Your order of Milk, Eggs, Bread has been dispatched. Arriving in 10 minutes!"),

    # ── Hindi SPAM ────────────────────────────────────────────────────────────
    ("HI-SPAM", "spam", "प्रिय ग्राहक, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा। अभी कॉल करें: 9876543210"),
    ("HI-SPAM", "spam", "आपके खाते में कोई संदिग्ध गतिविधि देखी गई है। KYC अपडेट करें: http://sbi-kyc-update.xyz"),
    ("HI-SPAM", "spam", "आयकर विभाग: आपके खिलाफ FIR दर्ज होने वाली है। तत्काल संपर्क करें: 9911000000"),

    # ── Hinglish SPAM ─────────────────────────────────────────────────────────
    ("HL-SPAM", "spam", "Aapka electricity connection aaj raat 9:30 PM ko band ho jayega. Turant call karein: 98765XXXXX"),
    ("HL-SPAM", "spam", "Aapka SBI bank account suspend ho gaya hai. Abhi KYC kijiye nahi to permanently band ho jayega: http://sbi-kyc.xyz"),
    ("HL-SPAM", "spam", "Congratulations! Aapne 50,000 rupaye ka lucky draw jeeta hai. Claim karne ke liye call karein: 9000012345"),
    ("HL-SPAM", "spam", "CBI notice: Aapke naam pe money laundering case darj hua hai. Digital arrest se bachne ke liye turant contact karein officer ko."),
    ("HL-SPAM", "spam", "Aapka UPI ID expire ho raha hai. 2 ghante mein renew karein: http://upi-renew.club/verify"),
    ("HL-SPAM", "spam", "Income Tax Department: Aapke account mein suspicious transaction mili hai. FIR darj hogi. Abhi call karein: 9912345678"),
    ("HL-SPAM", "spam", "Aapka Aadhaar card block ho jayega 24 ghante mein. Update karein: http://uidai-update.xyz/verify"),

    # ── Legit Indian SMS (false-positive risk) ────────────────────────────────
    ("IN-HAM", "ham", "Dear Customer, your HDFC Bank a/c XX9821 credited Rs.12,500.00 on 30-May. Avl bal: Rs.87,432.10."),
    ("IN-HAM", "ham", "Airtel: Congratulations! Your mobile number is eligible for a free 5G SIM upgrade. Visit your nearest Airtel store."),
    ("IN-HAM", "ham", "IRCTC: OTP for your ticket booking is 739182. Valid for 5 minutes. Do NOT share with anyone."),
    ("IN-HAM", "ham", "Bijli Bill: Aapka MSEB bijli bill Rs.1,847 generate ho gaya hai. Due date: 10-Jun-26. Pay at mseb.co.in"),
    ("IN-HAM", "ham", "Paytm: Your order #ORD884521 of Rs.1,299 has been placed. Track at paytm.com/orders."),
    ("IN-HAM", "ham", "Jio: Your plan of Rs.299 has been renewed. 1.5GB/day for 28 days. Thanks for choosing Jio!"),

    # ── Adversarial / edge cases (no expected label — note in output only) ────
    ("EDGE", None, "Click here http://bit.ly/3xK9Lmn"),
    ("EDGE", None, "Call back on this number immediately: 9876543210"),
    ("EDGE", None, "Free Recharge! Get Rs.1000 talktime free. Limited offer. Reply YES to claim."),
    ("EDGE", None, "Dear Sir, your loan of Rs.5,00,000 at 8.5% p.a. is approved. Contact us to proceed."),
    ("EDGE", None, "Your SBI account is safe. No action needed. This is a test message from SBI fraud team."),

    # ── GREEN CHANNEL tests: promo/ad spam with legit URLs should NOT be "spam" ─
    # These are ads/promos (spammy language) but NOT scams
    ("GREEN", "safe", "Congratulations! You're eligible for a special cashback offer on Amazon. Shop now at amazon.in/offers"),
    ("GREEN", "safe", "Flipkart Big Billion Sale! Exclusive deals for you. Up to 80% off! Visit flipkart.com/sale"),
    ("GREEN", "safe", "WINNER! You've been selected for a special Netflix upgrade. Enjoy 3 months free at netflix.com/upgrade"),

    # These ARE scams — green channel must NOT clear them
    ("GN-SCAM", "spam", "WINNER! You've been selected for Rs.5,00,000 prize. Claim at http://prize-winner.xyz/claim"),
    ("GN-SCAM", "spam", "Your Netflix account will be suspended. Update payment details: http://netflix-billing.info/update"),
    ("GN-SCAM", "spam", "Amazon: Your account is locked. Verify immediately at http://amaz0n-verify.top/login"),
]


def run_tests():
    print(f"Loading model from {MODEL_PATH}...")
    predictor = SmishingPredictor(MODEL_PATH)
    print()

    stats = {"correct": 0, "total": 0, "by_cat": {}}

    header = f"{'Category':<10} {'Exp':<5} {'Got':<5} {'Conf':>6}  {'Risk':<8} {'Lang':<9} {'Status'}"
    print(header)
    print("─" * len(header))

    for category, expected, text in TEST_CASES:
        result    = predictor.predict(text)
        got_label = result["label"]
        conf      = result["confidence"]
        risk      = result.get("risk_level", "?")
        lang      = result.get("language", "?")

        if expected is None:
            status = "EDGE"
        else:
            # 'safe' (green channel) counts as correct when expected is 'ham' or 'safe'
            if expected in ("ham", "safe"):
                correct = got_label in ("ham", "safe")
            else:
                correct = got_label == expected
            status  = "\u2713" if correct else "\u2717 WRONG"
            cat_key = category.split("-")[0]
            stats["total"] += 1
            stats["correct"] += correct
            stats["by_cat"].setdefault(cat_key, [0, 0])
            stats["by_cat"][cat_key][0] += correct
            stats["by_cat"][cat_key][1] += 1

        exp_str = (expected or "?").upper()[:4]
        got_str = got_label.upper()[:4]
        gc = result.get("green_channel", False)
        gc_tag = " [GC]" if gc else ""
        print(f"{category:<10} {exp_str:<5} {got_str:<5} {conf:>6.1%}  {risk:<8} {lang:<9} {status}{gc_tag}")
        if status == "\u2717 WRONG":
            print(f"           \u21b3 {text[:90]}{'...' if len(text)>90 else ''}")

    print("─" * len(header))
    acc = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
    print(f"\nOverall: {stats['correct']}/{stats['total']} ({acc:.1f}%)\n")
    print("By category:")
    for cat, (ok, total) in sorted(stats["by_cat"].items()):
        pct = ok / total * 100
        bar = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
        print(f"  {cat:<6} [{bar}] {pct:5.1f}%  ({ok}/{total})")


if __name__ == "__main__":
    run_tests()
