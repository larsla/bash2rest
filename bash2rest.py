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
LOGDIR = "/logs"
SCRIPTDIR = "/scripts"

app = Flask(__name__)

class ParseError(Exception):
    pass

@app.route("/", methods=['GET', 'POST', 'PUT', 'DELETE'])
def index():
    return execute("")

@app.route("/<path:path>", methods=['GET', 'POST', 'PUT', 'DELETE'])
def execute(path):
    def run(cmd, env, queue, logfile):
        with open(logfile, 'wb') as log:
            def write_log(message):
                log.write(message)
                log.flush()
                queue.put(message)
            log.write("Output from %s\n" % ' '.join(cmd))
            log.write("Adding to environment:\n%s\n" % env)
            log.write("###START###\n")
            log.flush()
            p = subprocess.Popen(cmd, env=env, cwd=SCRIPTDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while True:
                line = p.stdout.readline()
                if not line:
                    break
                write_log(line)
            write_log("###STOP###\n")
        os._exit(os.EX_OK)

    def tail(queue):
        while True:
            line = queue.get()
            if line:
                if line == "###STOP###\n":
                    return
                yield line
            else:
                time.sleep(0.01)

    method = request.method
    base = os.path.dirname(path)
    script = os.path.basename(path)
    resource = '%s/%s_%s' % (base, method, script)

    if method in ["GET", "DELETE"]:
        data = {}
    else:
        try:
            data = json.loads(request.get_data())
        except:
            raise ParseError("Unable to load JSON data")

    cmd = ['/bin/bash']
    cmd.append('./%s.sh' % resource)

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

    logfile = '%s/%s.log' % (LOGDIR, "%s-%s" % (resource, int(time.time())))
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=run, args=(cmd, env, queue, logfile))
    p.start()
    return Response(tail(queue))


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0')
