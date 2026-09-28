import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor import SmishingPredictor
from explainability.shap_explainer import SmishingExplainer
from utils.safe_browsing import check_domain_status
from utils.encryption import decrypt_message, get_key_hex

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
CORS(app)

# Model checkpoint path - relative to smishing_detector root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_PATH = os.path.join(PROJECT_ROOT, "best_model.pt")

predictor = None
explainer = None

if os.path.exists(CHECKPOINT_PATH):
    try:
        predictor = SmishingPredictor(CHECKPOINT_PATH)
        explainer = SmishingExplainer(predictor)
    except Exception as e:
        print(f"Warning: Failed to load model: {e}")
        predictor = None
        explainer = None


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/check-domain', methods=['POST'])
def check_domain():
    """Check if a domain is legitimate using Google Safe Browsing API."""
    if not request.get_json() or 'domain' not in request.get_json():
        return jsonify({"error": "Missing 'domain' field"}), 400
    
    domain = request.get_json()['domain'].lower().strip()
    
    if not domain:
        return jsonify({"error": "Domain cannot be empty"}), 400
    
    try:
        status = check_domain_status(domain)
        return jsonify({
            "domain": domain,
            "is_legitimate": status == "known_safe",
            "is_malicious": status == "known_malicious",
            "status": status
        })
    except Exception as e:
        return jsonify({
            "error": f"Failed to check domain: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health():
    if predictor is None:
        return jsonify({
            "status": "error",
            "model": "SmishingDetector (DistilBERT + URL features)",
            "error": "Model checkpoint not found. Run train.py first."
        }), 503

    return jsonify({
        "status": "ok",
        "model": "SmishingDetector (XLM-RoBERTa · EN/HI/Hinglish)",
        "encryption": "AES-256-CBC"
    })


@app.route('/predict', methods=['POST'])
def predict():
    if predictor is None:
        return jsonify({
            "error": "Model checkpoint not found. Run train.py first."
        }), 503

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    message = data['message']
    result = predictor.predict(message)

    result['message'] = message

    return jsonify(result)


@app.route('/batch_predict', methods=['POST'])
def batch_predict():
    if predictor is None:
        return jsonify({
            "error": "Model checkpoint not found. Run train.py first."
        }), 503

    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({"error": "Missing 'messages' field"}), 400

    messages = data['messages']
    results = [predictor.predict(msg) for msg in messages]

    return jsonify({
        "results": results,
        "count": len(results)
    })


@app.route('/predict_secure', methods=['POST'])
def predict_secure():
    """
    Encrypted prediction endpoint for mobile app.
    Expects: { "message": "<AES-256-CBC base64 ciphertext>",
               "address": "<sender>" (optional) }
    Returns same shape as /predict but with encryption_used: true.
    """
    if predictor is None:
        return jsonify({"error": "Model not loaded."}), 503

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    try:
        plaintext = decrypt_message(data['message'])
    except Exception as e:
        return jsonify({"error": f"Decryption failed: {e}"}), 400

    result = predictor.predict(plaintext)
    result['message']          = plaintext
    result['encryption_used']  = True
    return jsonify(result)


@app.route('/api/encryption-key', methods=['GET'])
def encryption_key():
    """
    Returns the AES-256 key for the mobile app.
    Protected by X-App-Token header (set APP_TOKEN in .env).
    """
    expected = os.getenv('APP_TOKEN', 'scamshield-dev-token')
    if request.headers.get('X-App-Token') != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'key': get_key_hex(), 'algorithm': 'AES-256-CBC'})


@app.route('/explain', methods=['POST'])
def explain():
    if predictor is None or explainer is None:
        return jsonify({
            "error": "Model checkpoint not found. Run train.py first."
        }), 503

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    message = data['message']

    result = predictor.predict(message)

    try:
        explanation = explainer.explain_text(message, num_features=10)
    except Exception as e:
        return jsonify({
            "error": f"SHAP explanation failed: {str(e)}"
        }), 500

    return jsonify({
        "label": result['label'],
        "confidence": result['confidence'],
        "top_spam_words": explanation['top_spam_words'],
        "top_ham_words": explanation['top_ham_words'],
        "feature_importances": explanation['feature_importances']
    })


if __name__ == '__main__':
    host = os.getenv('SCAMSHIELD_HOST', '0.0.0.0')
    port = int(os.getenv('SCAMSHIELD_PORT', '5000'))
    debug = os.getenv('SCAMSHIELD_DEBUG', 'true').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug)
