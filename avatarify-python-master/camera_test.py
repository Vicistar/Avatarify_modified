data = b""
while True:
    chunk = s.recv(1024)
    if not chunk:
        break
    data += chunk
print(f"Received all data: {data}")
