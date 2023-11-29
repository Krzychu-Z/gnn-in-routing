#!/usr/bin/env bash

PC_IPS=("10.0.2.254" "10.0.6.254" "10.0.8.254" "10.0.13.254" "10.0.14.254" "10.0.15.254" "10.0.19.254" "10.0.22.254" \
"10.0.27.254" "10.0.25.254" "10.0.26.254")
LOCAL_IP=$(ifconfig | grep inet | head -n 1 | awk -F ' ' '{print$2}')

# Launch every 2m for 30s
while true
do
  sleep 120

  # Run packet storm for 30s
  PIDS=()
  for IP in "${PC_IPS[@]}"
  do
    if [[ ${IP} =~ $LOCAL_IP ]]
    then
      continue
    else
      cat /dev/zero | pv -L 1G | nc -u "$IP" 8888 &
      PIDS+=("$!")
    fi
  done

  sleep 30

  for val in ${PIDS[*]}
  do
    kill -9 "$val"
  done

  # Sleep for a short duration to avoid high CPU usage
  sleep 1
done