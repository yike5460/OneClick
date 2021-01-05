import sys
import os
sys.path.append('/opt/python/lib/python3.7/site-packages')
# sys.path.append('/opt/python/lib/python3.7/site-packages/pytesseract')
# sys.path.append('/opt/python/lib/python3.7/site-packages/PIL')
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
import PIL
import pytesseract
import json
import io
import cv2


def write_to_file(save_path, data):
  with open(save_path, "wb") as f:
    f.write(base64.b64decode(data))
def ocr(img):
  ocr_text = pytesseract.image_to_string(img, config = "eng")
  return ocr_text
def handler(event, context=None):

    write_to_file("/tmp/photo.jpg", event['body'])
    im = cv2.imread("/tmp/photo.jpg")
    
    ocr_text = ocr(im)

    # Return the result data in json format
    return {
      "statusCode": 200,
      "body": ocr_text
    }