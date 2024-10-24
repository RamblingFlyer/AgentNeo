import os
import sys
import time
import logging
import subprocess
import socket
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def find_free_port(start_port=8000, max_port=8100):
    """Finds a free port between start_port and max_port."""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    return None


def is_port_free(port):
    """Checks if a port is free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False


def launch_dashboard(port=3005):
    """Launches the dashboard on a specified port."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "dashboard_server.py")

    if not os.path.exists(script_path):
        logging.error(f"Error: Dashboard server script not found at {script_path}")
        return

    # Find a free port starting from the specified port
    if not is_port_free(port):
        logging.info(f"Port {port} is busy. Finding an available port...")
        free_port = find_free_port(port + 1)
        if free_port is None:
            logging.error(f"No free ports available starting from {port}")
            return
        logging.info(f"Using port {free_port}")
    else:
        free_port = port

    # Start the dashboard server in a new detached subprocess
    command = [sys.executable, script_path, "--port", str(free_port)]

    try:
        if sys.platform == "win32":
            # Windows
            DETACHED_PROCESS = 0x00000008
            process = subprocess.Popen(
                command,
                creationflags=DETACHED_PROCESS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
        else:
            # Unix/Linux/Mac
            process = subprocess.Popen(
                command,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

        try:
            stdout, stderr = process.communicate(timeout=5)
            if process.returncode is not None:
                logging.error(
                    f"Dashboard failed to start. Return code: {process.returncode}"
                )
                logging.error(f"STDOUT: {stdout.decode('utf-8')}")
                logging.error(f"STDERR: {stderr.decode('utf-8')}")
                return
        except subprocess.TimeoutExpired:
            # Process is still running, which is good
            logging.info("Dashboard process started successfully")

        # Check if the server is responding
        max_retries = 5
        for _ in range(max_retries):
            try:
                response = requests.get(
                    f"http://localhost:{free_port}/health", timeout=1
                )
                if response.status_code == 200:
                    logging.info(
                        f"Dashboard launched successfully. Access it at: http://localhost:{free_port}"
                    )
                    return
            except requests.RequestException:
                time.sleep(1)

        logging.error(
            "Dashboard started but is not responding. It may have encountered an error."
        )
    except Exception as e:
        logging.error(f"Failed to launch dashboard: {e}", exc_info=True)
        return

    logging.info(
        f"Dashboard launch attempt completed. If successful, access it at: http://localhost:{free_port}"
    )


def close_dashboard(port=3005):
    """Closes the dashboard by sending a shutdown request."""
    try:
        response = requests.post(f"http://localhost:{port}/shutdown")
        if response.status_code == 200:
            logging.info("Dashboard closed successfully.")
        else:
            logging.warning("Failed to close the dashboard.")
    except Exception as e:
        logging.error(f"Error closing dashboard: {e}")
