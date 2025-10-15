import sys
import os
import asyncio
import importlib.util
import subprocess
import time
import socket
import signal
import inspect as _inspect
import threading

# Start the real server (server.py located in parent folder)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_PY = os.path.join(ROOT, "server.py")
CLIENT_PY = os.path.join(ROOT, "client.py")

# set the inspector target URL here
INSPECTOR_URL = "http://127.0.0.1:8000/sse"

def wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except Exception:
                time.sleep(0.1)
    return False

# only load local client.py as module 'fastmcp' if explicitly requested
# set LOAD_LOCAL_CLIENT=1 to enable (default: use installed fastmcp package)
def load_client_as_fastmcp(client_path: str):
    spec = importlib.util.spec_from_file_location("fastmcp", client_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fastmcp"] = module
    spec.loader.exec_module(module)
    return module

def health_check_url(url: str, timeout: float = 2.0):
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "mcp-inspector/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.getheader("Content-Type")
            return resp.status, ct
    except Exception as e:
        return None, str(e)

async def run_inspector(url: str):
    # import the inspector after ensuring fastmcp is available in sys.modules
    import mini_inspector as inspector  # located in tests/

    main = getattr(inspector, "main", None)
    if not callable(main):
        raise RuntimeError("mini_inspector.main not found or not callable")

    # If main accepts an argument, pass the URL directly.
    try:
        sig = _inspect.signature(main)
        if len(sig.parameters) >= 1:
            await main(url)
            return
    except Exception:
        pass

    # Otherwise try setting common module-level names that mini_inspector might use.
    for name in ("INSPECTOR_URL", "INSPECTOR_BASE", "BASE_URL", "BASE", "base", "SSE_URL", "sse_url", "URL", "url"):
        try:
            setattr(inspector, name, url)
        except Exception:
            pass

    await main()

def _stream_proc_output(proc):
    if proc.stdout is None:
        return
    try:
        for raw in proc.stdout:
            try:
                line = raw.decode(errors="replace") if isinstance(raw, bytes) else raw
            except Exception:
                line = str(raw)
            print("[server]", line.rstrip())
    except Exception:
        pass

if __name__ == "__main__":
    server_proc = None
    try:
        # allow running with an already-running server (set SKIP_SERVER=1)
        skip_server = os.environ.get("SKIP_SERVER") in ("1", "true", "True")

        if not skip_server:
            print("Starting server subprocess:", SERVER_PY)
            # launch server.py as a subprocess and capture output so we can see errors
            server_proc = subprocess.Popen(
                [sys.executable, SERVER_PY],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )

            # start background thread to forward server logs to this console
            t = threading.Thread(target=_stream_proc_output, args=(server_proc,), daemon=True)
            t.start()

            # give subprocess a moment and check if it exited immediately
            time.sleep(0.5)
            if server_proc.poll() is not None:
                # process exited early — capture remaining output and show exit code
                print("Server subprocess exited early with code", server_proc.poll())
                try:
                    if server_proc.stdout:
                        remaining = server_proc.stdout.read().decode(errors="replace")
                        if remaining:
                            print("[server][early-output]", remaining.rstrip())
                except Exception:
                    pass
                raise SystemExit("Server failed to start — see output above")

        else:
            print("SKIP_SERVER set — assuming server already running")

        # wait until server accepts connections (assumes server listens on 127.0.0.1:8000)
        print("Waiting for server port 127.0.0.1:8000 ...")
        ready = wait_for_port("127.0.0.1", 8000, timeout=15.0)
        if not ready:
            print("Warning: server did not become ready on 127.0.0.1:8000 (continuing anyway)")
        else:
            print("Server port is open. Proceeding to load client and inspector.")

        # load real client implementation unless user explicitly asked to load local client.py
        if os.path.exists(CLIENT_PY) and os.environ.get("LOAD_LOCAL_CLIENT") in ("1", "true", "True"):
            print("Loading local client.py as fastmcp module (LOAD_LOCAL_CLIENT set):", CLIENT_PY)
            load_client_as_fastmcp(CLIENT_PY)
        else:
            if os.path.exists(CLIENT_PY):
                print("Found client.py but not loading it as fastmcp (to load set LOAD_LOCAL_CLIENT=1).")
            else:
                print("client.py not found at", CLIENT_PY)

        # quick health-check of the inspector URL so we see whether the server accepts connections
        status, info = health_check_url(INSPECTOR_URL, timeout=2.0)
        if status:
            print(f"Health-check OK: {INSPECTOR_URL} returned status={status}, content-type={info}")
        else:
            print(f"Health-check failed for {INSPECTOR_URL}: {info}")
            print("Inspector will still attempt to connect; if the server uses SSE it may accept then hold the connection open.")

        # run the inspector main (will connect to the running server). Pass URL constant.
        print("Running inspector with URL:", INSPECTOR_URL)
        asyncio.run(run_inspector(INSPECTOR_URL))

    finally:
        # terminate server process if we started it
        if server_proc:
            try:
                if server_proc.poll() is None:
                    print("Stopping server subprocess")
                    server_proc.terminate()
                    try:
                        server_proc.wait(timeout=2)
                    except Exception:
                        server_proc.kill()
            except Exception:
                pass