[Main](https://github.com/Sid220/sidsploit)
# Sidsploit Client
Sidsploit Client is the client for SidSploit. It is written in Python and currently only runs on Unix.

## Usage
```
usage: main.py [-h] --host HOST --id ID [--verbose] [--dont-clear-stdin] command

positional arguments:
  command             Command to run

options:
  -h, --help          show this help message and exit
  --host HOST         Host of server (must have http or https protocol)
  --id ID             ID of exploit (find in web dashboard)
  --verbose           Generate verbose output
  --dont-clear-stdin  Don't clear Web STDIN on startup

```