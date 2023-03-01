import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import logging
from boto3.dynamodb.conditions import Key, Attr
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

REGION = 'us-east-1'
INDEX = 'yelp-restaurants'
HOST = 'https://search-restaurant-abarocnh7j6sf2dw5gbwnyyzsq.us-east-1.es.amazonaws.com'

def getSQSMsg():
    SQS = boto3.client("sqs")
    url = 'https://sqs.us-east-1.amazonaws.com/751685537060/Q1'
    response = SQS.receive_message(
        QueueUrl=url, 
        AttributeNames=['SentTimestamp'],
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    try:
        message = response['Messages'][0]
        if message is None:
            logger.debug("Empty message")
            return None
    except KeyError:
        logger.debug("No message in the queue")
        return None
    message = response['Messages'][0]
    SQS.delete_message(
            QueueUrl=url,
            ReceiptHandle=message['ReceiptHandle']
        )
    logger.debug('Received and deleted message: %s' % response)
    return message
    
def query(term):
    q = {'size': 5, 'query': {'multi_match': {'query': term}}}
    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
    res = client.search(index=INDEX, body=q)
    print(res)
    hits = res['hits']['hits']
    results = []
    for hit in hits:
        results.append(hit['_source'])
    return results
        
def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                        cred.secret_key,
                        region,
                        service,
                        session_token=cred.token)

def lambda_handler(event, context):
    
    """
        Query SQS to get the messages
        Store the relevant info, and pass it to the Elastic Search
    """
    
    message = getSQSMsg() #data will be a json object
    #logger.debug(message)
    #print(message)
    if message is None:
        logger.debug("No Cuisine or PhoneNum key found in message")
        return
    cuisine = message["MessageAttributes"]["Cuisine"]["StringValue"]
    location = message["MessageAttributes"]["Location"]["StringValue"]
    date = message["MessageAttributes"]["DiningDate"]["StringValue"]
    time = message["MessageAttributes"]["DiningTime"]["StringValue"]
    numOfPeople = message["MessageAttributes"]["NumberOfPeople"]["StringValue"]
    phoneNumber = message["MessageAttributes"]["PhoneNumber"]["StringValue"]
    #phoneNumber = "+1" + phoneNumber
    if not cuisine or not phoneNumber:
        logger.debug("No Cuisine or PhoneNum key found in message")
        return
    
    """
        Query database based on elastic search results
        Store the relevant info, create the message and sns the info
    """
    
    es_query = "https://search-restaurant-abarocnh7j6sf2dw5gbwnyyzsq.us-east-1.es.amazonaws.com/_search?q={cuisine}".format(
        cuisine=cuisine)
    
    headers = { "Content-Type": "application/json" }
    r = requests.get(es_query, auth=get_awsauth(REGION, 'es'), headers=headers)

    res = r.json()
    print(res)
    noOfHits = res['hits']['total']
    hits = res['hits']['hits']

    
    # extract bID from AWS ES
    ids = []
    for restaurant in hits:
        if "restaurant_id" in restaurant["_source"]:
            ids.append(restaurant["_source"]["restaurant_id"])
        else:
            ids.append(restaurant["_source"]["restaurant-id"])
    
    messageToSend = 'Hello! Here are my {cuisine} restaurant suggestions in {location} for {numPeople} people, for {diningDate} at {diningTime}: '.format(
            cuisine=cuisine,
            location=location,
            numPeople=numOfPeople,
            diningDate=date,
            diningTime=time,
        )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    itr = 1
    for id in ids:
        if itr == 3:
            break
        response = table.scan(FilterExpression=Attr('restaurant_id').eq(id))
        print(response)
        item = response['Items'][0]
        if response is None:
            continue
        restaurantMsg = '' + str(itr) + '. '
        name = item["name"]
        address = item["display_address"][0]
        restaurantMsg += name +', located at ' + address +'. '
        messageToSend += restaurantMsg
        itr += 1
        
    messageToSend += "Enjoy your meal!!"
    print("/n" + messageToSend)
    
    # try:
    #     client = boto3.client('ses', region_name= 'us-east-1')
    #     response = client.publish(
    #         PhoneNumber=phoneNumber,
    #         Message= messageToSend,
    #         MessageStructure='string'
    #     )
    # except KeyError:
    #     logger.debug("Error sending ")
    # logger.debug("response - %s",json.dumps(response) )
    # logger.debug("Message = '%s' Phone Number = %s" % (messageToSend, phoneNumber))
    
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = "grossmann.6@osu.edu"
    
    # Replace recipient@example.com with a "To" address. If your account 
    # is still in the sandbox, this address must be verified.
    RECIPIENT = phoneNumber
    
    # Specify a configuration set. If you do not want to use a configuration
    # set, comment the following variable, and the 
    # ConfigurationSetName=CONFIGURATION_SET argument below.
    #CONFIGURATION_SET = "ConfigSet"
    
    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "us-east-1"
    
    # The subject line for the email.
    SUBJECT = "Your Dining Suggestions"
    
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = messageToSend
    
    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>Amazon SES Test (SDK for Python)</h1>
      <p> {messageToSend} </p>
    </body>
    </html>""".format(messageToSend=messageToSend)            
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            #ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    
    return {
        'statusCode': 200,
        'body': json.dumps("LF2 running succesfully")
    }
    # return messageToSend
    
