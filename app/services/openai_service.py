from openai import OpenAI
import shelve
import os
import time
from dotenv import load_dotenv, set_key
import logging

# Load environment variables
load_dotenv()

# Load API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Get script's base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolve absolute path for the CSV file
FILE_PATH = os.path.join(BASE_DIR, "../../data/data.csv")

def upload_file(file_path):
    """Uploads a file and returns the file ID."""
    try:
        with open(file_path, "rb") as file:
            uploaded_file = client.files.create(file=file, purpose="assistants")  # ✅ Use "assistants" as purpose
        return uploaded_file.id
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logging.error(f"File upload failed: {e}")
        return None

def create_assistant(file_id):
    """Creates an assistant with file search enabled and attaches the file."""
    try:
        assistant = client.beta.assistants.create(
            name="WhatsApp Real Estate Assistant",
            instructions="You are a smart real estate chatbot that helps users find the best properties...",
            tools=[{"type": "file_search"}],  # ✅ Enable file search
            model="gpt-4o-mini",
            file_ids=[file_id] if file_id else []  # Attach file at the assistant level
        )
        return assistant.id
    except Exception as e:
        logging.error(f"Assistant creation failed: {e}")
        return None

# Initialize assistant
assistant_id = os.getenv("ASSISTANT_ID")
file_id = upload_file(FILE_PATH)

if not assistant_id and file_id:
    assistant_id = create_assistant(file_id)
    if assistant_id:
        set_key(".env", "ASSISTANT_ID", assistant_id)

def check_if_thread_exists(wa_id):
    """Checks if a thread exists for a given WhatsApp ID."""
    with shelve.open("threads_db") as db:
        return db.get(wa_id, None)

def store_thread(wa_id, thread_id):
    """Stores a thread ID for a given WhatsApp ID."""
    with shelve.open("threads_db", writeback=True) as db:
        db[wa_id] = thread_id

def run_assistant(thread_id, assistant_id):
    """Runs the assistant and returns the generated response."""
    try:
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        while run.status not in ["completed", "failed"]:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        if run.status == "failed":
            return "Sorry, the assistant run failed."

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        return messages.data[0].content[0].text.value
    except Exception as e:
        logging.error(f"Error running assistant: {e}")
        return "Sorry, I encountered an error."

def generate_response(message_body, wa_id, name, assistant_id):
    """Generates a response using the assistant and maintains threads."""
    try:
        thread_id = check_if_thread_exists(wa_id)

        if thread_id is None:
            thread = client.beta.threads.create()
            store_thread(wa_id, thread.id)
            thread_id = thread.id
        else:
            thread = client.beta.threads.retrieve(thread_id)

        # ✅ Send message without file_ids
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_body
        )
        
        return run_assistant(thread_id, assistant_id)
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return "Sorry, something went wrong."

if __name__ == "__main__":
    # Example usage
    response = generate_response("What are the check-in timings?", "wa_12345", "John", assistant_id)
    print("Assistant Response:", response)
