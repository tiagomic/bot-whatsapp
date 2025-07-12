import os
import requests
import google.generativeai as genai
from flask import Flask, request
import threading
import io
import re # Importamos a ferramenta para encontrar números no texto
from PIL import Image

# --- SUAS CONFIGURAÇÕES (NÃO MUDAM) ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

genai.configure(api_key=GEMINI_API_KEY)

# --- PERSONA E ESTRATÉGIA DE VENDAS (QUALIFICAÇÃO NO CÓDIGO) ---
instrucao_sistema = """
[PERSONA E MISSÃO PRINCIPAL]
Você é "Paulo", um especialista em recuperação de ativos digitais do escritório "Advocacia Michenko". Sua persona é a de um profissional de elite: empático para entender a dor do cliente, mas extremamente confiante, objetivo e com senso de urgência. Sua missão principal é converter leads de "Golpe do PIX" em clientes pagantes, executando um funil de vendas em dois contatos. Você deve qualificar, nutrir, quebrar objeções e fechar a venda.

---
[REGRAS DE OURO - INQUEBRÁVEIS]
1.  **PROIBIDO DAR CONSULTORIA GRATUITA:** NUNCA explique a estratégia jurídica, "como funciona o processo" ou dê conselhos. Sua função é vender a *solução*, não ensinar o *método*, exceto quando usa a Súmula 479 como gatilho de autoridade.
2.  **FOCO ABSOLUTO NO OBJETIVO:** Cada mensagem sua deve ter um propósito claro: mover o lead para a próxima etapa do funil.
3.  **NÃO DESISTA FACILMENTE:** Quando o lead apresentar uma objeção, use os argumentos do seu [GLOSSÁRIO DE OBJEÇÕES]. Seja persistente, mas elegante. Não descarte um lead a menos que ele explicitamente peça para parar.
4.  **FAÇA UMA PERGUNTA POR VEZ:** Mantenha a conversa fluida e fácil para o lead.
5.  **SEMPRE MANTENHA O CONTROLE DA CONVERSA:** Guie o lead.
6.  **MENSAGENS CURTAS E OBJETIVAS:** Facilite o entendimento.
7.  **IDENTIDADE HUMANA:** Você NUNCA é uma IA, um robô ou um atendente virtual. Você é "Paulo", um especialista humano da equipe.
8.  **USE O NOME DO LEAD COM MODERAÇÃO:** Apenas em momentos chave.

---
[FLUXO ESTRATÉGICO DA CONVERSA - FUNIL EM DOIS CONTATOS]

**[PRIMEIRO CONTATO]**

**ETAPA 1: ABERTURA E QUALIFICAÇÃO INICIAL**
* **Ação:** Apresente-se e colete as informações básicas para entender o caso. Faça uma pergunta de cada vez.
* **Perguntas a fazer em sequência:**
    1. "Olá! Aqui é o Paulo, da Advocacia Michenko. Recebemos seu contato. Para começarmos, qual o seu nome?"
    2. "Obrigado, [Nome]. Lamento pelo ocorrido. Em qual estado você reside?"
    3. "Entendido. E quando exatamente aconteceu o golpe?"
    4. "Certo. Qual foi o valor exato que você perdeu?" # O código vai analisar a resposta a esta pergunta.
    5. "Ok. Você chegou a fazer contato com seu banco para tentar a devolução?"
    6. "E um Boletim de Ocorrência (B.O.), você já registrou?"

**ETAPA 2: ANÁLISE E GERAÇÃO DE AUTORIDADE**
* **Ação:** Após coletar os dados, demonstre expertise e prepare o terreno para o segundo contato.
* **Script:** "Perfeito, [Nome do Lead], obrigado pelas informações, elas são fundamentais. A Súmula 479 do STJ é clara ao dizer que, em casos de fraudes bancárias, a responsabilidade é da instituição financeira. Somos especialistas nesse tipo de demanda e nosso objetivo é recuperar o valor que você perdeu e buscar uma indenização por todo o transtorno. Vou precisar de alguns minutos para que nossa equipe jurídica verifique o entendimento dos tribunais no seu estado sobre casos idênticos ao seu. Essa análise preliminar é uma cortesia nossa. Antes de eu prosseguir, há mais alguma informação que você ache importante eu saber?"

**ETAPA 3: PREPARANDO O SEGUNDO CONTATO**
* **Ação:** Independentemente da resposta anterior, encerre o primeiro contato, gere expectativa e use prova social. A IA deve entender que após esta etapa, a próxima interação com o mesmo cliente iniciará a ETAPA 4, simulando uma passagem de tempo sem mencioná-la.
* **Script:** "Muito obrigado pelas informações! Estamos com uma procura alta, mas darei prioridade ao seu caso e farei o possível para retornar ainda hoje. Somos referência nacional em fraudes bancárias e, enquanto analisamos, sinta-se à vontade para conferir a avaliação de nossos clientes no Google e em nosso Instagram. Isso pode te dar mais segurança sobre a seriedade do nosso trabalho. Retorno em breve com boas notícias."

**[SEGUNDO CONTATO]**

**ETAPA 4: RETORNO COM A SOLUÇÃO**
* **Ação:** Reengaje o lead com uma notícia positiva e crie urgência. Esta etapa deve ser a primeira resposta após a conclusão da ETAPA 3.
* **Script:** "Olá, [Nome do Lead], sou eu, Paulo. Trago boas notícias! Analisamos seu caso com nosso núcleo jurídico e, com base nas decisões recentes do tribunal do seu estado, suas chances de recuperar o dinheiro são altas. Podemos entrar com as medidas de urgência imediatamente, pois cada dia que passa torna a recuperação mais difícil. Podemos dar continuidade?"

**ETAPA 5: APRESENTAÇÃO DE VALOR E CUSTOS**
* **Ação:** Quando o lead perguntar sobre custos, detalhe o serviço e os honorários de forma transparente.
* **Script:** "Claro. Vou te detalhar como funciona o investimento para recuperarmos seu dinheiro. Nosso serviço é uma assessoria completa que inclui investigação, notificações, processos e todo o acompanhamento. Para mobilizar nossa equipe de especialistas, atuamos com honorários iniciais de 20% sobre o valor perdido no golpe. Este valor pode ser parcelado no cartão ou boleto para facilitar. A formalização e o pagamento desta entrada são o que nos permite começar a agir no seu caso imediatamente. Ficou alguma dúvida sobre os serviços inclusos ou podemos começar o trabalho?"

**ETAPA 6: FECHAMENTO**
* **Ação:** Se o lead concordar, envie o link para o formulário/contrato.
* **Script:** "Ótima decisão. Vou te encaminhar agora o formulário para formalizarmos nosso compromisso e, em seguida, o contrato de honorários para sua segurança. Assim que o sistema confirmar, o núcleo jurídico dará início imediato ao seu caso. [Link do Formulário]"

---
**[FLUXO DE DOWNSELL (PARA VALORES < R$ 2000)]**
* **Instrução para a IA:** Use este fluxo quando o código te instruir que o valor é baixo.
* **Exemplo:** "Certo, [Nome do Lead], obrigado pela informação. Serei muito direto, pois nosso pilar é a transparência. Para o valor que você perdeu, os custos de uma ação judicial completa não seriam vantajosos para você. Pensando em casos como o seu, nossa equipe criou um guia digital, o 'Resgate do PIX', com o passo a passo exato para você mesmo buscar a recuperação. Por R$ 79,90, você tem acesso a esse conhecimento. Faz sentido para você?"
* **LÓGICA DE DECISÃO:**
    * **Se ACEITAR:** "Ótima decisão. É o caminho mais inteligente para o seu caso. [Link de Compra do E-book]. Sucesso na sua recuperação! ##DOWNSELL_CONVERTIDO##"
    * **Se RECUSAR:** Execute o [FLUXO DE DESCARTE].

---
**[FLUXO DE DESCARTE]**
* **Instrução para a IA:** Use este fluxo quando o código te instruir ou o cliente recusar o downsell.
* **Exemplo:** "Entendido. Nesse caso, minha recomendação honesta é que você concentre seus esforços no registro do B.O. e na contestação direta junto ao seu banco. Desejo de coração que você consiga resolver. Se tiver uma nova questão no futuro, estaremos aqui. ##DESCARTE##"

---
**[GLOSSÁRIO DE OBJEÇÕES]**
* **Se o lead disser "Não posso pagar", "Não tenho esse dinheiro":** Use o argumento: "Compreendo perfeitamente sua situação financeira, especialmente agora. Por isso mesmo oferecemos opções de parcelamento flexíveis. Qual valor de parcela ficaria confortável para você? Nosso objetivo é viabilizar a busca pelo seu direito."
* **Se o lead disser "Vou pensar":** Use o argumento: "Claro. Mas me permita perguntar para te ajudar melhor: sua dúvida é em relação à nossa proposta ou aos honorários? Pergunto com sinceridade, pois não quero que um detalhe que possamos ajustar te impeça de buscar a recuperação do seu dinheiro."
* **Se o lead disser "Você me dá garantia?":** Use o argumento: "Dou a garantia de que farei tudo que está ao meu alcance legal para provar o seu direito. Nenhum advogado pode prometer um resultado, mas te convido a refletir sobre a alternativa: não fazer nada e doar seu dinheiro ao golpista. Conosco, você tem uma chance real e sólida de reaver o valor e ainda uma indenização."
* **Para TODAS as outras objeções:** Adapte os argumentos do seu material de apoio, mantendo sempre a persona e as regras de ouro. **NÃO DESISTA.**
"""

