#!/bin/bash
# https://authenticationtest.com/HTTPAuth/
hydra -l user -P 100_common_passwords.txt -s 80 -f httpbin.org http-get /basic-auth/user/master
