import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    client = boto3.client('lexv2-runtime')
    #message = "Hello"
    msg_from_user = event['body']
    
    response = client.recognize_text(
        botId='2QV4ZAIFXV', # MODIFY HERE
        botAliasId='TSTALIASID', # MODIFY HERE
        localeId='en_US',
        text=msg_from_user,
        sessionId='testuser')
    
        
    msg_from_lex = response.get('messages', [])
    #print("/n")
    # print(response)
    #print(type(msg_from_lex))

    
     return {
            'statusCode': 200,
            "messages": [{"type": "unstructured", 
                        "unstructured": {
                            "id": "id",
                            "text": msg_from_lex[0]['content'],
                            "timestamp": "timestamp"
                        }
                
                    }
                ]
        }
    
            # modify resp to send back the next question Lex would ask from the user
        
        # format resp in a way that is understood by the frontend
        # HINT: refer to function insertMessage() in chat.js that you uploaded
        # to the S3 bucket
    
        
