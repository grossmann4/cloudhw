import json
import boto3
import logging

def lambda_handler(event, context):
    client = boto3.client('lexv2-runtime')
    #message = "Hello"
    msg_from_user = event['messages'][0]['content']
    
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
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type, Origin, X-Auth-Token',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': {
            "messages": [
                {
                    "type": "unstructured",
                    "unstructured": {
                        "id": "1",
                        "text": msg_from_lex
                    }
                }
            ]

        }
    }
    
            # modify resp to send back the next question Lex would ask from the user
        
        # format resp in a way that is understood by the frontend
        # HINT: refer to function insertMessage() in chat.js that you uploaded
        # to the S3 bucket
    
        
