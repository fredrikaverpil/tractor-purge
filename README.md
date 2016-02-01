# tractor-purge

### What's this?

Purge task logs from Pixar's Tractor to avoid running out of disk space.

### Instructions

This script was designed to be executed on the Tractor engine, and with the default cmd-logs spool path settings: `/var/spool/tractor/cmd-logs` and with `DBArchiving` set to `False` in tractor.config.

#### Installation and execution of script

Edit the script and set the path to tq, the engine name/IP, the cmd-logs location, the purge log, and the number of days worth of jobs and logs to keep.

Then execute like this:

    python tractor_job_log_purge.py


Or run as cron job every 1 day:

    chmod +x python tractor-purge.py
    nano /etc/crontab (...and enter:)
    echo "0 0 */1 * * root python /path/to/tractor-purge.py" >> /etc/crontab


