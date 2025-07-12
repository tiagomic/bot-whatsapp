import os
import requests
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# Configurações das APIs a partir das Variáveis de Ambiente
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

genai.configure(api_key=GEMINI_API_KEY)

# Instruções para o modelo Gemini
generation_config = {
  "temperature": 0.8,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# Endpoint para o Webhook do WhatsApp
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return "Verification token mismatch", 403
    
    data = request.get_json()
    if data and data.get('object'):
        if (data.get('entry') and
                data['entry'][0].get('changes') and
                data['entry'][0]['changes'][0].get('value') and
                data['entry'][0]['changes'][0]['value'].get('messages')):
            
            message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
            from_number = message_data['from']
            user_message = message_data['text']['body']

            # Inicia uma conversa com o Gemini
            convo = model.start_chat(history=[])
            convo.send_message(user_message)
            gemini_response = convo.last.text

            # Envia a resposta do Gemini de volta para o usuário
            send_whatsapp_message(from_number, gemini_response)

    return "OK", 200

def send_whatsapp_message(to_number, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": message}
    }
    try:
        requests.post(url, json=payload, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")

if __name__ == '__main__':
    app.run(debug=False)
