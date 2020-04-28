from __future__ import print_function
import json
import sys
import logging

from os import getenv
from time import time
from boto3 import client
from botocore.exceptions import ClientError

# REQUIRED: The table name to copy records to.
# LeaderBoardTable = getenv('LEADERBOARD_TABLE')
LeaderBoardTable ='LeaderBoardTable'
LeaderBoardRegion = 'ap-northeast-1'

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

dynamodb = client('dynamodb', region_name=LeaderBoardRegion)

def handler(event, context):
    if LeaderBoardTable is None:
        raise ValueError('LeaderBoard name needed as input param')
    logger.info('invoke event %s' % json.dumps(event, indent=4, cls=DecimalEncoder))

    if 'detail' not in event or len(event['detail']) == 0:
        raise KeyError('No records are available to copy')
    switch = {
        "INSERT":insert_handle,
        "MODIFY":update_handle,
        "REMOVE":delete_handle
    }
    cookie = {
        "detail-type":event['detail-type'],
        "detail":event['detail'],
        "placeholder":"null"
    }
    try:
        switch[event['detail-type']](cookie)
    except KeyError as e:
        pass

def insert_handle(cookie):
    logger.info('enter into insert process with cookie %s' % json.dumps(cookie, indent=4, cls=DecimalEncoder))
    if 'NewImage' not in cookie['detail']:
        logger.error('Record does not have a NewImage to process')
        return

    # need to modify due to upstream dynamodb table adjustment
    # if 'projectScore' not in cookie['detail']["NewImage"] or 'userName' not in cookie['detail']["NewImage"]:
    #     logger.error('Recore does not have needed attributes')
    #     return

    # first time we create the hackathon
    if cookie['detail']["Keys"]["metaData"]["S"] == 'Details' or cookie['detail']["Keys"]["metaData"]["S"] == 'details':
        if 'hackathonName' not in cookie['detail']["NewImage"]:
            logger.error('Recore does not have needed attributes')
            return
        # extract 'hackathonName' only
        item = {
            # 'metaData': cookie['detail']["Keys"]["metaData"],
            'Id': cookie['detail']["Keys"]["Id"],
            'metaData': cookie['detail']["Keys"]["metaData"],
            'hackathonName': cookie['detail']["NewImage"]["hackathonName"],
        }
    # for successive dynamodb operations for score posting
    else:
        if 'projectScore' not in cookie['detail']["NewImage"] or 'userName' not in cookie['detail']["NewImage"]:
            logger.info('Record does not have needed attributes, pass directly')
            return
        item = {
            # 'metaData': cookie['detail']["Keys"]["metaData"],
            'Id': cookie['detail']["Keys"]["Id"],
            'metaData': cookie['detail']["Keys"]["metaData"],
            'projectScore': cookie['detail']["NewImage"]["projectScore"],
            'userName': cookie['detail']["NewImage"]["userName"],
        }
    try:
        response = dynamodb.put_item(TableName=LeaderBoardTable, Item=item)
    except ClientError as e:
        logger.info(e.response['Error']['Message'])
    else:
        logger.info("insert item successful")
        logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))

# on what condition that user update hackathon name or projectScore?
def update_handle(cookie):
    # consider refering to https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.03.html#GettingStarted.Python.03.03
    logger.info('enter into update process with cookie %s' % json.dumps(cookie, indent=4, cls=DecimalEncoder))
    if 'NewImage' not in cookie['detail']:
        logger.error('Record does not have a NewImage to process')
        return
    if 'projectScore' not in cookie['detail']["NewImage"] or 'userName' not in cookie['detail']["NewImage"]:
        logger.error('Recore does not have needed attributes')
        return
    item = {
        # 'metaData': cookie['detail']["Keys"]["metaData"],
        'Id': cookie['detail']["Keys"]["Id"],
        'metaData': cookie['detail']["Keys"]["metaData"],
        'projectScore': cookie['detail']["NewImage"]["projectScore"],
        'userName': cookie['detail']["NewImage"]["userName"],
    }
    try:
        response = dynamodb.put_item(TableName=LeaderBoardTable, Item=item)
    except ClientError as e:
        logger.info(e.response['Error']['Message'])
    else:
        logger.info("update item successful")
        logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))

def delete_handle(cookie):
    logger.info('enter into delete process with cookie %s' % json.dumps(cookie, indent=4, cls=DecimalEncoder))
    logger.info(cookie['detail']["Keys"]["Id"]["S"])
    if 'OldImage' not in cookie['detail']:
        logger.error('Record does not have a OldImage to process')
    try:
        response = dynamodb.delete_item(
            TableName=LeaderBoardTable,
            Key={
                'Id': {
                    'S': cookie['detail']["Keys"]["Id"]["S"],
                },
                'metaData': {
                    'S': cookie['detail']["Keys"]["metaData"]["S"],
                }
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            logger.info(e.response['Error']['Message'])
        else:
            raise
    else:
        logger.info("delete item successful")
        logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))
