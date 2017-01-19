# tractor-purge

Purge command logs from [Pixar's Tractor](https://renderman.pixar.com/view/pixars-tractor) to avoid running out of disk space.

### How does this work?

This script is designed to be executed on the Tractor engine and must have write access to the command logs.

The script will find all jobs (including archived jobs) which *do not* have status `active` or `ready` and which are older than `n` days. It will then delete all associated command logs. If the `--deletejobs` option is given, the jobs will also be deleted from the database (or archived if `DBArchiving` is set to `True` in Tractor's `db.config`).

Please note, a separate facility provided by Pixar is available to purge jobs from the job archive database: `tractor-dbctl --purge-archive-to-year-month YY-MM`


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


#### Example crontab on CentOS 7

This is how I run this script in conjunction with a jobs archive db purge:

```bash
# Tractor cmd logs purge (and archival of 7 day old jobs), run every day
  0  0 */1 *  * root /opt/tractor-purge/tractor-purge.py --days=7 --deletejobs
#
# Tractor job archives db purge (keep 2 months worth of jobs)
#
# Year and month of today
YEAR=$((`date +%y`))
MONTH=$((`date +%m`))
#
# Get year and month from today minus 2 months
if [ $MONTH -eq 1 ]
then
    YEAR=$(($YEAR-1))
    MONTH=11
else
    MONTH=$(($MONTH-2))
fi
#
# Add padding to month
MONTH=`printf "%02d\n" $MONTH`
#
# Command (must run as the user executing tractor-engine), run every day
  0  0 */1 *  * tractoruser /opt/pixar/Tractor-2.2/bin/tractor-dbctl --purge-archive-to-year-month $YEAR-$MONTH --config-dir=/opt/pixar/config
```
