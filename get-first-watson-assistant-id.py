from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import os
from dotenv import load_dotenv

def list_and_select_first_assistant(api_key):
    # Set up the authenticator
    authenticator = IAMAuthenticator(api_key)

    # Create the assistant object
    assistant = AssistantV2(
        version='2021-06-14',
        authenticator=authenticator
    )

    # Set the service URL (replace with your specific region if different)
    assistant.set_service_url('https://api.us-south.assistant.watson.cloud.ibm.com')

    try:
        # List the assistants
        response = assistant.list_assistants().get_result()
        
        if not response['assistants']:
            print("No assistants found.")
            return None

        print("Available Assistants:")
        for i, ass in enumerate(response['assistants'], 1):
            print(f"{i}. Name: {ass['name']}, ID: {ass['assistant_id']}")

        # Select the first assistant
        selected_assistant = response['assistants'][0]
        print(f"\nUsing the first assistant by default:")
        print(f"Name: {selected_assistant['name']}, ID: {selected_assistant['assistant_id']}")

        return selected_assistant

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# Usage example
if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv('IBMWATSON_API_KEY')
    selected_assistant = list_and_select_first_assistant(api_key)
    
    if selected_assistant:
        print(f"\nYou can now use this assistant ID for further operations: {selected_assistant['assistant_id']}")
    else:
        print("Failed to retrieve assistants. Check your API key and try again.")
