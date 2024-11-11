import socket
import threading
import os
import re
import sys

# Dynamic timeout settings
BASE_TIMEOUT = 30  # in seconds
MIN_TIMEOUT = 2
ACTIVE_CONNECTIONS = []


# Function to calculate dynamic timeout based on server load
def calculate_timeout():
    # Reduce timeout when active connections increase
    load_factor = len(ACTIVE_CONNECTIONS)
    return max(MIN_TIMEOUT, BASE_TIMEOUT - load_factor)


# Function to handle each client connection with persistent connection support
def handle_client(client_socket, address):
    ACTIVE_CONNECTIONS.append(client_socket)
    try:
        client_socket.settimeout(calculate_timeout())  # Set initial dynamic timeout
        while True:
            # Adjust timeout based on current load
            client_socket.settimeout(calculate_timeout())
            request = b""
            try:
                # Receive data in chunks to handle large requests
                while True:
                    part = client_socket.recv(4096)
                    if not part:
                        return  # Client closed the connection
                    request += part
                    if len(part) < 4096:
                        break
            except socket.timeout:
                # Close connection if timeout is reached
                response = "close"
                print(f"Connection timed out with {address}. Closing connection.")
                return
            print("Request received: ")
            decoded_request = request.decode('utf-8')
            formatted_request = decoded_request.replace('\r\n', '\n')
            print(formatted_request)
            print("___________________________________________________________________")
            try:
                request_lines = request.splitlines()
                method, path, _ = request_lines[0].decode('utf-8').split()
            except Exception as e:
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\nInvalid request format.")
                continue

            # Handle GET request
            if(path[0] == '/'):
                path = path[1:]
            if method == 'GET':
                if os.path.exists(path):
                    with open(path, 'rb') as file:
                        file_data = file.read()
                    response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(file_data)}\r\nConnection: keep-alive\r\n\r\n".encode('utf-8') + file_data
                else:
                    print("NO")
                    response = "HTTP/1.1 404 Not Found\r\nConnection: keep-alive\r\n\r\nFile not found.".encode('utf-8')

            # Handle POST request
            elif method == 'POST':
                header_body_split = request.split(b"\r\n\r\n", 1)
                headers = header_body_split[0].decode('utf-8')
                body = header_body_split[1] if len(header_body_split) > 1 else b""

                # Parse headers to check for Content-Type and boundary
                content_type = None
                boundary = None
                for line in headers.split("\r\n"):
                    if line.lower().startswith("content-type:"):
                        content_type = line.split(":")[1].strip()
                        if "multipart/form-data" in content_type:
                            boundary_match = re.search(r'boundary=(.*)', content_type)
                            if boundary_match:
                                boundary = boundary_match.group(1)

                if boundary:
                    # Process multipart/form-data
                    boundary_bytes = f"--{boundary}".encode('utf-8')
                    parts = body.split(boundary_bytes)

                    for part in parts:
                        if part == b'' or part == b'--\r\n':
                            continue

                        # Separate headers and content within each part
                        part_header_end = part.find(b"\r\n\r\n")
                        part_headers = part[:part_header_end].decode('utf-8')
                        part_content = part[part_header_end + 4:]

                        # Check if this part is the file based on Content-Disposition
                        if "Content-Disposition:" in part_headers:
                            disposition_match = re.search(r'filename="(.+)"', part_headers)
                            if disposition_match:
                                file_name = disposition_match.group(1)
                                # Save file content
                                with open(file_name, 'wb') as file:
                                    file.write(part_content)
                                response = "HTTP/1.1 200 OK\r\nConnection: keep-alive\r\n\r\nFile received.".encode('utf-8')
                                break
                else:
                    # Handle other media types by directly saving the body as binary
                    with open(path, 'wb') as file:
                        file.write(body)
                    response = "HTTP/1.1 200 OK\r\nConnection: keep-alive\r\n\r\nFile received.".encode('utf-8')

            else:
                response = "HTTP/1.1 400 Bad Request\r\nConnection: keep-alive\r\n\r\nUnknown command.".encode('utf-8')

            # Send the response to the client
            client_socket.sendall(response)

            # Check for 'Connection: close' header in request to determine if we should close the connection
            if b"Connection: close" in request:
                print(f"Closing persistent connection with {address}.")
                break  # Break the loop to close connection after response

    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        client_socket.close()
        ACTIVE_CONNECTIONS.remove(client_socket)
        print(f"Connection closed with {address}")


# Main server function
def start_server(port=8080):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    print(f"Server started on port {port}")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_handler.start()


# Run the server
if __name__ == "__main__":
    port_number = 8080
    try:
        port_number = int(sys.argv[1])
        try:
            start_server(port_number)
        except Exception as e:
            print(e)
            # print("This Port number is not available now, choose another")

    except Exception as e:
        print("Please add port Number")