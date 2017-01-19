# tractor-purge

Purge command logs from [Pixar's Tractor](https://renderman.pixar.com/view/pixars-tractor) to avoid running out of disk space.

### How does this work?

This script is designed to be executed on the Tractor engine and must have write access to the command logs.

The script will find all jobs (including archived jobs) which *do not* have status `active` or `ready` and which are older than `n` days. It will then delete all associated command logs. If the `--deletejobs` option is given, the jobs will also be deleted from the database (or archived if `DBArchiving` is set to `True` in Tractor's `db.config`).

Please note, instead of using the `--deletejobs` option, you may wish to run the facility provided by Pixar to purge jobs from the database: `tractor-dbctl --purge-archive-to-year-month YY-MM`


#### Installation and execution of script

Put the file somewhere on the Tractor Engine, e.g:

    $ git clone https://github.com/fredrikaverpil/tractor-purge.git /opt/tractor-purge

Check out the commandline options:

    $ python tractor-purge.py --help

    Usage: tractor-purge.py [options]

    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -t TQ, --tq=TQ        Absolute path to tq [default:
                            /opt/pixar/Tractor-2.2/bin/tq]
      -c CMDLOGSDIR, --cmdlogsdir=CMDLOGSDIR
                            Absolute path to cmd-logs dir [default:
                            /var/spool/tractor/cmd-logs]
      -l LOGFILE, --log=LOGFILE
                            Absolute path to tractor-purge log file [default:
                            /var/tmp/tractor-purge.log]
      -d DAYS, --days=DAYS  Number of days worth of jobs/logs to keep [default:
                            30]
      --deletejobs          Delete jobs from psql database after log deletion. If
                            DBArchiving is True in Tractor config, archive jobs
                            instead.
      --dryrun              Do not perform actual deletion, instead just preview
                            deletions

Then execute like this:

    $ python tractor-purge.py [OPTIONS]


Or run as cron job every 1 day:

    $ chmod +x python tractor-purge.py
    $ echo "0 0 */1 * * root python /path/to/tractor-purge.py" >> /etc/crontab


