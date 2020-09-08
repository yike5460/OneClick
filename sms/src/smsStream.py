# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
#
# Author: kyiamzn@amazon.com
# Revision: v1.0

import boto3
import json
import logging
import requests
import base64
import time
from os import getenv
from botocore.exceptions import ClientError

# @see https://docs.python.org/3/library/logging.html#logging-levels
LOGGING_LEVEL = getenv('LOGGING_LEVEL', 'INFO')

# Set up logging level, and stream stream to stdout if not running in Lambda.
# (We don't want to change the basicConfig if we ARE running in Lambda).
logger = logging.getLogger(__name__)
if getenv('AWS_EXECUTION_ENV') is None:
  logging.basicConfig(stream=sys.stdout, level=LOGGING_LEVEL)
else:
  logger.setLevel(LOGGING_LEVEL)

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

hookURL = "http://44.226.222.87:1816/sms/cgi"

def handler(event, context):

    finalPayloadList = []
    for record in event['Records']:

        # kinesis data is base64 encoded so decode here
        payload=base64.b64decode(record["kinesis"]["data"])
        print("Decoded payload: " + payload.decode())
        rawStringData = payload.decode()
        # adaption for alicloud json format
        # {
        #     "phone_number" : "13900000001",
        #     "send_time" : "2017-01-01 00:00:00",
        #     "report_time" : "2017-01-01 00:00:00",
        #     "success" : true,
        #     "err_code" : "DELIVERED",
        #     "err_msg" : "用户接收成功",
        #     "sms_size" : "1",
        #     "biz_id" : "12345",
        #     "out_id" : "67890"
        # }

        # AWS orginal format (_SMS.SUCCESS)
        # {
        #     "event_type": "_SMS.SUCCESS",
        #     "event_timestamp": 1598586072336,
        #     "arrival_timestamp": 1598586072092,
        #     "event_version": "3.1",
        #     "application": {
        #         "app_id": "1d205f0b0bb54f1a8499e1e60ce7f553",
        #         "sdk": {}
        #     },
        #     "client": {
        #         "client_id": "87if1aweya3ahcnzgncsorettp4"
        #     },
        #     "device": {
        #         "platform": {}
        #     },
        #     "session": {},
        #     "attributes": {
        #         "sender_request_id": "9506421d-192e-445c-bf29-aff2f1799d32",
        #         "destination_phone_number": "+6588583978",
        #         "record_status": "DELIVERED",
        #         "iso_country_code": "SG",
        #         "mcc_mnc": "525003",
        #         "number_of_message_parts": "1",
        #         "message_id": "ebhqipuecef0g8k06mtofa918rgtaiv3c0jbp7g0",
        #         "message_type": "Transactional",
        #         "origination_phone_number": "SenderIdAWS"
        #     },
        #     "metrics": {
        #         "price_in_millicents_usd": 5375
        #     },
        #     "awsAccountId": "705247044519"
        # }

        # {
        #     "event_type": "_SMS.FAILURE",
        #     "event_timestamp": 1598594864339,
        #     "arrival_timestamp": 1598594864339,
        #     "event_version": "3.1",
        #     "application": {
        #         "app_id": "1d205f0b0bb54f1a8499e1e60ce7f553",
        #         "sdk": {}
        #     },
        #     "client": {
        #         "client_id": "2jmj7l5rsw0yvb/vlwaykk/ybwk"
        #     },
        #     "device": {
        #         "platform": {}
        #     },
        #     "session": {},
        #     "attributes": {
        #         "number_of_message_parts": "1",
        #         "message_id": "fc3qremjc072gp5kmtvkltju34q3g2f5ckhrij00",
        #         "sender_request_id": "3f112ae5-9061-40b2-89cb-3c2a846382e3",
        #         "record_status": "Failed to send because phoneNumber provided is empty or null.",
        #         "iso_country_code": "XX"
        #     },
        #     "metrics": {
        #         "price_in_millicents_usd": 0
        #     },
        #     "awsAccountId": "705247044519"
        # }

        # concatenate payload
        finalPayload = {}
        if json.loads(rawStringData)["event_type"] == "_SMS.SUCCESS":
            finalPayload['phone_number'] = json.loads(rawStringData)["attributes"]["destination_phone_number"]

            # change to localtime
            time_local = time.localtime(json.loads(rawStringData)["event_timestamp"]/1000)
            # format as (2016-05-05 20:28:54)
            finalPayload['send_time'] = time.strftime("%Y-%m-%d %H:%M:%S",time_local)

            # change to localtime
            time_local = time.localtime(json.loads(rawStringData)["arrival_timestamp"]/1000)
            # format as (2016-05-05 20:28:54)
            finalPayload['report_time'] = time.strftime("%Y-%m-%d %H:%M:%S",time_local)

            finalPayload['success'] = (json.loads(rawStringData)["attributes"]["record_status"] == "DELIVERED")
            finalPayload['err_code'] = json.loads(rawStringData)["attributes"]["record_status"]
            finalPayload['err_msg'] = json.loads(rawStringData)["event_type"]
            finalPayload['sms_size'] = ""
            finalPayload['biz_id'] = json.loads(rawStringData)["attributes"]["message_id"]
            finalPayload['out_id'] = json.loads(rawStringData)["attributes"]["sender_request_id"]
            
            # aws specific attributes
            finalPayload['iso_country_code'] = json.loads(rawStringData)["attributes"]["iso_country_code"]
            finalPayload['message_type'] = json.loads(rawStringData)["attributes"]["message_type"]
            finalPayload['mcc_mnc'] = json.loads(rawStringData)["attributes"]["mcc_mnc"]
            finalPayload['metrics_price'] = json.loads(rawStringData)["metrics"]["price_in_millicents_usd"]

        elif json.loads(rawStringData)["event_type"] == "_SMS.FAILURE":
            # add error handler for destination_phone_number and mcc_mnc
            if "destination_phone_number" in json.loads(rawStringData)["attributes"]:
                finalPayload['phone_number'] = json.loads(rawStringData)["attributes"]["destination_phone_number"]
            else:
                finalPayload['phone_number'] = ""

            # change to localtime
            time_local = time.localtime(json.loads(rawStringData)["event_timestamp"]/1000)
            # format as (2016-05-05 20:28:54)
            finalPayload['send_time'] = time.strftime("%Y-%m-%d %H:%M:%S",time_local)

            # change to localtime
            time_local = time.localtime(json.loads(rawStringData)["arrival_timestamp"]/1000)
            # format as (2016-05-05 20:28:54)
            finalPayload['report_time'] = time.strftime("%Y-%m-%d %H:%M:%S",time_local)

            finalPayload['success'] = (json.loads(rawStringData)["attributes"]["record_status"] == "DELIVERED")
            finalPayload['err_code'] = json.loads(rawStringData)["attributes"]["record_status"]
            finalPayload['err_msg'] = json.loads(rawStringData)["event_type"]
            finalPayload['sms_size'] = ""
            finalPayload['biz_id'] = json.loads(rawStringData)["attributes"]["message_id"]
            finalPayload['out_id'] = json.loads(rawStringData)["attributes"]["sender_request_id"]
            
            # aws specific attributes
            finalPayload['iso_country_code'] = json.loads(rawStringData)["attributes"]["iso_country_code"]
            finalPayload['message_type'] = json.loads(rawStringData)["attributes"]["message_type"]
            if "mcc_mnc" in json.loads(rawStringData)["attributes"]:
                finalPayload['mcc_mnc'] = json.loads(rawStringData)["attributes"]["mcc_mnc"]
            else:
                finalPayload['mcc_mnc'] = ""
            finalPayload['metrics_price'] = json.loads(rawStringData)["metrics"]["price_in_millicents_usd"]
        else:
            logger.info('none attributes matched, return null value instead!')
        finalPayloadList.append(finalPayload)

    print(json.dumps(finalPayloadList))

    # send back to fixed customer url
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", hookURL, headers=headers, data = json.dumps(finalPayloadList))
    print(response.text.encode('utf8'))