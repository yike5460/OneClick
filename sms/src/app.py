
import boto3
import time
import json
from os import getenv
from botocore.exceptions import ClientError
sns = boto3.client('sns') 
pinpoint = boto3.client('pinpoint', region_name="us-west-2")
PinPointID = getenv('PinPointID')

def pinpoint_handler(event, context):

    # raise 1$ quota limitation for pinpoint sms sending function, refer to
    # https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-awssupport-spend-threshold.html

    content = event['body'].strip().replace('\"','').replace('\\','').replace('{','').replace('}','')
    print(content)
    phoneNumberStart = content.find('+')
    phoneNumberEnd = content.find(',')
    msgStart = content.find(':', phoneNumberEnd)

    # The phone number or short code to send the message from. The phone number
    # or short code that you specify has to be associated with your Amazon Pinpoint
    # account. For best results, specify long codes in E.164 format.
    originationNumber = ""

    # The recipient's phone number.  For best results, you should specify the
    # phone number in E.164 format.
    # phoneNumber = "+6588583978"
    phoneNumber = content[phoneNumberStart:phoneNumberEnd]

    # The content of the SMS message.
    # message = ('This is a sample message sent from Amazon Pinpoint by using the AWS SDK for Python (Boto 3). %s' % time.asctime(time.localtime(time.time())))
    message = content[msgStart+1:].strip()
    print('send sms %s to phone number %s' %(message, phoneNumber))

    # The Amazon Pinpoint project/application ID to use when you send this message.
    # Make sure that the SMS channel is enabled for the project or application
    # that you choose.
    applicationId = PinPointID
    print('applicationId is %s' % applicationId)
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

    except ClientError as e:
        print(e.response['Error']['Message'])
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
    else:
        print("Message sent! result %s" % response['MessageResponse']['Result'][phoneNumber])
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

def sms_handler(event, context):

    # https://aws.amazon.com/cn/premiumsupport/knowledge-center/sns-sms-spending-limit-increase/
    print("Received event: " + json.dumps(event, indent=2)) 
    # Replace following with your SNS ARN 
    sns_arn = 'arn:aws:sns:us-west-2:705247044519:SimpleSMS'
    sns_event = event 
    sns_event["default"] = json.dumps(event) 
    try: 
        response = sns.publish( 
            TargetArn=sns_arn,
            PhoneNumber='+6588583978',
            Message='Test from SNS',
            #MessageStructure='json', 
            Subject="Test for SMS function" 
        )
        print("Message sent! result %s" % response)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "successful sending SMS!",
                # "location": ip.text.replace("\n", "")
            }),
        }
    except Exception as e:
        print(e)
        raise e