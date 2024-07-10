#!/bin/bash
while true; do
    flask db upgrade
    if [[ "$?" == "0" ]]; then
      break
    fi
    echo Upgrade command failed, retrying in 5 sec...
    sleep 5
done
exec gunicorn --workers 4 -b :5000 --access-logfile - --error-logfile - testsite:app
