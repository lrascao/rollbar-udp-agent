#!/bin/sh

#################################
# Beginning of the installation #
#################################

if [ -n "$ROLLBAR_ACCESS_TOKEN" ]; then
    access_token=$ROLLBAR_ACCESS_TOKEN
fi

logfile="/tmp/rollbar-udp-agent-install.log"

# install dependencies
printf "Installing Rollbar UDP Agent..." | tee -a $logfile
sudo pip install rollbar-udp-agent --no-cache-dir >> $logfile 2>&1
printf "$GREEN Done\n$DEFAULT"

printf "Configuring Rollbar access token..." | tee -a $logfile
sudo sed --in-place "s/api_key =/api_key = $ROLLBAR_ACCESS_TOKEN/g" /etc/rollbar-udp-agent.conf
printf "$GREEN Done\n$DEFAULT"

printf "Adding Rollbar UDP Agent to init.d..." | tee -a $logfile
sudo chkconfig --add rollbar-udp-agent >> $logfile 2>&1
sudo chkconfig rollbar-udp-agent on >> $logfile 2>&1
printf "$GREEN Done\n$DEFAULT"

printf "Starting Rollbar UDP Agent..." | tee -a $logfile
sudo service rollbar-udp-agent start >> $logfile 2>&1
printf "$GREEN Done\n$DEFAULT"
