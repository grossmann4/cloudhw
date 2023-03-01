import boto3
import json
import logging

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime',region_name='us-east-1')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    logger.debug(type(event['messages']))
    msg_from_user = event['messages']
    logger.debug(msg_from_user[0]['unstructured']['text'])
    
    # change this to the message that user submits on 
    # your website using the 'event' variable
    # msg_from_user = "Hello"
    print(f"Message from frontend: {msg_from_user}")
    # Initiate conversation with Lex
    response = client.recognize_text(
            botId='IJO9DTXWRF', # MODIFY HERE
            botAliasId='TSTALIASID', # MODIFY HERE
            localeId='en_US',
            sessionId='testuser',
            text=msg_from_user[0]['unstructured']['text'])
    
    msg_from_lex = response.get('messages', [])
    if msg_from_lex:
        
        print(f"Message from Chatbot: {msg_from_lex[0]['content']}")
        print(response)
        
        
        # modify resp to send back the next question Lex would ask from the user
        
        # format resp in a way that is understood by the frontend
        # HINT: refer to function insertMessage() in chat.js that you uploaded
        # to the S3 bucket
        return {
            'statusCode': 200,
        "messages": [
        {
        "type": "unstructured",
        "unstructured": {
          "id": 1,
          "text":  msg_from_lex[0]['content'],
          "timestamp": "28-02-2023"
        }
      }
    ]
  }
