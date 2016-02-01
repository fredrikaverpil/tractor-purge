# tractor-purge

Purge task logs from [Pixar's Tractor](https://renderman.pixar.com/view/pixars-tractor) to avoid running out of disk space.

### How does this work?

This script was designed to be executed on the Tractor engine, and with the default cmd-logs spool path settings: `/var/spool/tractor/cmd-logs` and with `DBArchiving` set to `False` in tractor.config.

The script will find all jobs which have *do not* have status `active` and which are older than `n` days. It will then delete all associated task logs and the job itself from the Tractor database.

#### Installation and execution of script

Edit the script and set the path to tq, the engine name/IP, the cmd-logs location, the purge log, and the number of days worth of jobs and logs to keep.

Then execute like this:

    python tractor-purge.py


Or run as cron job every 1 day:

    chmod +x python tractor-purge.py
    echo "0 0 */1 * * root python /path/to/tractor-purge.py" >> /etc/crontab


