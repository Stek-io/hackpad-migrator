import boto3
from botocore.client import Config
import mimetypes
from datetime import datetime, timedelta
import urllib.request
from PIL import Image
import io
from bs4 import BeautifulSoup

bucket_name = 'stekpad'

s3 = boto3.resource('s3', config=Config(signature_version='s3v4'))

def replace_image(html, bucket_name, http_scheme):
    # parse html and add it in a var - will help to find images efficiently and replace the src attribute
    soup = BeautifulSoup(html, "html.parser")

    # run loop for all images in the html
    # Upload images in our bucket and replace image src
    for image in soup.findAll('img'):
        image_src = image['src']

        # read image url
        file = io.BytesIO(urllib.request.urlopen(image_src).read())
        img = Image.open(file, mode='r')

        # stream file in binary mode
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()

        # get image name
        image_url_parts = image_src.split('/')
        image_name = image_url_parts

        # get image mime_type
        mime_type_info = mimetypes.guess_type(image_src)
        mime_type = mime_type_info[0] if mime_type_info[0] else 'binary/octet-stream'

        # construct expire and cache control headers
        days=100
        cache_control = 'max-age= %d' % (60 * 60 * 24 * days)
        expires = datetime.utcnow() + timedelta(days=days)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # upload images to our bucket
        s3.Bucket(bucket_name).put_object(Key=image_name[-1], Body=imgByteArr, ACL='public-read', ContentType=mime_type, CacheControl=cache_control,Expires=expires)

        # replace the src of the image with the new uploaded location
        image['src'] = http_scheme+'://s3.eu-central-1.amazonaws.com/'+bucket_name+'/'+image_name[-1]

        return soup