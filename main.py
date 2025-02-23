import subprocess

# Start Other Scripts (Only If They Don't Run a Discord Bot)
subprocess.Popen(["python", "bot_status.py"])  # This can run separately
subprocess.Popen(["python", "commands.py"])  # This should NOT start a new bot instance
