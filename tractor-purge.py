"""Tractor Purge - avoid running out of diskspace!
More info: https://github.com/fredrikaverpil/tractor-purge
"""

import sys
import os
import platform
import subprocess
import re
import shutil
import datetime
import logging
from optparse import OptionParser
import time
import glob


####################################
# Option parser and constants
TRACTOR_PURGE_VERSION = 'v2.0.0'
DEFAULT_DAYS = '30'
parser = OptionParser(version='%prog ' + TRACTOR_PURGE_VERSION)
parser.add_option('-t', '--tq', dest='tq',
                  default='/opt/pixar/Tractor-2.2/bin/tq',
                  help='Absolute path to tq [default: %default]')
parser.add_option('-c', '--cmd-log-sdir', dest='cmdlogsdir',
                  default='/var/spool/tractor/cmd-logs',
                  help='Absolute path to cmd-logs dir [default: %default]')
parser.add_option('-l', '--log', dest='logfile',
                  default='/var/tmp/tractor-purge.log',
                  help='Absolute path to tractor-purge log file '
                       '[default: %default]')
parser.add_option('-d', '--days', dest='days', default=DEFAULT_DAYS,
                  help='Number of days worth of jobs/logs to keep '
                       '[default: %default]')
parser.add_option('--delete-cmd-logs', action='store_true',
                  dest='deletecmdlogs',
                  default=False, help='Delete cmd logs [default: %default]')
parser.add_option('--delete-jobs', action='store_true', dest='deletejobs',
                  default=False,
                  help='Delete jobs from psql database after log deletion. '
                       'If DBArchiving is True in Tractor config, archive '
                       'jobs instead. [default: %default]')
parser.add_option('--dry-run', action='store_true', dest='dryrun',
                  default=False,
                  help='Do not perform actual deletion, instead just preview \
                      deletions [default: %default]')
(options, args) = parser.parse_args()

TQ = options.tq
CMD_LOGS_DIR = options.cmdlogsdir
PURGE_LOG = options.logfile
DAYS = options.days
DELETE_CMD_LOGS = options.deletecmdlogs
DELETE_JOBS = options.deletejobs
DRY_RUN = options.dryrun

if not os.path.exists(TQ):
    parser.error('tq not found on path' + TQ)
if DELETE_CMD_LOGS and not os.path.exists(CMD_LOGS_DIR):
    parser.error('cmd-logs dir not found on path ' + CMD_LOGS_DIR)
if DELETE_CMD_LOGS is False and DELETE_JOBS is False:
    parser.error('Neither --delete-cmd-logs or --delete-jobs were specified.')

####################################
# General setup

# Logging
logger = logging.getLogger('Tractor 2.2 purger')
hdlr = logging.FileHandler(PURGE_LOG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# Logging to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)


####################################
# Functions

def jids_to_delete(days):
    """Create list of all job ids matching query."""
    jids = []
    command = [TQ, 'jobs',
               'not active and not ready and spooltime  < -' + days + 'd',
               '--noheader', '--archives',
               '--cols', 'jid',
               '--sortby', 'jid',
               '--limit', '0']
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)

    try:
        for line in iter(p.stdout.readline, b''):
            sys.stdout.flush()
            jid = line.rstrip()
            jids.append(int(jid))
            logger.info('Found job: ' + jid)
    except:
        logger.warning('Failed to read stdout.')

    return jids


def jids_to_keep(days):
    """Create list of all job ids matching query.

    NOTE: this query returns all jids within the time span in order to
          NOT delete them.
    """

    jids = []
    command = [TQ, 'jobs',
               'spooltime > -' + days + 'd or active or ready or blocked',
               '--noheader',
               '--archives',
               '--cols', 'jid',
               '--sortby', 'jid',
               '--limit', '0']

    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)

    try:
        for line in iter(p.stdout.readline, b''):
            sys.stdout.flush()
            jid = line.rstrip()
            jids.append(int(jid))
            logger.info('Keep logs for job: ' + jid)
    except:
        logger.warning('Failed to read stdout.')

    return jids


def get_job_folders_for_deletion(job_folders, keep_jids):
    """Return list of job folders to NOT keep."""

    folders_to_delete = []

    for job_folder in job_folders:
        jid = int(os.path.basename(job_folder).replace("J", ""))

        if jid not in keep_jids:
            folders_to_delete.append(job_folder)

    return folders_to_delete


def delete_logs(delete_list):
    """Delete the actual log folders
    """
    for job_folder in delete_list:
        if not DRY_RUN:
            logger.info('Deleting %s' % job_folder)
            shutil.rmtree(job_folder)
        else:
            logger.info('Dry run: (not) deleting %s' % job_folder)


def delete_tractor_jobs(days):
    """Delete jobs from Tractor. You can also delete jobs manually using:
    tractor-dbctl --purge-archive-to-year-month YY-MM
    """
    if not DRY_RUN:
        logger.info('Executing tq command to delete jobs...')
        command = [TQ, '--force', '--yes', 'delete',
                   'not active and not ready and spooltime  < -' + days + 'd',
                   '--cols', 'jid',
                   '--limit', '0']
    else:
        logger.info('Executing tq command to (not) delete jobs...')
        command = [TQ, 'jobs', '--archives',
                   'not active and not ready and spooltime  < -' + days + 'd',
                   '--cols', 'jid',
                   '--limit', '0']

    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    try:
        for line in iter(p.stdout.readline, b''):
            sys.stdout.flush()
            logger.info(line.rstrip())
    except:
        logger.warning('Failed reading stdout.')


####################################
# Main

def main():
    """Main program."""

    # Show warning
    seconds = 10
    warning_message = ('Welcome to tractor-purge.\n\n' +
                       'This script will now execute the follow actions')
    if DRY_RUN:
        warning_message += ' in "dry run" mode:\n'
    else:
        warning_message += ':\n'
    if DELETE_CMD_LOGS:
        warning_message += ('- Delete cmd-logs older than ' +
                            str(DAYS) + ' days.\n')
    if DELETE_JOBS:
        warning_message += ('- Delete/archive jobs older than ' +
                            str(DAYS) + ' days.\n')
    warning_message += ('\nAbort now (ctrl+c) if this is does not look ' +
                        'right to you. You have ' + str(seconds) + ' ' +
                        'seconds and counting...')
    logger.warning(warning_message)
    time.sleep(seconds)

    logger.info('Tractor purge initiated.')

    # Queries
    if DELETE_CMD_LOGS:
        jids = jids_to_keep(days=DAYS)
        all_job_folders = glob.glob("%s/*/J*" % (CMD_LOGS_DIR))
        paths_to_delete = get_job_folders_for_deletion(
            job_folders=all_job_folders, keep_jids=jids)

        logger.info('Job log folders found: %s' % len(all_job_folders))
        logger.info('Job log folders to be emptied: %s' % len(paths_to_delete))

        if len(jids) > 0:
            delete_logs(delete_list=paths_to_delete)
        else:
            logger.info('No logs to delete.')

    # Delete jobs
    elif DELETE_JOBS:
        jids = jids_to_delete(days=DAYS)
        logger.info('Jobs to be deleted: %s' % len(jids))

        if len(jids) > 0:
            delete_tractor_jobs(days=DAYS)
        else:
            logger.info('No jobs to delete.')

    logger.info('Tractor purge done.\n')


if __name__ == '__main__':
    main()
