import boto3
import botocore
import mimetypes
from datetime import datetime, timedelta
import urllib.parse, urllib.request
from PIL import Image
import io
import re
from logger import logging

boto3.setup_default_session(profile_name='stekpad')
s3 = boto3.resource('s3', config=botocore.client.Config(signature_version='s3v4'))

def replace_image(job_id, file_name, html_string, bucket_name, bucket_folder='content/'):
    # parse html and put it in a variable
    images = set(re.findall("src='([^']+)'", html_string))
    
    logging.info("[IMG] Start analyzing html for job %s in file %s", job_id, file_name)
    
    # run loop for all images in the html
    # Upload images in our bucket and replace image src
    for image in images:
        image_src = image.strip()

        # if image was not uploaded to hackapad s3 ignore
        if not image_src.startswith('https://hackpad-attachments.s3.amazonaws.com/'):
            continue
        
        logging.info("[IMG] Processing image %s" % image_src)
        
        #get image mime_type
        mime_type_info = mimetypes.guess_type(image_src)
        mime_type = mime_type_info[0] if mime_type_info[0] else 'image/jpeg'

        # construct expire and cache_control headers
        days=100
        cache_control = 'max-age= %d' % (60 * 60 * 24 * days)
        expires = datetime.utcnow() + timedelta(days=days)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        try:
            logging.info("[IMG] First try for image %s", image_src)
            # get image name
            image_url_parts = image_src.split('/')
            image_name = image_url_parts

            # read image url
            image_src_parsed = urllib.parse.urlparse(image_src)
            image_name_encoded = urllib.parse.quote(image_src_parsed.path)            
            file = io.BytesIO(urllib.request.urlopen(urllib.parse.urljoin(image_src, image_name_encoded)).read())
            img = Image.open(file, mode='r')
        except urllib.error.HTTPError as error:
            logging.warning("[IMG] First try block resulted in urllib.error.HTTPError: %s" % error)
            try:
                logging.info("[IMG] retry for image %s", image_src)
                file = io.BytesIO(urllib.request.urlopen(image_src).read())
                img = Image.open(file, mode='r')
            except urllib.error.HTTPError as error:
                logging.error("[IMG] %s", error.read())
                continue
            except UnicodeEncodeError:
                logging.error("[IMG] UnicodeEncodeError for image %s", image_src)
                continue
                

        # get the image extension
        image_parts = image_src_parsed.path.split('.')
        image_extension = 'JPEG' if image_parts[-1].upper() == 'JPG' else image_parts[-1]
        # hack for weird image URLs
        if len(image_extension) > 4:
            image_extension = 'png'
        
        # stream file in binary mode
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format=image_extension.upper())
        imgByteArr = imgByteArr.getvalue()
        
        # upload image to our bucket
        # First check if it already exists
        exists = False
        try:
            s3.Object(bucket_name, bucket_folder + image_name[-1]).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                exists = False
        else:
            exists = True
        if exists:
            logging.info("[IMG] Skipping upload: %s already exists" % image_src)
        else:
            logging.info("[IMG] Uploading %s" % image_src)
            s3.Bucket(bucket_name).put_object(Key=bucket_folder+image_name[-1], Body=imgByteArr, ACL='public-read', ContentType=mime_type, CacheControl=cache_control,Expires=expires)

        logging.info("[IMG] Replace %s with %s" % (image_src,'https://s3-eu-west-1.amazonaws.com/'+bucket_name+'/'+bucket_folder+image_name[-1]))
        # replace the src of the image with the new uploaded location
        html_string = html_string.replace(image_src, 'https://s3-eu-west-1.amazonaws.com/'+bucket_name+'/'+bucket_folder+image_name[-1])

        logging.info("[IMG] Replaced with %s", image_src)

    logging.info("[IMG] Finished analyzing html for job %s in file %s", job_id, file_name)
        
    return html_string


if __name__ == '__main__':
    html_string = """<html><body><h1>Point helpt je beter en makkelijker delen</h1><p><img class="inline-img" faketext="*" contenteditable="false" src='https://hackpad-attachments.s3.amazonaws.com/hackpad.com_kqQGLwBTjFe_p.222569_1407665146682_Get_Point.jpg'/></p><ul><li>Het is een zoektocht die al lang aan de gang is: hoe maak je delen van sites en pagina&rsquo;s makkelijker zonder dat je daar andere diensten voor hoeft in te zetten. Het lijkt erop dat Point een goede stap is. Op dit moment nog alleen inzetbaar voor Google Chrome gebruikers, maar dat zullen velen van jullie zijn. Installeer de Point extentie en je kunt iedere pagina of ieder stuk dat je de moeite waard vindt met anderen delen.&nbsp;</li>
<li>Je selecteert een url of een zin of een afbeelding, <img class="inline-img" faketext="*" contenteditable="false" src='https://hackpad-attachments.s3.amazonaws.com/sherlock.hackpad.com_Eg6oJCrkowa_p.443015_1455387507974_Capture d’écran 2016-02-13 à 19.18.15.png'/> &rsquo;point&rsquo; hem naar een bepaalde gebruiker en kunt vervolgens met die persoon over de link het gesprek aan gaan. Om links overzichtelijk te bewaren geef je er vervolgens een hashtag aan mee.&nbsp;</li>
<li>Point <img class="inline-img" faketext="*" contenteditable="false" src='https://hackpad-attachments.s3.amazonaws.com/hackpad.com_kqQGLwBTjFe_p.222569_1407665146682_Get_Point.jpg'/> is nog maar net bezig, maar heeft potentie. Ook voor Fast Moving Targets. <img class="inline-img" faketext="*" contenteditable="false" src='https://hackpad-attachments.s3.amazonaws.com/sherlock.hackpad.com_WgNISAqLSfL_p.411274_1455572770459_Statua ing copy.png'/>Komen jullie bijvoorbeeld waardevolle berichten of video&rsquo;s of tools tegen, point ze naar <b>erwblo@gmail.com</b> en we kijken of we ze in de Handpicked nieuwsbrief meenemen!&nbsp;</li></ul>
<p>Link: <a href='http://www.getpoint.co/'/>Getpoint</a></p><p><a href='https://handpicked.hackpad.com/Handpicked-een-onregelmatige-FMT-selectie-SfyplAdeT9y'/>Terug naar overzichtspagina</a></p><p></p></body>
</html>"""
    bucket_name = 'stekpad-prod'
    res = replace_image(1, 'fake-file.html', html_string, bucket_name)
    print(res)
