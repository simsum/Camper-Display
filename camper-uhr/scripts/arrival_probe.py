"""Run the same provider as the Pi without touching GPS, settings or services."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import arrival_provider

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--include-image',action='store_true')
    parser.add_argument('--image-out',help='Save the downloaded raster for local preview')
    args=parser.parse_args()
    start=time.monotonic()
    data=arrival_provider.lookup(45.7663900,10.4937710)
    image=data.pop('_image',b'')
    data['image_bytes']=len(image)
    data['lookup_seconds']=round(time.monotonic()-start,2)
    data['test']=True
    if args.image_out and image:
        Path(args.image_out).write_bytes(image)
    if args.include_image and image:
        data['image_url']='data:'+data['image_mime']+';base64,'+base64.b64encode(image).decode()
    print(json.dumps(data,ensure_ascii=True))
