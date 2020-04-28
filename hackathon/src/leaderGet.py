from __future__ import print_function
import json
import sys
import logging
import os
from os import getenv

from boto3 import client
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import jsonUtils as jsonU

dynamoDBName = os.environ['TABLE_NAME']
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
    logger.info('invoke event %s' % json.dumps(event, indent=4, cls=DecimalEncoder))

    try:
        response = dynamodb.query(ScanIndexForward=True,
                                    ExpressionAttributeValues={
                                        ':v1': {
                                            # Id here represent per hackathon
                                            'S': '6049798849b3438f8f0cfcd7531fa81a',
                                            # uncomment when integration
                                            #'S': event['queryStringParameters']['Id']
                                        },
                                    },
                                    KeyConditionExpression='Id = :v1',
                                    # ProjectionExpression='SongTitle',
                                    TableName=dynamoDBName,)
    except ClientError as e:
        logger.info(e.response['Error']['Message'])
    else:
        logger.info("query item successful")
        logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))
        
        jitem = jsonU.loads(response['Items'])
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        'body': (json.dumps(jitem, indent=4, ensure_ascii=False))
    }
