import logging
from flask import current_app, jsonify
import json
import requests
import re
import os
from dotenv import load_dotenv

from app.services.openai_service import generate_response, file_id

load_dotenv()
assistant_id = os.getenv("ASSISTANT_ID")


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,  # Now sending to the dynamic sender ID
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    text = re.sub(r"\【.*?\】", "", text).strip()

    # Convert double asterisks (Markdown) to single asterisks (WhatsApp bold)
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)

    return text


def process_whatsapp_message(body):
    """
    Process incoming WhatsApp messages and send a response to the sender.
    """
    value = body["entry"][0]["changes"][0]["value"]
    
    if "messages" in value:
        wa_id = value["contacts"][0]["wa_id"]  # Get sender's WhatsApp ID
        name = value["contacts"][0]["profile"]["name"]
        message_body = value["messages"][0]["text"]["body"]

        # OpenAI Integration
        response = generate_response(message_body, wa_id, name, assistant_id)
        response = process_text_for_whatsapp(response)

        # Send message back to the sender (instead of RECIPIENT_WAID)
        data = get_text_message_input(wa_id, response)
        send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
