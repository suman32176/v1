import os
from datetime import datetime
import json
import logging

# Log types
LOG_TYPE_GPT = "GPT"
LOG_TYPE_PEXEL = "PEXEL"

# log directory paths
DIRECTORY_LOG_GPT = ".logs/gpt_logs"
DIRECTORY_LOG_PEXEL = ".logs/pexel_logs"

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def log_response(log_type, query, response):
    try:
        log_entry = {
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        if log_type == LOG_TYPE_GPT:
            directory = DIRECTORY_LOG_GPT
        elif log_type == LOG_TYPE_PEXEL:
            directory = DIRECTORY_LOG_PEXEL
        else:
            logging.error(f"Invalid log type: {log_type}")
            return

        ensure_directory_exists(directory)
        filename = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_{log_type.lower()}.txt'
        filepath = os.path.join(directory, filename)

        with open(filepath, "w") as outfile:
            json.dump(log_entry, outfile, indent=2)
        logging.info(f"Log entry saved: {filepath}")
    except Exception as e:
        logging.error(f"Error logging response: {str(e)}")