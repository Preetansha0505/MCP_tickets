# tckt_66

Small Python project demonstrating a simple client/server example and a small inspection utility.

## Contents
- `server.py` - Simple TCP/UDP server (see file for protocol and ports).
- `client.py` - Client to connect to `server.py` and exercise the protocol.
- `mini_inspector.py` - Lightweight utility to inspect or log messages exchanged between client and server.
- `notes.txt` - Project notes and quick reminders.
- `__pycache__/` - Compiled bytecode for the current Python interpreter.

## Requirements
- Python 3.13 (files were generated/byte-compiled with CPython 3.13). Compatible with Python 3.9+ in most environments.
- No external dependencies required (check files for any imports).

## Quick start
1. Start the server:
   python server.py
2. In another terminal, run the client:
   python client.py
3. Use `mini_inspector.py` to monitor messages or add logging:
   python mini_inspector.py

Adjust host/port and other settings directly in the scripts as needed.

## Notes
- Inspect `notes.txt` for developer comments and known limitations.
- Review code comments for protocol specifics and configuration options.

## License
No license specified. Add a LICENSE file if redistribution is intended.