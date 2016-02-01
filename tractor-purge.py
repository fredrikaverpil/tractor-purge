#!/usr/bin/env python

import sys
import os
import platform
import subprocess
import re
import shutil
import datetime
import logging




####################################
# Settings

TQ = '/opt/pixar/Tractor-2.2/bin/tq'
TRACTOR_ENGINE = 'TRACTOR-ENGINE' # You can use an IP address here
CMD_LOGS_DIR = '/var/spool/tractor/cmd-logs'
PURGE_LOG = '/var/tmp/tractor-purge.log'
DAYS = '15' # keep logs and jobs of this age


####################################
# Set up

# TRACTOR_ENGINE environment variable
if not os.environ.get('TRACTOR_ENGINE') == None:
    os.environ['TRACTOR_ENGINE'] = TRACTOR_ENGINE

# Logging
logger = logging.getLogger('Tractor 2.2 jobs/logs purger')
hdlr = logging.FileHandler( PURGE_LOG )
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


def jobs_to_delete(days=None):
    """Create list of all jids (equivalient of all jobs to be deleted)
    """
    jids = []
    command = [TQ, 'jobs', 'done and spooltime < -' + days + \
               'd', '--nh', '-c', 'jid']
    p = subprocess.Popen( command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT )
    for line in iter(p.stdout.readline, b''):
        sys.stdout.flush()
        jid = line.rstrip()
        jids.append(int(jid))
        logger.info('Added job for deletion: ' + jid)
        
    return jids


def get_all_job_folders(cmd_logs_dir=None):
    """Create list of all job folders
    """
    job_folders = []
    for root, directories, files in os.walk( cmd_logs_dir ):
        if len(directories) > 0:
            for directory in directories:
                match = re.search('J\d*', directory)
                if match:
                    job_folder = root + '/' + directory
                    job_folders.append( job_folder )
    return job_folders


def get_job_deletion_list(job_folders=None, jids=None):
    """Compare job folders list against jids list, create deletion list
    """
    delete_list = []
    for job_folder in job_folders:
        jid_match = False
        for jid in jids:
            if job_folder.endswith('J'+str(jid)):
                jid_match = True
            
        if jid_match:
            delete_list.append( job_folder )
            logger.info('Added log folder for deletion: ' + job_folder)
            

    return delete_list


def delete_logs(delete_list=None):
    """Delete the actual log folders
    """
    for job_folder in delete_list:
        delete = True

        if delete:
            logger.info( 'Deleting ' + job_folder )
            shutil.rmtree( job_folder )


def delete_tractor_jobs(days=None):
    """Delete jobs from Tractor (requires that DBArchiving is False in 
        tractor.config)
    """
    command = [TQ, '--force', '--yes', 'delete', 'done and spooltime < -' + \
               days + 'd']
    p = subprocess.Popen( command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT )
    for line in iter(p.stdout.readline, b''):
        sys.stdout.flush()
        logger.info( line.rstrip() )




####################################
# Main

if __name__ == '__main__':

    logger.info( 'Tractor purge initiated.' )

    # Queries
    jids = jobs_to_delete(days=DAYS)
    job_folders = get_all_job_folders(cmd_logs_dir=CMD_LOGS_DIR)
    delete_list = get_job_deletion_list(job_folders=job_folders, jids=jids)

    # Summary
    logger.info('Jobs to be deleted: ' + str(len(jids)))
    logger.info('Job log folders found: ' + str(len(job_folders)))
    logger.info('Job log folders to be deleted: ' + str(len(delete_list)))


    # Delete logs
    if len(jids) > 0:
        delete_logs(delete_list=delete_list)
    else:
        logger.info( 'No logs to delete.' )

    # Delete jobs
    if len(delete_list) > 0:
        logger.info( 'Executing tq command to delete jobs...' )
        delete_tractor_jobs(days=DAYS)
    else:
        logger.info( 'No jobs to delete.' )

    logger.info( 'Tractor purge done.\n' )