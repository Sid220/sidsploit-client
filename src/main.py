import argparse
import os
import sys
import subprocess
import json
import requests
import threading
import time
import urllib
import re
import signal
from timer import Timer

parser = argparse.ArgumentParser()

parser.add_argument('--host', type=str, required=True, help="Host of server (must have http or https protocol)")
parser.add_argument('--id', type=str, required=True, help="ID of exploit (find in web dashboard)")
parser.add_argument('--verbose', required=False, action='store_true', help="Generate verbose output")
parser.add_argument('--dont-clear-stdin', required=False, help="Don't clear Web STDIN on startup", action='store_true')
parser.add_argument('command', type=str, help="Command to run")

args = parser.parse_args()

output = ""


def write_and_push(val: str):
    global output
    sys.stdout.write(val)
    sys.stdout.flush()
    output += val


def push_log(key: str, value: str = None, client: bool = True, send_output: bool = True, testing: bool = False):
    global output

    log = f"[SIDSPLOIT {'CLIENT' if client else 'SERVER'}: {key}]{f': {value}' if value is not None else ''}\n"
    if args.verbose:
        sys.stdout.write(log)
        sys.stdout.flush()

    if send_output:
        output += log
        push_output(testing)


class Threads:
    @staticmethod
    def push_output():
        timer = Timer()
        wait = 1000
        while True:
            if timer.current_time > 1000:
                timer.reset()
                if output != '':
                    push_output()

            time.sleep(wait / 1000)
            timer.update_time(wait)

    @staticmethod
    def send_local_input():
        global output
        while process.poll() is None:
            input_string = sys.stdin.read(1)

            output += input_string

            # Send input_string to the process' stdin
            process.stdin.write(input_string)
            try:
                process.stdin.flush()
            except BrokenPipeError:
                push_log("UNABLE TO SEND DATA FROM REAL STDIN")
                break

            time.sleep(0.1)

    @staticmethod
    def get_input():
        while True:
            # Replace this with your own method to generate input string
            input_string = get_input_string()

            write_and_push(input_string)

            # Send input_string to the process' stdin
            process.stdin.write(input_string)
            try:
                process.stdin.flush()
            except BrokenPipeError:
                push_log("UNABLE TO SEND DATA FROM WEB STDIN")
                break

            # Sleep for 500ms before sending the next input
            time.sleep(0.5)


class UnexpectedSIDSIGException(Exception):
    pass


signals = {
    "SIGINT": {
        "type": "stdsig",
        "val": signal.SIGINT
    },
    "SIGTERM": {
        "type": "stdsig",
        "val": signal.SIGTERM
    },
    "SIGQUIT": {
        "type": "stdsig",
        "val": signal.SIGQUIT
    },
    "SIGKILL": {
        "type": "stdsig",
        "val": signal.SIGKILL
    },
    "\\n": {
        "type": "stdin",
        "val": "\n"
    },
    "\\t": {
        "type": "stdin",
        "val": "\t"
    }
}


def parse_signal(string):
    pattern = r"\[SIDSIG\](.*?)\[/SIDSIG\]"
    match = re.search(pattern, string)
    if match:
        data = match.group(1)
        if data in signals:
            sidsig = signals[data]
            if sidsig["type"] == "stdin":
                process.stdin.write(sidsig["val"])
                try:
                    process.stdin.flush()
                except BrokenPipeError:
                    push_log("UNABLE TO SEND DATA FROM WEB STDIN (SIDSIG)")
            elif sidsig["type"] == "stdsig":
                os.kill(process.pid, sidsig["val"])
            # Experimental
            elif sidsig["type"] == "EOF":
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    push_log("UNABLE TO SEND EOF FROM WEB STDIN")
            else:
                raise UnexpectedSIDSIGException("Unknown signal type")
            return None
        else:
            raise UnexpectedSIDSIGException("Unknown signal: " + data)
    else:
        return string


def get_input_string():
    x = requests.post(args.host + "/api/get_in.php?id=" + args.id)
    if x.status_code != 200:
        push_log("UNABLE TO GET WEB STDIN", f"UNKNOWN RESPONSE CODE {x.status_code}")
        return ""
    if x.content != b'':
        write_and_push("[SIDSPLOIT CLIENT: GOT WEB STDIN]")
        parsed = parse_signal(x.content.decode("utf-8"))
        return parsed if parsed is not None else ""
    return ""


def push_output(testing: bool = False):
    global output

    body = {"id": args.id, "output": urllib.parse.quote(output)}
    try:
        request = requests.post(args.host + "/api/post_out.php", data=body)
    except requests.exceptions.ConnectionError:
        if testing:
            print("Error: Unable to connect to server")
            sys.exit(1)
        else:
            print(
                f"[SIDSPLOIT CLIENT: FAILED TO SEND DATA TO SERVER!]: Couldn't connect")
            return
    if args.verbose:
        print("[SIDSPLOIT CLIENT: SENDING DATA]", flush=True)
    if request.status_code != 200:
        print(f"[SIDSPLOIT CLIENT: FAILED TO SEND DATA TO SERVER!]: INVALID STATUS CODE {request.status_code}",
              flush=True)
        if testing:
            sys.exit(1)
    try:
        response = json.loads(request.content)
        if 'success' not in response:
            print(
                f"[SIDSPLOIT CLIENT: FAILED TO SEND DATA TO SERVER!]: SUCCESS NOT IN STATUS CODE", flush=True)
            if testing:
                print(f"Error: {response['error']}")
                sys.exit(1)
    except json.decoder.JSONDecodeError:
        print(f"[SIDSPLOIT CLIENT: FAILED TO SEND DATA TO SERVER!]: INVALID JSON", flush=True)
        if testing:
            sys.exit(1)
    output = ""


push_log("SERVER INFO", "Host: " + args.host + " ID: " + args.id + " CMD: " + args.command, testing=True)

if not args.dont_clear_stdin:
    x = requests.post(args.host + "/api/get_in.php?id=" + args.id)
    if x.status_code != 200:
        push_log("UNABLE TO GET WEB STDIN", f"UNKNOWN RESPONSE CODE {x.status_code}")
        sys.exit(2)

process = subprocess.Popen(args.command.split(" "),
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           # TODO: Make STDERR actually output to STDERR
                           stderr=subprocess.STDOUT,
                           universal_newlines=True
                           )

input_thread = threading.Thread(target=Threads.get_input, daemon=True)
input_thread.start()

local_input_thread = threading.Thread(target=Threads.send_local_input, daemon=True)
local_input_thread.start()

send_thread = threading.Thread(target=Threads.push_output, daemon=True)
send_thread.start()

while process.poll() is None:
    if process.poll() is not None:
        break

    stdout = process.stdout.read(1)

    if stdout == '':
        break

    if stdout:
        write_and_push(stdout)

# Wait for the process to finish and get the return code
return_code = process.wait()
push_output()

push_log("COMMAND DONE")

process.poll()

push_log("COMMAND EXIT CODE", str(process.returncode))

sys.exit(0)
