from api_request import get_package, send_api_request
from ui import clear_screen, pause
import time
import json
from datetime import datetime



def enter_sentry_mode(api_key: str, tokens: dict):
    clear_screen()
    print("Entering Sentry Mode...")
    print("Press Ctrl+C to exit.")
    
    file_name = f"sentry_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    data = []
    
    in_sentry = True
    while in_sentry:
        time = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Fetch my packages