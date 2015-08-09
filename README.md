## Bash2REST
Lets you execute bash scripts located in /scripts via a REST interface.  
Does some basic escape character removal, but only trust it from internal source.  

Name the script with the request method first: METHOD_SCRIPT.sh  
Ex: GET_test.sh  

You can use directories:  
/scripts/users/POST_create.sh  

Contains some example scripts:  
POST_example.sh - plain old helloworld that prints the input parameter.  
POST_env.sh - prints the environment variables that was set when the script runs.  
POST_jq.sh - example of using jq to parse JSON input  
GET_counter.sh - counting to 10 with 1s sleep in each step.  
                shows how the streaming log output works


# Execute script:
```
$ curl http://127.0.0.1:5000/example -d '{"args": "some_parameter"}'
Hello, World. You sent in: some_parameter
```

# Add extra environment variables, will be prepended with REST_:
```
$ curl http://127.0.0.1:5000/env -d '{"args": "", "key":"value"}'
REST_KEY=value
PWD=/Users/larlar/Projects/bash2rest
SHLVL=1
_=/usr/bin/env
```

# Using jq (http://stedolan.github.io/jq/) to parse JSON input:
```
$ curl http://127.0.0.1:5000/jq -d '{"args": "", "key":"value"}'
{
 "key": "value",
 "args": ""
}
```

# Build docker container with your own scripts based on this:
```
$ cat >Dockerfile <<EOF
FROM larsla/bash2rest
ADD my_scripts /scripts
VOLUME /logs
CMD /usr/bin/python /bash2rest/bash2rest.py
EOF
$ docker build -t my_bash2rest .
```
