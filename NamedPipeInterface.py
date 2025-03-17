import os
import json
import requests
import time
import win32pipe, win32file

PIPE_NAME = r"\\.\pipe\GarbageDetectionPipe"

def process_local_image_with_schema(image_path):
    """
    Processes the provided image with the AI model.

    Args:
      image_path: The path to the local image to be processed.

    Returns:
      A dictionary containing Llava Model response or error.
    """
    try:
        with open(image_path, "rb") as image_file:
            image_blob = image_file.read()
    except FileNotFoundError:
        return {"error": f"File not found: {image_path}"}

    # Prepare the inputs based on the schema
    inputs = {
        "temperature": 0.7,
        "prompt": "Describe what is in the image. Then, conclude your response by classifying the scene as either 'HAS PILED WASTE DUMPED' or 'NO PILED WASTE DUMPED' in the following format: CLASSIFICATION: [HAS PILED WASTE DUMPED / NO PILED WASTE DUMPED]",
        "raw": False,
        "image": list(image_blob),
        "max_tokens": 512
    }

    xuraw = bytes.fromhex("68747470733a2f2f6170692e636c6f7564666c6172652e636f6d2f636c69656e742f76342f6163636f756e74732f34313961336530313666663231663966343132646362636437663731333239382f61692f72756e2f4063662f6c6c6176612d68662f6c6c6176612d312e352d37622d6866")
    raw = bytes.fromhex("366f317034754c5762713346676a57646f2d48446b7368617047724446546e71695a41464a425a79") 

    imageopx = raw.decode('utf-8')
    xu = xuraw.decode('utf-8')

    headers = {
        'Authorization': f'Bearer {imageopx}',
        'Content-Type': 'application/json'
    }

    # Send the POST request
    response = requests.post(xu, headers=headers, json=inputs)

    if response.status_code != 200:
        return {"error": f"Llava Model processing failed. Status code: {response.status_code}", "details": response.text}

    # Parse and return the response
    ai_response = response.json()
    return {"response": ai_response}

def named_pipe_server():
    """
    Keeps the named pipe open for continuous communication with other interfaces
    """
    print("Named Pipe Server Started. Waiting for connections...")
    
    while True:
        # Create a persistent named pipe server
        pipe = win32pipe.CreateNamedPipe(
            PIPE_NAME,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None)

        # Connect to the named pipe client (.Net Framework Provided)
        try:
            win32pipe.ConnectNamedPipe(pipe, None)  # Wait for client connection
            print("Client connected. Ready to receive image paths.")
        except Exception as e:
            print(f"Error connecting to named pipe: {e}")
            continue  # Restart the loop if connection fails

        while True:
            try:
                # Read data from Connected Interface
                data = win32file.ReadFile(pipe, 65536)[1]
                image_path = data.decode("utf-8").strip()

                # Remove BOM character if present (for clean image path)
                image_path = image_path.lstrip('\ufeff')

                if not image_path:
                    continue  # Ignore empty messages

                print(f"Received image path: {image_path}")

                # Process the image
                result = process_local_image_with_schema(image_path)

                # Convert response to JSON and send it back to Connected Interface
                response_str = json.dumps(result)
                win32file.WriteFile(pipe, response_str.encode("utf-8"))
                print("Response sent to Connected Interface.")
                
                # Break the inner loop to restart the connection
                break

            except Exception as e:
                print(f"Error processing the image or sending response: {e}")
                break  # Exit the inner loop on error

        # Close the pipe after each interaction
        try:
            win32pipe.DisconnectNamedPipe(pipe)
        except Exception as e:
            print(f"Error during pipe disconnection: {e}")
        finally:
            win32file.CloseHandle(pipe)
            print("Pipe closed. Waiting for the next connection...")

if __name__ == "__main__":
    named_pipe_server()
