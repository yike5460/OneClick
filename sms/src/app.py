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
import time
import json
import logging
from os import getenv
from botocore.exceptions import ClientError
sns = boto3.client('sns') 
pinpoint = boto3.client('pinpoint', region_name="us-west-2")
SNSorPinpoint = getenv('SNSorPinpoint')
PinPointID = getenv('PinPointID')

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

def handler(event, context):

    logger.info('invoke event %s' % json.dumps(event, indent=4, cls=DecimalEncoder))
    content = event['body'].strip().replace('\"','').replace('\\','').replace('{','').replace('}','')
    phoneNumberStart = content.find('+')
    phoneNumberEnd = content.find(',')
    msgStart = content.find(':', phoneNumberEnd)

    # The recipient's phone number.  For best results, you should specify the
    # phone number in E.164 format.
    # phoneNumber = "+6588583978"
    phoneNumber = content[phoneNumberStart:phoneNumberEnd]

    # The content of the SMS message.
    # message = ('This is a sample message sent from Amazon Pinpoint by using the AWS SDK for Python (Boto 3). %s' % time.asctime(time.localtime(time.time())))
    message = content[msgStart+1:].strip()
    logger.info('send message \"%s\" to phone %s with %s' % (message, phoneNumber, SNSorPinpoint))
    response = {}
    if SNSorPinpoint == 'SNS':
        response = sms_handler(message, phoneNumber)
    else:
        response = pinpoint_handler(message, phoneNumber)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "resultOutput": response,
        }),
    }

def pinpoint_handler(message, phoneNumber):

    # raise 1$ quota limitation for pinpoint sms sending function, refer to
    # https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-awssupport-spend-threshold.html

    # The phone number or short code to send the message from. The phone number
    # or short code that you specify has to be associated with your Amazon Pinpoint
    # account. For best results, specify long codes in E.164 format.
    originationNumber = ""

    # The Amazon Pinpoint project/application ID to use when you send this message.
    # Make sure that the SMS channel is enabled for the project or application
    # that you choose.
    applicationId = PinPointID

    # The type of SMS message that you want to send. If you plan to send
    # time-sensitive content, specify TRANSACTIONAL. If you plan to send
    # marketing-related content, specify PROMOTIONAL.
    messageType = "TRANSACTIONAL"

    # The registered keyword associated with the originating short code.
    registeredKeyword = ""

    # The sender ID to use when sending the message. Support for sender ID
    # varies by country or region. For more information, see
    # https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-countries.html
    senderId = "SenderIdAWS"

    try:
        response = pinpoint.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                'Addresses': {
                    phoneNumber: {
                        'ChannelType': 'SMS'
                    }
                },
                'MessageConfiguration': {
                    'SMSMessage': {
                        'Body': message,
                        'Keyword': registeredKeyword,
                        'MessageType': messageType,
                        'OriginationNumber': originationNumber,
                        'SenderId': senderId
                    }
                }
            }
        )
    # {
    #     'MessageResponse': {
    #         'ApplicationId': 'string',
    #         'EndpointResult': {
    #             'string': {
    #                 'Address': 'string',
    #                 'DeliveryStatus': 'SUCCESSFUL'|'THROTTLED'|'TEMPORARY_FAILURE'|'PERMANENT_FAILURE'|'UNKNOWN_FAILURE'|'OPT_OUT'|'DUPLICATE',
    #                 'MessageId': 'string',
    #                 'StatusCode': 123,
    #                 'StatusMessage': 'string',
    #                 'UpdatedToken': 'string'
    #             }
    #         },
    #         'RequestId': 'string',
    #         'Result': {
    #             'string': {
    #                 'DeliveryStatus': 'SUCCESSFUL'|'THROTTLED'|'TEMPORARY_FAILURE'|'PERMANENT_FAILURE'|'UNKNOWN_FAILURE'|'OPT_OUT'|'DUPLICATE',
    #                 'MessageId': 'string',
    #                 'StatusCode': 123,
    #                 'StatusMessage': 'string',
    #                 'UpdatedToken': 'string'
    #             }
    #         }
    #     }
    # }
    except ClientError as e:
        logger.error(e.response['Error']['Message'])

    else:
        logger.info("Message sent by Pinpoint! result %s" % response['MessageResponse']['Result'][phoneNumber])
        return {
            # mock for api gw
            "statusCode": 200,
            "body": json.dumps({
                "StatusCode": response['MessageResponse']['Result'][phoneNumber]['StatusCode'],
                "DeliveryStatus": response['MessageResponse']['Result'][phoneNumber]['DeliveryStatus'],
                "StatusMessage": response['MessageResponse']['Result'][phoneNumber]['StatusMessage'],
                # "location": ip.text.replace("\n", "")
            }),
        }

def sms_handler(message, phoneNumber):

    # Replace following with your SNS ARN 
    sns_arn = 'arn:aws:sns:us-west-2:<account id>:SimpleSMS'
    # sns_event = event 
    # sns_event["default"] = json.dumps(event) 

    '''
    response = client.publish(
        TopicArn='string',
        TargetArn='string',
        PhoneNumber='string',
        Message='string',
        Subject='string',
        MessageStructure='string',
        MessageAttributes={
            'string': {
                'DataType': 'string',
                'StringValue': 'string',
                'BinaryValue': b'bytes'
            }
        }
    )
    '''
    try: 
        response = sns.publish( 
            #TargetArn=sns_arn,
            PhoneNumber=phoneNumber,
            Message=message,
            #MessageStructure='json', 
            Subject="SMS function" 
        )
        logger.info("Message sent by SNS! result %s" % response)

        # return {
        #     'statusCode': 200,
        #     'headers': {
        #         'Content-Type': 'application/json',
        #         'Access-Control-Allow-Origin': '*',
        #         "Access-Control-Allow-Headers": "*",
        #         "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        #     },
        #     'body': json.dumps({
        #         "message": "hello world",
        #     })
        # }
        return {
            "statusCode": 200,
            "body": json.dumps({
                "HTTPStatusCode": response['ResponseMetadata']['HTTPStatusCode'],
                # "location": ip.text.replace("\n", "")
                "PlaceHolder": "NULL",
            }),
        }
    except Exception as e:
        logger.error(e)
        raise e