import boto3
from botocore.client import Config
import mimetypes
from datetime import datetime, timedelta
import urllib.parse, urllib.request
from PIL import Image
import io
from bs4 import BeautifulSoup
from logger import logging

s3 = boto3.resource('s3', config=Config(signature_version='s3v4'))

def replace_image(job_id, file_name, html, bucket_name, http_scheme='https'):
    # parse html and put it in a variable - BeautifulSoup parses html efficiently
    soup = BeautifulSoup(html, "html.parser")

    logging.debug("[IMG] Start analyzing html for job %s in file %s", job_id, file_name)
    
    # run loop for all images in the html
    # Upload images in our bucket and replace image src
    for image in soup.findAll('img'):
        image_src = image['src'].strip()

        # if image was not uploaded to hackapad s3 ignore
        if not image_src.startswith('https://hackpad-attachments.s3.amazonaws.com/'):
            continue
        
        logging.debug("[IMG] Processing image %s" % image_src)
        
        #get image mime_type
        mime_type_info = mimetypes.guess_type(image_src)
        mime_type = mime_type_info[0] if mime_type_info[0] else 'image/jpeg'

        # construct expire and cache_control headers
        days=100
        cache_control = 'max-age= %d' % (60 * 60 * 24 * days)
        expires = datetime.utcnow() + timedelta(days=days)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        try:
            logging.debug("[IMG] First try for image %s", image_src)
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
                logging.debug("[IMG] retry for image %s", image_src)
                file = io.BytesIO(urllib.request.urlopen(image_src).read())
                img = Image.open(file, mode='r')
            except urllib.error.HTTPError as error:
                logging.error("[IMG] %s", error.read())
                continue

        # get the image extension
        image_parts = image_src_parsed.path.split('.')
        image_extension = image_parts[-1] =='jpg' and 'JPEG' or image_parts[-1]

        # stream file in binary mode
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format=image_extension.upper())
        imgByteArr = imgByteArr.getvalue()
        
        # upload image to our bucket
        s3.Bucket(bucket_name).put_object(Key=image_name[-1], Body=imgByteArr, ACL='public-read', ContentType=mime_type, CacheControl=cache_control,Expires=expires)
        
        # replace the src of the image with the new uploaded location
        image['src'] = http_scheme+'://s3.eu-central-1.amazonaws.com/'+bucket_name+'/'+image_name[-1]

        logging.debug("[IMG] Replaced with %s", image['src'])

    logging.debug("[IMG] Finished analyzing html for job %s in file %s", job_id, file_name)
        
    return str(soup)


if __name__ == '__main__':
    html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="en-us" />
<meta name="version" content="482"/>
<style>body {font-family:Helvetica}ul.comment{list-style-image:url('https://hackpad.com/static/img/comment.png');} ul.task{list-style-image:url('https://hackpad.com/static/img/unchecked.png');}ul.taskdone{list-style-image:url('https://hackpad.com/static/img/checked.png');} </style><title>/16474$kqQGLwBTjFe</title>
</head>
<body><h1>Point helpt je beter en makkelijker delen</h1><p><img src='https://hackpad-attachments.s3.amazonaws.com/hackpad.com_kqQGLwBTjFe_p.222569_1407665146682_Get_Point.jpg'/></p><ul><li>Het is een zoektocht die al lang aan de gang is: hoe maak je delen van sites en pagina&rsquo;s makkelijker zonder dat je daar andere diensten voor hoeft in te zetten. Het lijkt erop dat Point een goede stap is. Op dit moment nog alleen inzetbaar voor Google Chrome gebruikers, maar dat zullen velen van jullie zijn. Installeer de Point extentie en je kunt iedere pagina of ieder stuk dat je de moeite waard vindt met anderen delen.&nbsp;</li>
<li>Je selecteert een url of een zin of een afbeelding, &rsquo;point&rsquo; hem naar een bepaalde gebruiker en kunt vervolgens met die persoon over de link het gesprek aan gaan. Om links overzichtelijk te bewaren geef je er vervolgens een hashtag aan mee.&nbsp;</li>
<li>Point is nog maar net bezig, maar heeft potentie. Ook voor Fast Moving Targets. Komen jullie bijvoorbeeld waardevolle berichten of video&rsquo;s of tools tegen, point ze naar <b>erwblo@gmail.com</b> en we kijken of we ze in de Handpicked nieuwsbrief meenemen!&nbsp;</li></ul>
<p>Link: <a href='http://www.getpoint.co/'/>Getpoint</a></p><p><a href='https://handpicked.hackpad.com/Handpicked-een-onregelmatige-FMT-selectie-SfyplAdeT9y'/>Terug naar overzichtspagina</a></p><p></p></body>
</html>"""
    bucket_name = 'stekpad'
    res = replace_image(1, 'fake-file.html', html, bucket_name)
    print(res)
