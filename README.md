# tractor-purge

Purge command logs and/or delete/archive jobs from [Pixar's Tractor](https://renderman.pixar.com/view/pixars-tractor) to avoid running out of disk space.

### How does this work?

This script is designed to be executed on the Tractor engine and must have write access to the command logs.

The script will find all jobs (including archived jobs) which *do not* have status `active` or `ready` and which are older than `n` days. It will then delete all associated command logs. If the `--deletejobs` option is given, the jobs will also be deleted from the database (or archived if `DBArchiving` is set to `True` in Tractor's `db.config`).

Please note, a separate facility provided by Pixar is available to purge jobs from the job archive database: `tractor-dbctl --purge-archive-to-year-month YY-MM`


#### Installation and execution of script

Put the file somewhere on the Tractor Engine, e.g:

    $ git clone https://github.com/fredrikaverpil/tractor-purge.git /opt/tractor-purge

Check out the commandline options:

```
$ python tractor-purge.py --help

  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -t TQ, --tq=TQ        Absolute path to tq [default:
                        /opt/pixar/Tractor-2.2/bin/tq]
  -c CMDLOGSDIR, --cmd-log-sdir=CMDLOGSDIR
                        Absolute path to cmd-logs dir [default:
                        /var/spool/tractor/cmd-logs]
  -l LOGFILE, --log=LOGFILE
                        Absolute path to tractor-purge log file [default:
                        /var/tmp/tractor-purge.log]
  -d DAYS, --days=DAYS  Number of days worth of jobs/logs to keep [default:
                        30]
  --delete-cmd-logs     Delete cmd logs [default: False]
  --delete-jobs         Delete jobs from psql database after log deletion. If
                        DBArchiving is True in Tractor config, archive jobs
                        instead. [default: False]
  --dry-run             Do not perform actual deletion, instead just preview
                        deletions [default: False]
```

#### Example crontab on CentOS 7

This is how I run this script in conjunction with a jobs archive db purge on a nightly basis. I have `DBArchiving` set to `True` in my `db.config`.

* Archive jobs with status "not active and not ready" which are older than 7 days
* Delete command logs which are part of jobs older than 2 months
* Purge archives database of jobs which are older than 2 months

```bash
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
# |  |  |  |  |
# *  *  *  *  * user-name  command to be executed
#

# Tractor Purge
#
# Remove cmd-logs for jobs which are older than 2 months:
  1  0 */1 *  * root python /opt/tractor-purge/tractor-purge.py --delete-cmd-logs --days=60
#
# Archive jobs older than 7 days which are "not active and not ready":
  5  0 */1 *  * root python /opt/tractor-purge/tractor-purge.py --delete-jobs --days=7
#
# Purge Tractor job archives database (keep 2 months worth of jobs):
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
