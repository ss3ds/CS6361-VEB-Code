#!/usr/bin/python3
from flask import Flask, render_template

domains = {
    "main": "https://vebmain.us.to",
    "cla": "https://vebcla.us.to",
    "ctf": "https://vebctf.us.to"
}

app = Flask(__name__)

@app.route("/")
def main():
    return render_template("index.html", domains=domains)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
