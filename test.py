from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OPENAI_API_KEY =""
FACEBOOK_ACCESS_TOKEN = ""
FACEBOOK_PHONE_NUMBER_ID = ""

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge", "")
    
    data = request.json
    logging.info(f"Received webhook data: {data}")
    
    if "entry" in data:
        for entry in data["entry"]:
            for change in entry.get("changes", []):
                if change["field"] == "messages":
                    for message in change["value"].get("messages", []):
                        if "text" in message:
                            user_message = message["text"]["body"]
                            sender_id = message["from"]
                            logging.info(f"Received message from {sender_id}: {user_message}")
                            response = generate_response(user_message)
                            send_whatsapp_message(sender_id, response)
    return jsonify(success=True)

def generate_response(message_body):
    logging.info(f"Generating response for message: {message_body}")
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message_body},
        ]
    )
    generated_message = response.choices[0].message.content
    logging.info(f"Generated response: {generated_message}")
    return generated_message

def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v17.0/{FACEBOOK_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {FACEBOOK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }
    response = requests.post(url, json=data, headers=headers)
    logging.info(f"Sent message to {to}: {message} (Response: {response.text})")

if __name__ == "__main__":
    logging.info("Starting Flask server on port 8000...")
    app.run(port=8000, debug=True)



