import json
from api_request import send_api_request, get_family
from auth_helper import AuthInstance
from ui import pause

PACKAGE_FAMILY_CODE = "08a3b1e6-8e78-4e45-a540-b40f06871cfe"

def get_package_xut():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print("No active user tokens found.")
        pause()
        return None
    
    packages = []
    
    data = get_family(api_key, tokens, PACKAGE_FAMILY_CODE)
    package_variants = data["package_variants"]
    start_number = 1
    for variant in package_variants:
        for option in variant["package_options"]:
            friendly_name = option["name"]
            
            if friendly_name.lower() == "vidio":
                friendly_name = "Unli Turbo Vidio"
            if friendly_name.lower() == "iflix":
                friendly_name = "Unli Turbo Iflix"
                
            packages.append({
                "number": start_number,
                "name": friendly_name,
                "price": option["price"],
                "code": option["package_option_code"]
            })
            
            start_number += 1
    return packages