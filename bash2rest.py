### Bash2REST
# Lets you execute bash scripts located in /scripts with an REST interface.
# Does some basic escape character removal, but only trust it from internal source.
#
# Name the script with the request method first: <METHOD>_<SCRIPT>.sh
# Ex: GET_test.sh
#
# You can use directories:
# /scripts/users/PUT_create.sh
#
# Contains some example scripts:
# POST_example.sh - plain old helloworld that prints the input parameter
# POST_env.sh - prints the environment variables that was set when the script runs
# POST_jq.sh - example of using jq to parse JSON input
# GET_counter.sh - counting to 10 with 1s sleep in each step.
#               shows how the streaming log output works
#
# Execute script:
# $ curl http://127.0.0.1:5000/example -d '{"args": "some_parameter"}'
# Hello, World. You sent in: some_parameter
#
# Add extra environment variables, will be prepended with REST_:
# $ curl http://127.0.0.1:5000/env -d '{"args": "", "key":"value"}'
# REST_KEY=value
# PWD=/Users/larlar/Projects/bash2rest
# SHLVL=1
# _=/usr/bin/env
#
# Using jq (http://stedolan.github.io/jq/) to parse JSON input:
# $ curl http://127.0.0.1:5000/jq -d '{"args": "", "key":"value"}'
# {
#   "key": "value",
#   "args": ""
# }
#
# //Lars Larsson
#
import os
import sys
import time
import json
from flask import Flask, request, Response
import subprocess
import multiprocessing

REMOVE_CHARS = ";&`'!\"|<>"
LOGDIR = "./logs"
SCRIPTDIR = "./scripts"

app = Flask(__name__)

class ParseError(Exception):
    pass

@app.route("/", methods=['GET', 'POST', 'PUT', 'DELETE'])
def index():
    return execute("")

@app.route("/<path:path>", methods=['GET', 'POST', 'PUT', 'DELETE'])
def execute(path):
    def run(cmd, env, logfile):
        with open(logfile, 'wb') as log:
            log.write("Output from %s\n" % ' '.join(cmd))
            log.write("Adding to environment:\n%s\n" % env)
            log.write("###START###\n")
            log.flush()
            p = subprocess.Popen(cmd, env=env, cwd=SCRIPTDIR, stdout=log, stderr=subprocess.STDOUT)
            p.wait()
            log.write("###STOP###\n")
        os._exit(os.EX_OK)

    def tail(logfile):
        with open(logfile, 'r') as log:
            start = False
            while True:
                line = log.readline()
                if line:
                    if line == "###STOP###\n":
                        return
                    if start:
                        yield line
                    if line == "###START###\n":
                        start = True
                else:
                    time.sleep(0.01)

    method = request.method
    base = os.path.dirname(path)
    script = os.path.basename(path)

    if method == "GET":
        data = {}
    else:
        try:
            data = json.loads(request.get_data())
        except:
            raise ParseError("Unable to load JSON data")

    cmd = ['/bin/bash']
    cmd.append('./%s/%s_%s.sh' % (base, method, script))

    if 'args' in data:
        for param in str(data['args']).translate(None, REMOVE_CHARS).split(' '):
            cmd.append(param)

    env = {}
    env['REQUEST_METHOD'] = method
    env['REQUEST_URI'] = path
    for key,value in data.items():
        if key != "args":
            env["REST_%s" % str(key).translate(None, REMOVE_CHARS).upper()] = value

    env['RAW_JSON'] = json.dumps(data)

    logfile = '%s/%s.log' % (LOGDIR, "%s-%s" % (script, int(time.time())))
    p = multiprocessing.Process(target=run, args=(cmd, env, logfile))
    p.start()
    time.sleep(1)
    return Response(tail(logfile))


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0')
