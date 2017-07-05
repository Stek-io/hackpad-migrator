"""
This module imports hackpad.com exported pads into another hackpad instance (like stekpad.com)
"""

import os
import mysql.connector
import redis
import random
import string
import re
import time
import magic
import html
import json
import gevent
import zipfile
from hackpad_api.hackpad import Hackpad
from image_uploader import replace_image
from send_email import send_html_email, send_text_email
from gevent import monkey
monkey.patch_all()


EMULATE_INSERTS_DELAY = 0 # real inserts when 0, otherwise delay per fake insert in seconds

# TODO
# create error, done, active queues
# stop the whole thing on error


def process_next_job():
    """ Read job from Redis, return location of files and email address """
    hackpad_rdb_host = os.environ.get('HACKPAD_REDIS_HOST') or '127.0.0.1'
    hackpad_rdb_port = os.environ.get('HACKPAD_REDIS_PORT') or '6379'
    hackpad_rdb_db = os.environ.get('HACKPAD_REDIS_DB') or 9

    hackpad_max_concurrent_jobs = os.environ.get('HACKPAD_MAX_CONCURRENT_JOBS') or 3
    active_jobs = 0
    
    rdb = redis.StrictRedis(host=hackpad_rdb_host, port=hackpad_rdb_port, db=hackpad_rdb_db)

    if EMULATE_INSERTS_DELAY > 0:
        # rdb.lpush('hackpad_imports', json.dumps({
        #     'from': 'Job1 One <job1@example.com>',
        #     'email_address': 'njob1@example.com',
        #     'attachment': './attachment/sherlock.hackpad.com.zxpc7WkEDkm.WiONyRJ5cG.zip'
        # }))
        rdb.lpush('hackpad_imports', json.dumps({
            'from': 'Job2 Two <job2@example.com>',
            'email_address': 'njob2@example.com',
            'attachment': './attachment/handpicked.hackpad.com.tz4vKPzuePB.yN4qm8o9SH.zip'
        }))
        rdb.lpush('hackpad_imports', json.dumps({
            'from': 'Three, Job3 <job3@example.com>',
            'email_address': 'njob3@example.com',
            'attachment': './attachment/hackpad.com.vEbKUwI4h4b.3nmKHa5CmC.zip'
        }))
        rdb.lpush('hackpad_imports', json.dumps({
            'from': 'Job4 <job4@example.com>',
            'email_address': 'njob4@example.com',
            'attachment': './attachment/hackpad.com.pxb3L0YOxil.neEUiOgdr2.zip'
        }))

    pool = gevent.pool.Pool(hackpad_max_concurrent_jobs)

    while True:
        job = rdb.brpop('hackpad_imports')
        job = json.loads(job[1].decode('utf-8'))

        pool.spawn(import_pads, job)



def import_pads(job):
    """ Import the pads for one account """

    # Open DB connection
    db = mysql_connect()
    
    # If email has no account for domain #1 yet, create one in the hackpad DB
    account_id = get_account_id(db, job['email_address'])
    new_account = False
    if not account_id:
        account_id = create_new_account(db, job['email_address'], job['from'])
        new_account = True

    # Get API token for account
    client_secret = get_account_api_token(db, account_id)

    # Get the API client_id for account
    client_id = get_client_id(account_id)
        
    # Create a new hackpad for each HTML file
    pads_created, pads_skipped = create_pads_from_files(job['attachment'], job['email_address'], client_id, client_secret)

    # All is good: email the customer the job is done + credentials (in case it is a new account)
    if pads_created + pads_skipped:
        email_account(job['email_address'], new_account, account_id, pads_created, pads_skipped)

    return True
    
def get_account_id(db, email, domain_id=1):
    """ Check if the current email is already a hackpad pro_accounts for the 
    specified domain_id and return the account_id
    """
    query = "SELECT id FROM pro_accounts WHERE email=%s AND domainId=%s"
    r = mysql_select_one(db, query, (email, domain_id))
    if r:
        return r['id']
    return None


