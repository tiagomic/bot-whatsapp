import os
import requests
from flask import Flask, request

# --- CONFIGURAÇÕES BÁSICAS ---
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

app = Flask(__name__)

# --- WEBHOOK SIMPLIFICADO ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # Código de verificação do Webhook (essencial para a Meta)
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return "Verification token mismatch", 403
    
    # Processa a mensagem recebida
    data = request.get_json()
    if data and data.get('object'):
        if (data.get('entry') and
                data['entry'][0].get('changes') and
                data['entry'][0]['changes'][0].get('value') and
                data['entry'][0]['changes'][0]['value'].get('messages')):
            
            message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
            from_number = message_data['from']
            
            # Envia uma resposta fixa
            send_whatsapp_message(from_number, "Robô em teste respondendo!")

    return "OK", 200

# --- FUNÇÃO DE ENVIO DE MENSAGEM ---
def send_whatsapp_message(to_number, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "text": {"body": message}}
    try:
        requests.post(url, json=payload, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")

if __name__ == '__main__':
    app.run(debug=False)
