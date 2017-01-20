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

def jobs_list(days):
    """Create list of all job ids matching query
    """
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


def get_all_job_folders(cmd_logs_dir):
    """Create list of all job folders
    """
    job_folders = []
    for root, directories, files in os.walk(cmd_logs_dir):
        if len(directories) > 0:
            for directory in directories:
                match = re.search(r'J\d*', directory)
                if match:
                    job_folder = root + '/' + directory
                    job_folders.append(job_folder)
    return job_folders


def get_job_folders_for_deletion(job_folders, jids):
    """Compare job folders list against jids list, create deletion list
    """
    delete_list = []
    for job_folder in job_folders:
        jid_match = False
        for jid in jids:
            if job_folder.endswith('J' + str(jid)):
                jid_match = True

        if jid_match:
            delete_list.append(job_folder)
            logger.info('Added log folder for deletion: ' + job_folder)

    return delete_list


def delete_logs(delete_list):
    """Delete the actual log folders
    """
    for job_folder in delete_list:
        if not DRY_RUN:
            logger.info('Deleting ' + job_folder)
            shutil.rmtree(job_folder)
        else:
            logger.info('Dry run: (not) deleting ' + job_folder)


def delete_tractor_jobs(days):
    """Delete jobs from Tractor. You can also delete jobs manually using:
    tractor-dbctl --purge-archive-to-year-month YY-MM
    """
    if not DRY_RUN:
        logger.info('Executing tq command to delete jobs...')
        command = [TQ, '--force', '--yes', 'delete',
                   'not active and not ready and spooltime  < -' + days + 'd',
                   '--limit', '0']
    else:
        logger.info('Executing tq command to (not) delete jobs...')
        command = [TQ, 'jobs', '--archives',
                   'not active and not ready and spooltime  < -' + days + 'd',
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

if __name__ == '__main__':

    # Show warning
    SECONDS = 10
    WARNING_MESSAGE = ('Welcome to tractor-purge.\n\n' +
                      'This script will now execute the follow actions')
    if DRY_RUN:
        WARNING_MESSAGE += ' in "dry run" mode:\n'
    else:
        WARNING_MESSAGE += ':\n'
    if DELETE_CMD_LOGS:
        WARNING_MESSAGE += ('- Delete cmd-logs older than ' +
                            str(DAYS) + ' days.\n')
    if DELETE_JOBS:
        WARNING_MESSAGE += ('- Delete/archive jobs older than ' +
                            str(DAYS) + ' days.\n')
    WARNING_MESSAGE += ('\nAbort now (ctrl+c) if this is does not look ' +
                        'right to you. You have ' + str(SECONDS) + ' ' +
                        'seconds and counting...')
    logger.warning(WARNING_MESSAGE)
    time.sleep(SECONDS)

    logger.info('Tractor purge initiated.')

    # Queries
    jids = jobs_list(days=DAYS)
    if DELETE_CMD_LOGS:
        all_job_folders = get_all_job_folders(cmd_logs_dir=CMD_LOGS_DIR)
        job_folders_for_deletion = get_job_folders_for_deletion(
            job_folders=all_job_folders, jids=jids)

    # Summary
    if DELETE_CMD_LOGS:
        logger.info('Job log folders found: ' +
                    str(len(all_job_folders)))
        logger.info('Job log folders to be emptied: ' +
                    str(len(job_folders_for_deletion)))
    if DELETE_JOBS:
        logger.info('Jobs to be deleted: ' + str(len(jids)))

    # Delete logs
    if DELETE_CMD_LOGS:
        if len(jids) > 0:
            delete_logs(delete_list=job_folders_for_deletion)
        else:
            logger.info('No logs to delete.')

    # Delete jobs
    if DELETE_JOBS:
        if len(jids) > 0:
            delete_tractor_jobs(days=DAYS)
        else:
            logger.info('No jobs to delete.')

    logger.info('Tractor purge done.\n')
