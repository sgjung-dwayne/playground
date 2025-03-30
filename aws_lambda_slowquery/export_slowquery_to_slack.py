import boto3 
import json 
import logging 
import os 
import datetime 
import base64 
import gzip 
import re 
from base64 import b64decode 
from urllib.request import Request, urlopen 
from urllib.error import URLError, HTTPError 
# The base-64 encoded, encrypted key (CiphertextBlob) stored in the kmsEncryptedHookUrl environment variable 
ENCRYPTED_HOOK_URL = os.environ['kmsEncryptedHookUrl'] 
# The Slack channel to send a message to stored in the slackChannel environment variable 
SLACK_CHANNEL = os.environ['slackChannel'] 
HOOK_URL = "https://" + boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_HOOK_URL),EncryptionContext={'LambdaFunctionName': os.environ['AWS_LAMBDA_FUNCTION_NAME']})['Plaintext'].decode('utf-8') 
logger = logging.getLogger() 
logger.setLevel(logging.INFO) 
def lambda_handler(event, context): 
     
     
    cw_data = event['awslogs']['data'] 
    compressed_event = base64.b64decode(cw_data) 
    uncompressed_event = gzip.decompress(compressed_event) 
    event = json.loads(uncompressed_event) 
    message = event['logEvents'][0]['message'] 
    # RDS 인스턴스명 
    rds_instance = event['logStream'] 
    # Time 변경 UTC -> KST 
    alert_time = re.findall('# Time: (.+)\\.[0-9]', message) 
    alert_time = alert_time[0] 
    alert_time = datetime.datetime.strptime(alert_time,'%Y-%m-%dT%H:%M:%S') 
    alert_time = alert_time + datetime.timedelta(hours=9) 
     
    # User@Host 추출 
    alert_host = re.findall('# User@Host: (.+)Id', message)[0].replace(" ","") 
    alert_host = re.findall('\\[(\w.+)]', alert_host)[0] 
    alert_host = alert_host.replace("]","").replace("[","") 
     
    # Query Time 추출 
    alert_query_time = re.findall('# Query_time: (.+) Lock', message)[0].replace(" ","") 
     
    # Rows Sent 추출 
    alert_rows_sent = re.findall('Rows_sent:(.+) Rows_examined', message)[0].replace(" ","") 
     
    # Rows Examined 추출 
    alert_rows_examined = re.findall('Rows_examined:(.+)', message)[0].replace(" ","") 
     
    # Slow Query 추출 
    alert_slow_query_pos = message.rfind('SET timestamp') 
    alert_slow_query_pos = message[alert_slow_query_pos:].find(';\n') + alert_slow_query_pos + 2 
    alert_slow_query = message[alert_slow_query_pos:] 
   
    slack_message = { 
        'channel': SLACK_CHANNEL, 
        "text": "Cloudwatch TO Slack", 
        "blocks": [ 
            { 
                "type": "section", 
                "text": { 
                    "type": "mrkdwn", 
                    "text": "*%s*\n>*AlertTime* : %s\n>*User@Host* : %s\n>*QueryTime* : %s\n>*RowSent* : %s\t*RowExamined* : %s\n>*SlowQuery* :\n%s" % (rds_instance,alert_time,alert_host,alert_query_time,alert_rows_sent,alert_rows_examined,alert_slow_query) 
                } 
            } 
        ] 
    } 
     
    req = Request(HOOK_URL, json.dumps(slack_message).encode('utf-8')) 
      
    try: 
        response = urlopen(req) 
        response.read() 
        logger.info("Message posted to %s", slack_message['channel']) 
    except HTTPError as e: 
        logger.error("Request failed: %d %s", e.code, e.reason) 
    except URLError as e: 
        logger.error("Server connection failed: %s", e.reason)