def create_new_account(db, email, the_from, domain_id=1):
    """ Create a new hackpad pro_accounts with this email for the specified domain_id """
    print('Creating new account...')
    try:
        cursor = db.cursor()

        full_name = from_to_name(the_from, email)
        
        query = """INSERT INTO pro_accounts (id, domainId, fullName, email, passwordHash, 
        createdDate, lastLoginDate, isAdmin, tempPassHash, isDeleted, fbid, 
        deletedDate) VALUES (NULL, %s, %s, %s,
        NULL, NOW(), NOW(), 0, NULL, 0, NULL, NULL);"""
        query_args = (domain_id, full_name, email)

        cursor.execute(query, query_args)
        db.commit()
    except mysql.connector.Error as err:
        print("Failed inserting records to Hackpad: {}".format(err))
        
    return cursor.lastrowid


def get_account_api_token(db, account_id, token_type=4):
    """ Generate a hackpad API token and insert it in the pro_tokens table 
    (if it doesn't exist yet) and return it.
    """
    query = "SELECT token FROM pro_tokens WHERE userId=%s AND tokenType=%s"
    r = mysql_select_one(db, query, (account_id, token_type))
    if r:
        if isinstance(r['token'], bytearray): # this db field is binary
            return r['token'].decode()        
        return r['token']
    
    print('Creating new token...')
    try:
        cursor = db.cursor()

        # Generate token: https://stackoverflow.com/a/23728630/562267
        token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(32))
        
        query = """INSERT INTO pro_tokens (userId, tokenType, expirationDate, token, tokenExtra) 
        VALUES (%s, %s, NULL, %s, NULL);"""
        query_args = (account_id, token_type, token)

        cursor.execute(query, query_args)
        db.commit()
    except mysql.connector.Error as err:
        print("Failed inserting token to Hackpad: {}".format(err))

    return token


def get_client_id(account_id):
    """ Do a lookup to get the client_id for account with account_id """
    account_id_encryption_key = os.environ.get('HACKPAD_ACCOUNT_ID_KEY') or '0123456789abcdef' # default used for local testing
    client_ids_path = os.environ.get('HACKPAD_CLIENT_IDS_PATH') or './client_ids/' # default used for local testing
    for line in open(client_ids_path + account_id_encryption_key, 'r'):
        id, client_id = line.split(' ')
        if str(account_id) == id:
            return client_id.strip()
    return False # trigger error @@@@@@@@@@@@
    

def create_pads_from_files(attachment, email, client_id, client_secret):
    """ For each HTML file in zipped attachment, create a new pad, return the number of
    created pads
    """
    print("Opening attached zip %s." % attachment)
    m = re.search('^.+attachment/(.+)\.zip$', attachment)
    directory = './data/' + m.group(1)
    unzip_attachment(attachment, directory)
    files = os.listdir(directory)
    
    hackpad = Hackpad(api_domain = os.getenv('HACKPAD_API_DOMAIN') or 'hackpad.dev',
                      sub_domain = os.getenv('HACKPAD_SUB_DOMAIN') or '',
                      consumer_key = client_id,
                      consumer_secret = client_secret)

    pads_created = pads_skipped = 0

    for file_name in files:
        file_path = directory + '/' + file_name
        # check if it is really an html file
        file_type = magic.from_file(file_path, mime=True)
        if file_type != 'text/html':
            print('Invalid file type for file %s :%s' % (file_path, file_type))
            continue 
        
        fh = open(file_path)

        print('importing for %s: %s' % (email, file_name))
        
        if insert_pad_from_file(hackpad, fh, file_name, client_id, client_secret):
            pads_created += 1
        else:
            pads_skipped += 1
        fh.close()
    # Check if all files are imported
    if pads_created + pads_skipped != len(files):
        print('err')
        # log an error and abort?
    return pads_created, pads_skipped


