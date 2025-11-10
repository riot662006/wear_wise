import subprocess

frontend_cmd = "npm run dev --prefix frontend"
backend_cmd = "python backend/server.py"

# Use shell=True so Windows can find npm
frontend = subprocess.Popen(frontend_cmd, shell=True)
backend = subprocess.Popen(backend_cmd, shell=True)

try:
    frontend.wait()
    backend.wait()
except KeyboardInterrupt:
    frontend.terminate()
    backend.terminate()
