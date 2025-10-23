"""
webhook_server.py
Simple Flask server to handle Stripe webhooks alongside Streamlit.
"""

from flask import Flask, request, jsonify
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.webhook_handler import handle_stripe_webhook

app = Flask(__name__)

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    if handle_stripe_webhook(payload, sig_header):
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('WEBHOOK_PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=False)
