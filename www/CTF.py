#!/usr/bin/python3
from email import message
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, send_from_directory
from flask import Flask, logging as flog
import logging
from OpenSSL import SSL
import string, random, requests
import sqlite3
import os.path
import json
import logging
from werkzeug.exceptions import HTTPException
import hashlib
from flask_session import Session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "CTF_DB.sqlite3")

domains = {
    "main": "https://vebmain.us.to",
    "cla": "https://vebcla.us.to",
    "ctf": "https://vebctf.us.to"
}

context = ("keys/app.crt","keys/app.key")

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = "9e7147a1fe85ef4d98ea8b3db08cef8851203c1e7ce94e39963b2808ab8dfe04"

connection = None
cursor = None

def connectDB():
    # create a database connection to a SQLite database
    global connection, cursor
    try:
        connection = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = connection.cursor()
        
        # cursor.execute("DROP TABLE IF EXISTS votings;")
        # [VOTINGID, VOTINGNAME, VOTINGDESC, ACTIVE]
        cursor.execute("""CREATE TABLE IF NOT EXISTS admin (
                            user_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            password TEXT NOT NULL
                        );""")
        # username = admin, password = Booth
        cursor.execute("""INSERT OR IGNORE INTO admin VALUES (1, "admin", "59a286a9bbb686814b08ffc09917162dd03cafd0f90982a7d37abbbd809a9e7e");""")
        
        # cursor.execute("DROP TABLE IF EXISTS votings;")
        # [VOTINGID, VOTINGNAME, VOTINGDESC, ACTIVE]
        cursor.execute("""CREATE TABLE IF NOT EXISTS votings (
                            voting_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            voting_name TEXT NOT NULL,
                            voting_description TEXT NOT NULL,
                            active INTEGER NOT NULL DEFAULT 1
                        );""")
        cursor.execute("""INSERT OR IGNORE INTO votings VALUES (1, "US President", "US President", 1);""")
        cursor.execute("""INSERT OR IGNORE INTO votings VALUES (2, "St. Mary President", "St. Mary President", 1);""")
        # cursor.execute("""DELETE FROM votings;""")
        
        # cursor.execute("DROP TABLE IF EXISTS candidates;")
        # [CANDIDATEID, CANDIDATEID, CANDIDATEVOTES, VOTINGID, ACTIVE]
        cursor.execute("""CREATE TABLE IF NOT EXISTS candidates (
                            candidate_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            candidate_name TEXT NOT NULL,
                            candidate_votes INTEGER NOT NULL,
                            voting_id INTEGER NOT NULL,
                            active INTEGER NOT NULL DEFAULT 1
                        );""")
        cursor.execute("""INSERT OR IGNORE INTO candidates VALUES (1, "Donald Trump", 0, 1, 1);""")
        cursor.execute("""INSERT OR IGNORE INTO candidates VALUES (2, "Joe Biden", 0, 1, 1);""")
        cursor.execute("""INSERT OR IGNORE INTO candidates VALUES (3, "Thomas Mengler", 0, 2, 1);""")
        cursor.execute("""INSERT OR IGNORE INTO candidates VALUES (4, "William Buhrman", 0, 2, 1);""")
        
        # cursor.execute("DROP TABLE IF EXISTS eligible_voters;")
        # [SECRET, VOTINGID]
        cursor.execute("""CREATE TABLE IF NOT EXISTS eligible_voters (
                            secret TEXT NOT NULL PRIMARY KEY,
                            voting_id INTEGER NOT NULL
                        );""")
        
        # cursor.execute("DROP TABLE IF EXISTS contributed_voters;")
        # [SSN, VOTINGID, CANDIDATEID]
        cursor.execute("""CREATE TABLE IF NOT EXISTS contributed_voters (
                            ssn TEXT NOT NULL,
                            voting_id INTEGER NOT NULL,
                            candidate_id INTEGER NOT NULL
                        );""")
        
        connection.commit()
        app.logger.info(cursor.lastrowid)
    except Exception as e:
        print(e)

@app.before_first_request
def before_first_request():
    app.logger.setLevel(logging.INFO)
    defaultFormatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    flog.default_handler.setFormatter(defaultFormatter)
    connectDB()

@app.route('/static/<path:path>')
def send_report(path):
    return send_from_directory('static', path)

@app.route("/admin")
def admin():
    # check if the users exist or not
    if not session.get("username"):
        # if not there in the session then redirect to the login page
        return redirect("/admin/login")
    return render_template("admin.html", domains=domains)

@app.route("/admin/login", methods=["POST", "GET"])
def login():
    # if form is submited
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?;", (username, password))
        voting = cursor.fetchone()
        app.logger.info(voting)
        if voting != None and len(voting) > 0:
            # record the user name
            session["username"] = request.form.get("username")
            # redirect to the main page
            return redirect("/admin")
        else:
            return render_template("admin.html", domains=domains, loginmessage="Wrong credentials!")
    return render_template("admin.html", domains=domains)

@app.route("/admin/logout")
def logout():
    session.pop('username', None)
    return redirect("/")

