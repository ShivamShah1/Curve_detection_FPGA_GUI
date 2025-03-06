import socket

# Main client code
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 12345))

try:
    while True:
        user_input = input('Enter "s" to request data: ')
        if user_input == 's':
            client.send(user_input.encode('utf-8'))
            response = b''

            # Receiving the large data in chunks
            while True:
                chunk = client.recv(1024)
                if not chunk:
                    break
                response += chunk

            print(f'[Client] Received {len(response)} bytes of data.')

        if user_input == 'e':
            print('[Client] App exit')

            break


except KeyboardInterrupt:
    print('\n[Client] Connection closed by user.')

client.close()
