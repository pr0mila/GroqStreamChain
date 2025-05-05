"""
Simple test script to verify Groq API functionality outside the WebSocket server.
Run this script to check if your API key and Groq setup are working correctly.
"""

import os
import sys
from dotenv import load_dotenv
from groq import Groq

def test_groq_api():
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment variables")
        return False
        
    # Initialize Groq client
    client = Groq(api_key=api_key)
    
    try:
        # Test with a simple prompt
        print("Sending test request to Groq API...")
        model = os.getenv("MODEL_NAME")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, can you hear me?"}
            ],
            temperature=0.7,
            max_tokens=100,
            stream=False
        )
        
        # Print the response
        response = completion.choices[0].message.content
        print(f"\nReceived response from Groq API:\n{response}\n")
        print("Groq API test successful!")
        return True
        
    except Exception as e:
        print(f"Error testing Groq API: {e}")
        return False

if __name__ == "__main__":
    success = test_groq_api()
    sys.exit(0 if success else 1)