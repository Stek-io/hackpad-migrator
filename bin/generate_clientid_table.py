import click
import subprocess

@click.command()
@click.option('--count', default=10, help='Number of client_id\'s to generate. Default 10.')
@click.option('--path', default='../client_ids/',
              help='Location of the lookup files, including trailing slash. Default is ../client_ids/')
@click.argument('account_id_encryption_key')
def generate_client_ids(count, path, account_id_encryption_key):
    """ Use the crypto.jar executable to generate more client_id's 
    for the hackpad API. Every run it generates an additional 10
    """

    # Open the file (or create it if non existing) and read number of lines
    with open(path + account_id_encryption_key, 'a+') as f:
        # Read the number of account id's for the specific key
        num_lines = 0
        f.seek(0)
        for num_lines, l in enumerate(f, 1): pass

    # Generate client_ids and append to file
    with open(path + account_id_encryption_key, 'a') as f:                
        for x in range(num_lines+1, num_lines+count+1):
            # java -jar crypto.jar 0123456789abcdef 6
            result = subprocess.run(['java', '-jar', 'crypto.jar', account_id_encryption_key, str(x)], stdout=subprocess.PIPE)
            client_id = result.stdout.decode('utf-8')
            print('Adding line: %s %s' % (x, client_id))
            f.write("%s %s" % (x, client_id))
            
if __name__ == '__main__':
    generate_client_ids()