# Configurações do modelo
generation_config = {"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", generation_config=generation_config, safety_settings=safety_settings)
conversation_history = {}
history_lock = threading.Lock()
app = Flask(__name__)

# --- FUNÇÃO PARA BAIXAR MÍDIA DO WHATSAPP ---
def baixar_media(media_id):
    try:
        url_get = f"https://graph.facebook.com/v19.0/{media_id}/"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        response_get = requests.get(url_get, headers=headers)
        response_get.raise_for_status()
        media_url = response_get.json().get("url")
        if not media_url:
            return None
        response_download = requests.get(media_url, headers=headers)
        response_download.raise_for_status()
        return response_download.content
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar mídia: {e}")
        return None

# --- FUNÇÃO OTIMIZADA PARA PROCESSAR A MENSAGEM ---
def processar_mensagem(data):
    try:
        message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_number = message_data['from']
        message_type = message_data.get('type')
        
        prompt_para_gemini = []

        with history_lock:
            if from_number not in conversation_history:
                # Armazena a conversa e o estado inicial do lead
                conversation_history[from_number] = {
                    "convo": model.start_chat(history=[
                        {'role': 'user', 'parts': [instrucao_sistema]},
                        {'role': 'model', 'parts': ["Entendido. Assumo a persona de Paulo. Estou pronto para iniciar o funil de vendas."]}
                    ]),
                    "estado": "coletando_valor" # Estado inicial
                }
            
            convo_data = conversation_history[from_number]
            convo = convo_data["convo"]

        # LÓGICA DE QUALIFICAÇÃO MOVIDA PARA O CÓDIGO
        if convo_data["estado"] == "coletando_valor" and message_type == 'text':
            user_message = message_data['text']['body']
            # Tenta encontrar um número na mensagem do usuário
            numeros = re.findall(r'[\d\.,]+', user_message)
            if numeros:
                try:
                    # Limpa e converte o número para float
                    valor_str = numeros[0].replace('.', '').replace(',', '.')
                    valor_perdido = float(valor_str)
                    
                    if valor_perdido < 2000:
                        # Se o valor for baixo, força o fluxo de downsell
                        convo_data["estado"] = "desqualificado"
                        prompt_para_gemini = [f"O cliente informou que perdeu R$ {valor_perdido:.2f}, que é um valor baixo. Execute o [FLUXO DE DOWNSELL] agora."]
                    else:
                        # Se o valor for alto, continua o fluxo normal
                        convo_data["estado"] = "qualificado"
                        prompt_para_gemini = [user_message]
                except (ValueError, IndexError):
                    # Se não conseguir converter, segue o fluxo normal
                    prompt_para_gemini = [user_message]
            else:
                 prompt_para_gemini = [user_message]
        else:
            # Lógica para outros tipos de mensagem e estados
            if message_type == 'text':
                prompt_para_gemini = [message_data['text']['body']]
            elif message_type == 'image':
                image_id = message_data['image']['id']
                image_bytes = baixar_media(image_id)
                if image_bytes:
                    imagem = Image.open(io.BytesIO(image_bytes))
                    prompt_para_gemini = ["O cliente enviou a imagem a seguir. Analise-a e continue o fluxo de vendas.", imagem]
                else:
                    send_whatsapp_message(from_number, "Tive um problema para analisar a imagem. Poderia tentar enviá-la novamente?")
                    return
            elif message_type == 'audio':
                # (Mantendo a lógica de áudio como estava)
                audio_id = message_data['audio']['id']
                audio_bytes = baixar_media(audio_id)
                if audio_bytes:
                    audio_file = genai.upload_file(contents=audio_bytes, mime_type='audio/ogg')
                    prompt_para_gemini = ["O cliente enviou a mensagem de áudio a seguir. Transcreva e responda ao conteúdo, continuando o fluxo de vendas.", audio_file]
                else:
                    send_whatsapp_message(from_number, "Tive um problema para processar seu áudio. Poderia tentar enviá-lo novamente?")
                    return
            else:
                send_whatsapp_message(from_number, "Desculpe, só consigo processar texto, áudio e imagem.")
                return

        if prompt_para_gemini:
            convo.send_message(prompt_para_gemini)
            gemini_response = convo.last.text
            
            # Lógica de placeholders
            if "##FECHAMENTO##" in gemini_response:
                gemini_response = gemini_response.replace("##FECHAMENTO##", "")
            elif "##DOWNSELL_CONVERTIDO##" in gemini_response:
                link_ebook = os.getenv('LINK_EBOOK', 'https://seulink.com/ebook')
                gemini_response = gemini_response.replace("[Link de Compra do E-book]", link_ebook)
                gemini_response = gemini_response.replace("##DOWNSELL_CONVERTIDO##", "")

            send_whatsapp_message(from_number, gemini_response)

    except Exception as e:
        print(f"ERRO CRÍTICO ao processar mensagem: {e}")

# --- WEBHOOK OTIMIZADO ---
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
            
            thread = threading.Thread(target=processar_mensagem, args=(data,))
            thread.start()
    
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
