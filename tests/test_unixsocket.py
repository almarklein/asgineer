import subprocess
import tempfile
import socket
import time
import os
from pathlib import Path

from common import get_backend

HTTP_REQUEST = (
    "GET / HTTP/1.1\r\n" + "Host: example.com\r\n" + "Connection: close\r\n\r\n"
)


def test_unixsocket():
    for backend_module in ["hypercorn", "uvicorn", "daphne"]:
        with tempfile.TemporaryDirectory() as temp_folder:
            socket_location = f"{temp_folder}/socket"
            main_location = f"{temp_folder}/main.py"
            project_location = Path(__file__).parent.parent.absolute()
            print(project_location)
            code_to_run = "\n".join(
                [
                    "# this allows us not to install asgineer and still import it",
                    "import importlib",
                    "import sys",
                    f"spec = importlib.util.spec_from_file_location('asgineer', '{project_location}/asgineer/__init__.py')",
                    "module = importlib.util.module_from_spec(spec)",
                    "sys.modules[spec.name] = module ",
                    "spec.loader.exec_module(module)",
                    "",
                    "import asgineer",
                    "@asgineer.to_asgi",
                    "async def main(request):",
                    '    return "Ok"',
                    "",
                    "if __name__ == '__main__':",
                    f"    asgineer.run(main, '{backend_module}', 'unix:{socket_location}')",
                ]
            )

            with open(main_location, "w") as file:
                file.write(code_to_run)

            process = subprocess.Popen(["python", main_location], cwd=project_location)

            time.sleep(1)

            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(socket_location)
                client.send(HTTP_REQUEST.encode())

                response = client.recv(1024).decode()

                if "200" not in response:
                    raise RuntimeError("Unexpected response")

            process.kill()
