# Avatarify_modified

GOOGLE COLLAB SCRIPT

# Set up environment
!rm -rf /content/avatarify
!git clone https://github.com/alievk/avatarify.git /content/avatarify
%cd /content/avatarify

# Clone first-order-model into fomm directory
!git clone https://github.com/alievk/first-order-model.git fomm
!pip install face-alignment==1.0.0 msgpack_numpy pyyaml==6.0.1

# Run download_data.sh script
!bash /content/avatarify/scripts/download_data.sh

# Download ngrok
!bash /content/avatarify/scripts/get_ngrok.sh

# Import libraries for subprocess and tunneling
from subprocess import Popen, PIPE
import shlex
import json
import time

def run_with_pipe(command):
    commands = list(map(shlex.split, command.split("|")))
    ps = Popen(commands[0], stdout=PIPE, stderr=PIPE)
    for command in commands[1:]:
        ps = Popen(command, stdin=ps.stdout, stdout=PIPE, stderr=PIPE)
    return ps.stdout.readlines()

def get_tunnel_addresses():
    info = run_with_pipe("curl http://localhost:4040/api/tunnels")
    assert info, "Ngrok API did not return tunnel information."

    info = json.loads(info[0])
    for tunnel in info['tunnels']:
        url = tunnel['public_url']
        local_port = tunnel['config']['addr'].split(':')[-1]
        print(f"{url} -> {local_port} [{tunnel['name']}]")
        if tunnel['name'] == 'input':
            in_addr = url
        elif tunnel['name'] == 'output':
            out_addr = url
        else:
            print(f"Unknown tunnel: {tunnel['name']}")
    return in_addr, out_addr

# Ports for communication
local_in_port = 5557
local_out_port = 5558

# (Re)Start the worker
with open('/tmp/run.txt', 'w') as f:
    ps = Popen(
        shlex.split(f'./run.sh --is-worker --in-port {local_in_port} --out-port {local_out_port} --no-vcam --no-conda'),
        stdout=f, stderr=f)
    time.sleep(3)

# Check if the worker started successfully
!ps aux | grep 'python3 afy/cam_fomm.py' | grep -v grep | tee /tmp/ps_run
!if [[ $(cat /tmp/ps_run | wc -l) == "0" ]]; then echo "Worker failed to start"; cat /tmp/run.txt; else echo "Worker started"; fi

# Ngrok configuration
authtoken = [ngrok_token]
region = "eu"

config = f"""
version: 2
authtoken: {authtoken}
region: {region}
console_ui: False
tunnels:
  input:
    addr: {local_in_port}
    proto: tcp
  output:
    addr: {local_out_port}
    proto: tcp
"""

# Write ngrok configuration
with open('/content/avatarify/ngrok.conf', 'w') as f:
    f.write(config)

    %%writefile /content/avatarify/scripts/open_tunnel_ngrok.sh
#!/usr/bin/env bash

# Kill any existing ngrok processes
pkill ngrok 2> /dev/null

# Start ngrok with the specified configuration, detached from the current process
echo "Opening tunnel"
nohup ./ngrok start --all --config ngrok.conf > ngrok.log 2>&1 &


!chmod +x /content/avatarify/scripts/open_tunnel_ngrok.sh
!bash /content/avatarify/scripts/open_tunnel_ngrok.sh

# Ensure ngrok is running and check tunnel status
ps = Popen('./scripts/open_tunnel_ngrok.sh', stdout=PIPE, stderr=PIPE)
time.sleep(5)

# Fetch tunnel addresses with enhanced error handling
try:
    print("Attempting to get tunnel addresses...")
    in_addr, out_addr = get_tunnel_addresses()
    print("Tunnel opened")
except AssertionError:
    print("Ngrok tunnel did not start. Please check if ngrok is properly configured.")
except json.JSONDecodeError:
    print("Error decoding JSON from ngrok. The ngrok service might not be returning the expected response.")
except Exception as e:
    print(f"Unexpected error: {e}")
    [print(l.decode(), end='') for l in ps.stdout.readlines()]
    print("Something went wrong, reopen the tunnel.")

# Connection instructions
print('Copy-paste the appropriate command below and run it in your terminal:\n')
print(f'Mac:\n ./run_mac.sh --is-client --in-addr {in_addr} --out-addr {out_addr}')
print(f'Windows:\n ./run_windows.bat --is-client --in-addr {in_addr} --out-addr {out_addr}')
print(f'Linux:\n ./run.sh --is-client --in-addr {in_addr} --out-addr {out_addr}')