@app.route("/admin/addvoting", methods=["POST", "GET"])
def addvoting():
    # check if the users exist or not
    if not session.get("username"):
        # if not there in the session then redirect to the login page
        return redirect("/admin/login")
    
    if request.method == "GET":
        return render_template('admin.html', domains=domains, addvoting=True)
    else:
        app.logger.info(request.form)
        voting_name = request.form["voting_name"]
        voting_desc = request.form["voting_desc"]
        candidatesNum = int(request.form["candidates_number"])

        cursor.execute("INSERT INTO votings (voting_name, voting_description) VALUES (?, ?);", (voting_name, voting_desc))
        connection.commit()

        cursor.execute("SELECT * FROM votings WHERE voting_name = ? AND voting_description = ?;", (voting_name, voting_desc))
        voting = cursor.fetchone()
        if voting != None and len(voting) > 0:
            votingID = voting[0]
            app.logger.info(votingID)
            for i in range(1, candidatesNum+1):
                app.logger.info("candidate_name" + str(i))
                cursor.execute("INSERT INTO candidates (candidate_name, candidate_votes, voting_id) VALUES (?, 0, ?);", (request.form["candidate_name" + str(i)], votingID))
                app.logger.info("OK")
            connection.commit()
            app.logger.info("OK")
            return render_template('admin.html', domains=domains, addvoting=True, message="Election added")
        return render_template('admin.html', domains=domains, addvoting=True, message="Election NOT added")

@app.route("/")
def main():
    return render_template("CTF.html", domains=domains, votings=getVotings1())

@app.route("/voting/<id>")
def voting(id):
    cursor.execute("SELECT * FROM votings WHERE voting_id = ? AND active = 1;", (id, ))
    voting = cursor.fetchone()
    app.logger.info(voting)
    if voting != None and len(voting) > 0:
        cursor.execute("SELECT * FROM candidates WHERE voting_id = ? AND active = 1;", (id, ))
        candidates = cursor.fetchall()
        app.logger.info(candidates)
        if candidates != None and len(candidates) > 0:
            return render_template("CTF_voting.html", domains=domains, voting=voting, candidates=candidates)
        else:
            return render_template("CTF.html", domains=domains, votings=getVotings1())
    else:
        return render_template("CTF.html", domains=domains, votings=getVotings1())

@app.route("/results")
def show_results():
    return render_template("CTF_Results.html", domains=domains, votings=getVotings1())

@app.route("/results/<id>")
def display_results(id):
    cursor.execute("SELECT * FROM votings WHERE voting_id = ? AND active = 1;", (id, ))
    voting = cursor.fetchone()
    app.logger.info(voting)
    cursor.execute("SELECT * FROM candidates WHERE voting_id = ? AND active = 1;", (id, ))
    candidates = cursor.fetchall()
    app.logger.info(candidates)
    cursor.execute("SELECT * FROM contributed_voters WHERE voting_id = ?;", (id, ))
    contributed_voters = cursor.fetchall()
    app.logger.info(contributed_voters)
    if voting != None and len(voting) > 0 and candidates != None and len(candidates) > 0 :
        return render_template("CTF_Results.html", domains=domains, voting=voting, candidates=candidates, contributed_voters=contributed_voters)
    else:
        return render_template("CTF_Results.html", domains=domains, votings=getVotings1())

@app.route("/getvotings")
def getVotings():
    votings = []
    cursor.execute("SELECT * FROM votings WHERE active = 1;")
    result = cursor.fetchall()
    if result != None and len(result) > 0:
        for voting in result:
            votings.append({"voting_id": voting[0], "voting_name": voting[1], "voting_description": voting[2]})
    
    response = app.response_class(
        response=json.dumps(votings),
        status=200,
        mimetype='application/json'
    )
    return response

def getVotings1():
    votings = []
    cursor.execute("SELECT * FROM votings WHERE active = 1;")
    result = cursor.fetchall()
    if result != None and len(result) > 0:
        for voting in result:
            votings.append({"voting_id": voting[0], "voting_name": voting[1], "voting_description": voting[2]})
    return votings

@app.route("/confirmation", methods=["POST"])
def confirmation():
    app.logger.info("confirm")
    app.logger.info(request.form)
    app.logger.info(request.from_values)
    message = validate_voter(request.form["valid_num"], request.form["ssn"], request.form["votingid"], request.form["candidate_id"])
    if message:
        # request_voter_name(request.form["valid_num"])
        # render
        return render_template("CTF.html", domains=domains, votings=getVotings1(), message="Your vote has been counted")
    else:
        # render
        return render_template("CTF.html", domains=domains, votings=getVotings1(), message="Sorry, you are not eligable to vote !")

@app.route("/add", methods=["POST"])
def add():
    voting_id = request.form["voting_id"]
    valid_num = request.form["valid_num"]
    cursor.execute("INSERT INTO eligible_voters VALUES (?, ?);", (valid_num, voting_id))
    connection.commit()
    response = app.response_class(
        response=json.dumps([{"status": "OK"}]),
        status=200,
        mimetype='application/json'
    )
    return response

def notifyCLA(voting_id, valid_num):
    info = {"voting_id": voting_id, "valid_num": valid_num}
    requests.post(domains["cla"] + "/notify", data=info)

def validate_voter(valid_num, ssn, voting_id, candidate_id):
    if not valid_num or not ssn or not voting_id or not candidate_id:
        app.logger.info("OFF")
        return "Please fill all of the fields."
    
    cursor.execute("SELECT * FROM eligible_voters WHERE secret = ? AND voting_id = ?;", (valid_num, voting_id))
    result = cursor.fetchone()
    if result != None and len(result) > 0:
        # Vote AND DELETE
        cursor.execute("UPDATE candidates SET candidate_votes = candidate_votes + 1 WHERE candidate_id = ?;", (candidate_id, ))
        cursor.execute("DELETE FROM eligible_voters WHERE secret = ? AND voting_id = ?;", (valid_num, voting_id))
        cursor.execute("INSERT INTO contributed_voters VALUES (?, ?, ?);", (ssn, voting_id, candidate_id))
        connection.commit()
        notifyCLA(voting_id, valid_num)
        app.logger.info("TRUE")
        return True
    else:
        # NOT eliglible to vote
        app.logger.info("FALSE")
        return False

if __name__ == "__main__":
    connectDB()
    app.run(host="0.0.0.0", port=3000, threaded=True) #, ssl_context=context)