def insert_pad_from_file(hackpad, fh, file_name, client_id, client_secret):
    """ Check the file contents, and create a pad via the hackpad API """
    html_pad = fh.read().replace('\n', '')
    if html_pad == '<body><h1>Untitled</h1><p></p><p>This pad text is synchronized as you type, so that everyone viewing this page sees the same text.&nbsp; This allows you to collaborate seamlessly on documents!</p><p></p><p></p></body>':
        return False # default pad
    html_pad = re.sub(r'^.*?<body', '<html><body', html_pad) # remove all stuff before first <body> tag

    # If file contains images, copy the images to our own S3 repo
    html_pad = replace_image(html_pad, 'stekpad')
    
    # get the title
    m = re.search('<h1.*?>(.+?)</h1>', html_pad)
    if m:
        title = re.sub('<[^<]+?>', '', m.group(1)) # strip html tags
        title = html.unescape(title).strip() # remove html encoded chars and whitespace around string
    else:
        # use the filename as the title
        title = file_name.replace('-', ' ').rstrip('.html').strip()

    if EMULATE_INSERTS_DELAY:
        print('Fake create, sleeping for %s seconds...' % EMULATE_INSERTS_DELAY)
        time.sleep(EMULATE_INSERTS_DELAY)
    else: # real insert
        new_pad = hackpad.create_hackpad(title, html_pad, '', 'text/html')
        if new_pad and 'globalPadId' in new_pad:
            print('Created pad: %s' % new_pad['globalPadId'])
            return True
        else:
            # log an error and mention in summary email? @@@@@@@@@@@@@@
            print("Could not create pad %s" % file_name)
            return False


def email_account(email, new_account, account_id, pads_created, pads_skipped):
    """  Email the account that the import was completed and (if new_account) 
    provide the login credentials.
    """
    msg = """Hi!

We have migrated your hackpad.com pads to stekpad.com!

Number of pads migrated: %s
Number of pads skipped (no content): %s

Please go to https://stekpad.com/ and login with your Google or Facebook account that uses the email address '%s'.

If your Google or Facebook accounts have a different email adress, please create a free Stek.io account with the email address '%s'. Then log in with Stek.

Cheers,
The Stek Team
    """ % (pads_created, pads_skipped, email, email)
    send_text_email('hello@stek.io', email, 'hello@stek.io', 'Migration from hackpad.com completed', msg)    



def unzip_attachment(zipped_attachment, target_dir):
    """ Unzip attachment into the data directory """
    zip_ref = zipfile.ZipFile(zipped_attachment, 'r')
    zip_ref.extractall(target_dir)
    zip_ref.close()

def from_to_name(the_from, email):
    """" Convert the from field of the email sender to a full name if possible """
    # First remove email and spacing
    the_from = re.sub('<.+>', '', the_from).strip()

    if not the_from:
        return email.split('@')[0]
    
    # If there is a comma, assume swapped first/last
    if ',' in the_from:
        parts = the_from.split(',')
        return parts[-1].strip() + ' ' + ' '.join(parts[:-1]).strip()
    
    return the_from


def mysql_connect():
    # Connect old skool to the DB    
    hackpad_db_host = os.environ.get('HACKPAD_MYSQL_HOST') or '127.0.0.1'
    hackpad_db_port = os.environ.get('HACKPAD_MYSQL_PORT') or '3306'
    hackpad_db_user = os.environ.get('HACKPAD_MYSQL_USER') or 'root'
    hackpad_db_pass = os.environ.get('HACKPAD_MYSQL_PASSWD') or ''
    hackpad_db_name = os.environ.get('HACKPAD_MYSQL_DB') or 'hackpad_dev'
    hackpad_db_charset = os.environ.get('HACKPAD_MYSQL_ENCODING') or 'utf8'

    conn = mysql.connector.connect(host=hackpad_db_host,
                                   port=hackpad_db_port,
                                   user=hackpad_db_user,
                                   passwd=hackpad_db_pass,
                                   database=hackpad_db_name,
                                   charset=hackpad_db_charset)
    return conn


def mysql_select_one(conn, query, query_args=None):
    """
    Fetches the first record matching the given query

    :param conn: Mysql Connection
    :param query: The SELECT query to run
    :param query_args: Query arguments
    :return: Result
    """
    # Return first row of result object
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, query_args)
    row = cursor.fetchone()
    cursor.close()
    return row



if __name__ == '__main__':
    process_next_job()
