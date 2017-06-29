"""
This module imports hackpad.com exported pads into another hackpad instance (like stekpad.com)
"""

import os
import mysql.connector


def process_next_job():
    """ Read job from Redis, return location of files and email address """    

    job = {}

    import_pads(job)


def import_pads(job):
    """ Import the pads for one account """

    # Open DB connection
    db = mysql_connect()
    
    # If email has no account for domain #1 yet, create one in the hackpad DB
    account_id = get_account_id(db, job['email'])
    new_account = False
    if not account_id:
        account_id = create_new_account(db, job['email'])
        new_account = True

    # Get API token for account
    client_secret = get_account_api_token(db, account_id)

    # Get the API client_id for account
    client_id = get_client_id(account_id)
        
    # Create a new hackpad for each HTML file
    pads_created = create_pads_from_files(job['file_dir'], client_id, client_secret)

    # All is good: email the customer the job is done + credentials (in case it is a new account)
    if pads_created:
        email_account(job['email'], new_account, account_id, pads_created)
    
    
def get_account_id(db, email, domain_id=1):
    """ Check if the current email is already a hackpad pro_accounts for the 
    specified domain_id and return the account_id
    """
    query = "SELECT id FROM pro_accounts WHERE email=%s AND domainId=%s"
    r = mysql_select_one(db, query, (email, domain_id))
    if r:
        return r['id']
    return None


def create_new_account(db, email, domain_id=1):
    """ Create a new hackpad pro_accounts with this email for the specified domain_id """
    print('Creating new account...')
    try:
        cursor = db.cursor()

        query = """INSERT INTO pro_accounts (id, domainId, fullName, email, passwordHash, 
        createdDate, lastLoginDate, isAdmin, tempPassHash, isDeleted, fbid, 
        deletedDate) VALUES (NULL, %s, %s, %s,
        NULL, NOW(), NOW(), 0, NULL, 0, NULL, NULL);"""
        query_args = (domain_id, email.split('@')[0], email)

        cursor.execute(query, query_args)
        db.commit()
    except mysql.connector.Error as err:
        print("Failed inserting records to Hackpad: {}".format(err))
        
    return cursor.lastrowid


def get_account_api_token(db, account_id, token_type=4):
    """ Generate a hackpad API token and insert it in the pro_token table 
    (if it doesn't exist yet) and return it.
    """
    print(account_id)


def get_client_id(account_id):
    """ Do a lookup to get the client_id for account with account_id """
    pass


def create_pads_from_files(directory, client_id, client_secret):
    """ For each HTML file in directory, create a new pad, return the number of
    created pads
    """
    files = os.listdir(directory)
    pads_created = 0

    return 0 # @@@@@@@@@@@@@@@@
    
    for file in files:
        print(file)
        fh = open(directory + '/' + file)
        insert_pad_from_file(fh, client_id, client_secret)
        pads_created += 1
    # Check if all files are imported
    if pads_created != len(files):
        print('err')
        # log an error and abort?
    return pads_created


def insert_pad_from_file(fh, client_id, client_secret):
    """ Check the file contents, and create a pad via the hackpad API """
    for line in fh:
        print(line)
    print('-'*79)
    
    # If file contains images, copy the images to our own S3 repo
    # @@@@@@@@@@@@@@@@


def email_account(email, new_account, account_id, pads_created):
    """  Email the account that the import was completed and (if new_account) 
    provide the login credentials.
    """
    pass


def mysql_connect():
    # Connect old skool to the DB    
    stek_db_host = os.environ.get('STEK_MYSQL_HOST') or '127.0.0.1'
    stek_db_port = os.environ.get('STEK_MYSQL_PORT') or '3306'
    stek_db_user = os.environ.get('STEK_MYSQL_USER') or 'root'
    stek_db_pass = os.environ.get('STEK_MYSQL_PASSWD') or ''
    stek_db_name = os.environ.get('STEK_MYSQL_DB') or 'hackpad_dev'
    stek_db_charset = os.environ.get('STEK_MYSQL_ENCODING') or 'utf8'

    conn = mysql.connector.connect(host=stek_db_host,
                                   port=stek_db_port,
                                   user=stek_db_user,
                                   passwd=stek_db_pass,
                                   database=stek_db_name,
                                   charset=stek_db_charset)
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
    job = {
        'email': 'mark-local2@pors.net',
        'file_dir': './data/hackpad.com.vEbKUwI4h4b.3nmKHa5CmC'
    }
    import_pads(job)
