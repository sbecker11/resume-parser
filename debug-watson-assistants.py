from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
import os
from dotenv import load_dotenv

def debug_watson_assistant_access(api_key):
    print(f"Attempting to access Watson Assistant with provided API key: {api_key[:5]}...{api_key[-5:]}")

    # Set up the authenticator
    authenticator = IAMAuthenticator(api_key)

    # Create the assistant object
    assistant = AssistantV2(
        version='2021-06-14',
        authenticator=authenticator
    )

    # Set the service URL (replace with your specific region if different)
    service_url = 'https://api.us-south.assistant.watson.cloud.ibm.com'
    assistant.set_service_url(service_url)
    print(f"Set service URL to: {service_url}")

    try:
        print("Attempting to list assistants...")
        response = assistant.list_assistants().get_result()
        
        print(f"Successfully retrieved assistants. Count: {len(response['assistants'])}")
        
        if not response['assistants']:
            print("No assistants found. This could be normal if you haven't created any assistants yet.")
            return None

        print("\nAvailable Assistants:")
        for i, ass in enumerate(response['assistants'], 1):
            print(f"{i}. Name: {ass['name']}, ID: {ass['assistant_id']}")

        # Select the first assistant
        selected_assistant = response['assistants'][0]
        print(f"\nUsing the first assistant by default:")
        print(f"Name: {selected_assistant['name']}, ID: {selected_assistant['assistant_id']}")

        return selected_assistant

    except ApiException as e:
        print(f"ApiException occurred. Status code: {e.code}")
        print(f"Error message: {e.message}")
        if e.code == 401:
            print("This could indicate an authentication issue. Please verify your API key and permissions.")
        elif e.code == 403:
            print("This could indicate a permissions issue. Please check your account's access to Watson Assistant.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None

# Usage example
if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv('IBMWATSON_API_KEY')

    selected_assistant = debug_watson_assistant_access(api_key)
    
    if selected_assistant:
        print(f"\nYou can now use this assistant ID for further operations: {selected_assistant['assistant_id']}")
    else:
        print("Failed to retrieve assistants. Please review the error messages above.")
