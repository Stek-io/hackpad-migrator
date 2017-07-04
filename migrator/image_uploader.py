import boto3
from botocore.client import Config
import mimetypes
from datetime import datetime, timedelta
import urllib.parse, urllib.request
from PIL import Image
import io
from bs4 import BeautifulSoup

s3 = boto3.resource('s3', config=Config(signature_version='s3v4'))

def replace_image(html, bucket_name, http_scheme='https'):
    # parse html and put it in a variable - BeautifulSoup parses html efficiently
    soup = BeautifulSoup(html, "html.parser")

    # run loop for all images in the html
    # Upload images in our bucket and replace image src
    for image in soup.findAll('img'):
        image_src = image['src'].strip()

        if not image_src.startswith('https://hackpad-attachments.s3.amazonaws.com/'):
            continue
        
        print("Processing image %s" % image_src)
        
        #get image mime_type
        mime_type_info = mimetypes.guess_type(image_src)
        mime_type = mime_type_info[0] if mime_type_info[0] else 'image/jpeg'

        # construct expire and cache_control headers
        days=100
        cache_control = 'max-age= %d' % (60 * 60 * 24 * days)
        expires = datetime.utcnow() + timedelta(days=days)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        try:
            # get image name
            image_url_parts = image_src.split('/')
            image_name = image_url_parts

            # read image url
            image_src_parsed = urllib.parse.urlparse(image_src)
            image_name_encoded = urllib.parse.quote(image_src_parsed.path)

            file = io.BytesIO(urllib.request.urlopen(urllib.parse.urljoin(image_src, image_name_encoded)).read())
            img = Image.open(file, mode='r')
        except urllib.error.HTTPError as error:
            try:
                print(image_src)
                file = io.BytesIO(urllib.request.urlopen(image_src).read())
                img = Image.open(file, mode='r')
            except urllib.error.HTTPError as error:
                print(error.read())
                break

        # stream file in binary mode
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()
        
        # upload image to our bucket
        s3.Bucket(bucket_name).put_object(Key=image_name[-1], Body=imgByteArr, ACL='public-read', ContentType=mime_type, CacheControl=cache_control,Expires=expires)
        
        # replace the src of the image with the new uploaded location
        image['src'] = http_scheme+'://s3.eu-central-1.amazonaws.com/'+bucket_name+'/'+image_name[-1]

        print("Replaced with %s", image['src'])
        
    return str(soup)


if __name__ == '__main__':
    html = "<html><body><h1>Some Example IoT stats so far&nbsp;</h1><p><img src='https://d3q75yzwz0mnvh.cloudfront.net/images/hero-78f5b28514.jpg'/></p></body></html>"
    bucket_name = 'stekpad'
    res = replace_image(html, bucket_name)
    print(res)
