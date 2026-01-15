import socket
import time
import yaml
import json
import requests
import re
from typing import List, Dict
from file_watcher import SSHFileWatcher
import threading

REMOTE_FILE = "/home/ubuntu/ur_movement/output.json"

# ---------- LLM Agent ----------
class LLM_Agent:
    def __init__(self, llm_config):
        self.model_name = llm_config["model_name"]
        self.max_retries = llm_config.get("max_retries", 3)
        self.llm_url = llm_config["url"]
        self.system_prompt = llm_config["system_prompt"]
    
    def process_request(self, user_prompt: str, timeout: float = 15.0) -> List[Dict]:
        message = {
            "model": self.model_name,
            "prompt": self.system_prompt + "\n" + user_prompt,
            "stream": True
        }

        retry_count = 0
        while True:
            try:
                # For testing, you can use response_input instead of real request
                response_input = None
                if response_input is None:
                    # Stream response from LLM
                    with requests.post(self.llm_url, data=json.dumps(message), stream=True, timeout=timeout) as r:
                        collected_text = ""
                        for line in r.iter_lines(decode_unicode=True):
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if "response" in event:
                                collected_text += event["response"]
                            if event.get("done", False):
                                break
                    response = collected_text.strip()
                else:
                    response = response_input.strip()

                # Strip markdown formatting like ```json
                if response.startswith("```"):
                    response = re.sub(r"^```(?:json)?\s*", "", response)
                    response = re.sub(r"\s*```$", "", response)

                parsed_response = json.loads(response)

                if isinstance(parsed_response, dict):
                    parsed_response = [parsed_response]  # wrap single dict as list

                return parsed_response
            
            except (requests.RequestException, json.JSONDecodeError) as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    print(f"LLM request failed after {self.max_retries} retries: {e}")
                    return []
                print(f"LLM request failed (attempt {retry_count}), retrying...: {e}")
                time.sleep(2)
# ---------- UR Dashboard control loop ----------

#UR_IP = "172.17.0.2"
UR_IP = "192.168.1.3"
DASHBOARD_PORT = 29999

# Load YAML
with open("prompt.yaml", "r") as f:
    config = yaml.safe_load(f)

llm_agent = LLM_Agent(config["llm"])

def send_cmd(sock, cmd: str):
    print(f">>> {cmd}")
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.2)
    response = sock.recv(4096).decode().strip()
    print(f"<<< {response}")
    return response

def run_think_in_background(sock):
    thread = threading.Thread(target=execute_actions, args=(sock, [{"program": "think.urp"}]))
    thread.start()
    return thread

def execute_actions(sock, actions: List[Dict], programs_folder="/programs/interaction/"):
    # Execute each program
    for action in actions:
        program = action.get("program")
        if not program:
            continue

        # Wait for any currently running program to finish
        print("Checking if robot is currently running a program...")
        running_response = send_cmd(sock, "running")
        while "true" in running_response.lower():
            print("Robot is running, waiting for completion...")
            time.sleep(1)
            running_response = send_cmd(sock, "running")
        
        print(f"Robot is ready. Loading program: {program}")
        
        # Stop any residual state
        send_cmd(sock, "stop")
        time.sleep(0.3)
        
        # Load the program
        program_path = f"{programs_folder}/{program}"
        response = send_cmd(sock, f"load {program_path}")
        if "File not found" in response or "Loading program failed" in response:
            print(f"Program '{program_path}' not found. Skipping.")
            continue

        # Start the program
        print(f"Starting program: {program}")
        response = send_cmd(sock, "play")
        if "Failed to execute" in response or "Starting program failed" in response:
            print(f"Program '{program_path}' could not play. "
                  "Make sure the robot is in the correct start pose.")
            continue

        # Wait until program finishes
        time.sleep(0.5)  # Give the program time to start
        print("Waiting for program to complete...")
        running_response = send_cmd(sock, "running")
        check_count = 0
        while "true" in running_response.lower():
            time.sleep(0.5)
            running_response = send_cmd(sock, "running")
            check_count += 1
            if check_count % 10 == 0:  # Print progress every 5 seconds
                print(f"Program still running... ({check_count * 0.5:.1f}s elapsed)")
        
        print(f"Program '{program}' completed.")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((UR_IP, DASHBOARD_PORT))

    watcher = SSHFileWatcher(
    hostname="130.225.37.138",
    username="ubuntu",
    key_filename="/home/anders/Documents/LLM-Max.pem",
    poll_interval=2.0
)
    
    # Initial message
    print(sock.recv(1024).decode().strip())

    initial_content = None

    for path, content in watcher.watch_file(REMOTE_FILE):
        print(f"\nFile changed: {path}")

        if initial_content is None:
            initial_content = content
            print("Initial file read. Ignoring for first run.")
            continue

        if content == initial_content:
            continue

        initial_content = content  # update stored content

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
            continue

        # Example: JSON → instruction
        user_prompt = data.get("text")
        if not user_prompt:
            print("No instruction found in JSON")
            continue

        #think_thread = run_think_in_background(sock)

        actions = llm_agent.process_request(user_prompt)
        print("LLM returned actions:", actions)

        # Wait for think.urp to finish before LLM actions
        #think_thread.join()

        # Execute actions if any
        if actions:
            print("Executing actions:", actions)
            execute_actions(sock, actions)
        else:
            print("No actions returned from LLM")


    sock.close()

if __name__ == "__main__":
    main()
