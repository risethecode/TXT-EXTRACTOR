from flask import Flask
import os
import threading
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 🚀"

def run_bot():
    subprocess.Popen(["python", "-m", "Extractor"])

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
