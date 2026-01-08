import socket
import time

UR_IP = "172.17.0.2"
DASHBOARD_PORT = 29999

# Programs to run
PROGRAM1 = "/ursim/programs/test2.urp"
PROGRAM2 = "/ursim/programs/test.urp"

def send_cmd(sock, cmd):
    """Send a command to the dashboard server and print response."""
    print(f">>> {cmd}")
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.2)
    response = sock.recv(4096).decode()
    print(f"<<< {response.strip()}")
    return response

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((UR_IP, DASHBOARD_PORT))

    # Initial dashboard message
    print(sock.recv(1024).decode().strip())

    # Power on and release brakes
    send_cmd(sock, "power on")
    send_cmd(sock, "brake release")

    # Run first program
    send_cmd(sock, f"load {PROGRAM1}")
    send_cmd(sock, "play")

    # Wait 10 seconds
    time.sleep(10)

    # Stop first program
    send_cmd(sock, "stop")

    # Run second program
    send_cmd(sock, f"load {PROGRAM2}")
    send_cmd(sock, "play")

    sock.close()

if __name__ == "__main__":
    main()
