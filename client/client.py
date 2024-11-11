import socket
import os
import sys


def start_client(input_file_path, server_ip='127.0.0.1', port=8080):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, port))
    print("Connected to the server.")
    file = None
    try:
        file = open(input_file_path, "r")
    except Exception as e:
        print("Input File not found!")
        return
    for command in file:
        # command = input("Enter your command (e.g., 'client_get <file_path>' or 'client_post <file_path>'): ")

        parts = command.split()

        action = parts[0]
        if action.lower() == 'close':
            print("Closing connection.")
            request = "connection: close"
            # client.send(request.encode('utf-8'))
            break
        if len(parts) < 2:
            print("Invalid command")
            break

        file_path, host_name = parts[1:3]
        if len(parts) > 3:
            port_number = parts[3]
        # Prepare GET request
        if action.lower() == "client_get":
            request = f"GET {file_path} HTTP/1.1\r\nHost: {server_ip}\r\n\r\n"
            client.send(request.encode('utf-8'))

            # Receive response in chunks and handle larger files
            response = b""
            try:
                while True:
                    part = client.recv(4096)
                    response += part
                    if len(part) < 4096:  # No more data to receive
                        break
            except Exception as e:
                print("Connection closed by the server because of Time Out!")
                return
            # Separate headers and body
            header_end_index = response.find(b"\r\n\r\n")
            headers = response[:header_end_index].decode('utf-8')
            print(f"Received headers from server:\n{headers}")

            # Extract content type from headers
            content_type = None
            for line in headers.split("\r\n"):
                if line.lower().startswith("content-type:"):
                    content_type = line.split(":")[1].strip()

            # Check if the response is an HTTP 200 OK
            if "HTTP/1.1 200 OK" in headers:
                file_content = response[header_end_index + 4:]
                file_name = os.path.basename(file_path)

                # Save content based on file type
                if content_type and ("text" in content_type or "html" in content_type):
                    # Handle text or html file
                    with open(file_name, 'w', encoding='utf-8') as file:
                        file.write(file_content.decode('utf-8'))
                    print(f"Text content saved to {file_name}.")
                else:
                    # Binary file handling (e.g., images, PDFs)
                    with open(file_name, 'wb') as file:
                        file.write(file_content)
                    print(f"File saved to {file_name}.")
            else:
                print("File not found or server error.")
            print("_____________________________________________")

        elif action.lower() == "client_post":
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            try:
                with open(file_path, 'rb') as file:
                    file_data = file.read()
                file_name = os.path.basename(file_path)

                body_start = (
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\n"
                    f"Content-Type: application/octet-stream\r\n\r\n"
                ).encode('utf-8')

                body_end = f"\r\n--{boundary}--\r\n".encode('utf-8')
                content_length = len(body_start) + len(file_data) + len(body_end)

                headers = (
                    f"POST {file_path} HTTP/1.1\r\n"
                    f"Host: {server_ip}\r\n"
                    f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
                    f"Content-Length: {content_length}\r\n\r\n"
                ).encode('utf-8')

                client.send(headers + body_start + file_data + body_end )
                try:
                    response = client.recv(4096).decode('utf-8')
                    print(f"Received from server:\n{response}")
                    print("_____________________________________________")
                except Exception as e:
                    print("Connection closed by the server because of Time Out.")

            except FileNotFoundError:
                print(f"File {file_path} not found.")
            except Exception as e:
                print("Connection closed from the server because of Time Out.")
                return
        else:
            print("Invalid command. Use 'client_get', 'client_post', or 'close'.")
            print("_____________________________________________")
            continue

    client.close()


# Run the client
if __name__ == "__main__":
    file_path, host_name = sys.argv[1:3]
    port_number = 8080
    if len(sys.argv) > 3:
        port_number = int(sys.argv[3])
    try:
        start_client(file_path, host_name, port_number)
    except Exception as e:
        print("Server not found")
