#! /bin/bash
rm $PHOENIX_HOME/_cache -rf
rm $PHOENIX_HOME/result -rf
rm $PHOENIX_HOME/evaluation -rf
rm $PHOENIX_HOME/web/db.sqlite3 -f
python $PHOENIX_HOME/web/manage.py migrate
