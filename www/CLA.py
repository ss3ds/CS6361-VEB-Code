#!/usr/bin/python3
from flask import Flask, render_template, request
from flask import Flask, logging as flog
import logging, json
import string, random, requests
import sqlite3
import os.path, traceback
# from OpenSSL import SSL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "CLA_DB.sqlite3")

domains = {
    "main": "https://vebmain.us.to",
    "cla": "https://vebcla.us.to",
    "ctf": "https://vebctf.us.to"
}

# SSL setup
# context = ("keys/cfa.crt","keys/cfa.key")

app = Flask(__name__)

connection = None
cursor = None

def connectDB():
    # create a database connection to a SQLite database
    global connection, cursor
    try:
        connection = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = connection.cursor()
        # cursor.execute("DROP TABLE IF EXISTS voters")
        # [SECRET, FIRST, LAST, SSN, VOTINGID, HAS_VOTED]
        cursor.execute("""CREATE TABLE IF NOT EXISTS voters (
                            secret NOT NULL PRIMARY KEY,
                            firstname TEXT NOT NULL,
                            lastname TEXT NOT NULL,
                            ssn TEXT NOT NULL,
                            votingid TEXT NOT NULL,
                            hasvoted INTEGER NOT NULL DEFAULT 0
                        );""")
        connection.commit()
    except Exception as e:
        print(e)

@app.before_first_request
def before_first_request():
    app.logger.setLevel(logging.INFO)
    defaultFormatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    flog.default_handler.setFormatter(defaultFormatter)
    connectDB()

def sendEligibleVoter(voting_id, valid_num):
    info = {"voting_id": voting_id, "valid_num": valid_num}
    req = requests.post(domains["ctf"] + "/add", data=info)
    app.logger.info(req.status_code)

# Generate RANDOM string (Secret)
def generateSecret(length):
    lst = [random.choice(string.ascii_letters + string.digits) for n in range(length)]
    rand = "".join(lst)
    return rand

def getVotings():
    try:
        req = requests.get(domains["ctf"] + "/getvotings")
        return req.json()
    except Exception as e:
        print(traceback.format_exc())
        return []

# VOTE
@app.route("/")
def main():
    # get all votings and pass it over to the form
    votings = getVotings()
    app.logger.info(votings)
    return render_template("CLA.html", domains=domains, votings=votings)

@app.route("/validation", methods=["POST"])
def validation():
    votings = getVotings()
    message = validate_voters(request.form["votingid"], request.form["first"], request.form["last"], request.form["ssn"])
    return render_template("CLA.html", domains=domains, votings=votings, message=message)

def validate_voters(votingID, first, last, SSN):
    # Verify all inputs are present
    if not first or not last or not SSN or not votingID:
        return "Please fill all of the fields."
    
    # Verify if the voter for specific votingID exists or not
    cursor.execute("SELECT * FROM voters WHERE firstname = ? and lastname = ? and ssn = ? and votingID = ?", (first, last, SSN, votingID))
    result = cursor.fetchall()
    app.logger.info(result)
    if len(result) == 0:
        secret = generateSecret(20)
        cursor.execute("INSERT INTO voters VALUES (?, ?, ?, ?, ?, ?)", (secret, first, last, SSN, votingID, 0))
        connection.commit()
        sendEligibleVoter(votingID, secret)
        return first + " " + last + ", your validation number is: [" + secret + "]. please, use it to vote"
    else:
        if result[0][5] == 1:
            return "You have already voted in this election"
        else:
            return "You have already registered for this election."

@app.route("/notify", methods=["POST"])
def add():
    voting_id = request.form["voting_id"]
    valid_num = request.form["valid_num"]
    cursor.execute("UPDATE voters SET hasvoted = 1 WHERE secret = ? AND votingID = ?;", (valid_num, voting_id))
    connection.commit()
    response = app.response_class(
        response=json.dumps([{"status": "OK"}]),
        status=200,
        mimetype='application/json'
    )
    return response

if __name__ == "__main__":
    connectDB()
    app.run(debug=True, host="0.0.0.0", port=2000, threaded=True) #, ssl_context=context)
