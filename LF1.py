import boto3
import math
import dateutil.parser
import datetime
import time
import os
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
SQS = boto3.client("sqs")

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

def getQueueURL():
    """Retrieve the URL for the configured queue name"""
    q = 'https://sqs.us-east-1.amazonaws.com/705981116321/Q1'
    return q
   
def record(slots):
    """The lambda handler"""
    logger.debug("Recording with event %s", slots)
    #data = slots.get('data')
    try:
        #logger.debug("Recording %s", data)
        u = getQueueURL()
        logging.debug("Got queue URL %s", u)
        resp = SQS.send_message(
            QueueUrl=u,
            MessageBody="Dining Concierge message from LF1 ",
            MessageAttributes={
                "Location": {
                    "StringValue": slots["Location"]['value']['interpretedValue'],
                    "DataType": "String"
                },
                "Cuisine": {
                    "StringValue": slots["Cuisine"]['value']['interpretedValue'],
                    "DataType": "String"
                },
                "DiningDate" : {
                    "StringValue": slots["Date"]['value']['interpretedValue'],
                    "DataType": "String"
                },
                "DiningTime" : {
                    "StringValue": slots["DiningTime"]['value']['interpretedValue'],
                    "DataType": "String"
                },
                "NumberOfPeople" : {
                    "StringValue": slots["NumberOfPeople"]['value']['interpretedValue'],
                    "DataType": "String"
                },
                "PhoneNumber" : {
                    "StringValue": slots["PhoneNumber"]['value']['interpretedValue'],
                    "DataType": "String"
                }
            }
        )
        logger.debug("Send result: %s", resp)
    except Exception as e:
        raise Exception("Could not record link! %s" % e)

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'slotToElicit': slot_to_elicit,
                'type': 'ElicitSlot'
            },
            'intent': {
                'name': intent_name,
                'slots': slots,
            }
        },
        'messages': [message]
    }


def close(session_attributes, fulfillment_state, message, name):
    response = {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': name,
                'state': fulfillment_state
            }
        },
        'messages': [message]
    }

    return response


def delegate(session_attributes, slots, name):
    return 
    {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate'
            },
            'intent': {
                'name': name,
                'slots': slots
            }
        }
    }
   
""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False
       
def validate_dining_suggestions(location, diningtime, diningdate, cuisine, numberofpeople, phonenumber):
    locations = ['manhattan', 'queens', 'brooklyn', 'bronx', 'staten island']
    if location is not None and location.lower() not in locations:
        return build_validation_result(False,
                                       'Location',
                                       'We do not have suggestions in {}, would you like to try a different location?  '
                                       'Our most popular location is Manhattan'.format(location))

    if diningdate is not None:
        if not isvalid_date(diningdate):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like to find a restaurant for?')
        elif datetime.datetime.strptime(diningdate, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'Date', 'You can make reservations from tomorrow onwards.  What day would you like to make a reservation for?')

    if diningtime is not None:
        if len(diningtime) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'DiningTime', None)

        hour, minute = diningtime.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'DiningTime', None)

        if hour < 11 or hour > 22:
            # Outside of business hours
            return build_validation_result(False, 'DiningTime', 'Our restaurants are only open for reservations between 11 am and 10 pm. Can you please specify a time during this range?')

    if numberofpeople is not None and not numberofpeople.isnumeric():
        return build_validation_result(False,
                                       'NumberOfPeople',
                                       'That is not a valid party size., '
                                       'Please try again.'.format(numberofpeople))
   
    # if phonenumber is not None and not phonenumber.isnumeric():
    #     return build_validation_result(False,
    #                                   'PhoneNumber',
    #                                   'That is not a valid phone number., '
    #                                   'Please try again.'.format(phonenumber))    
                                       
    return build_validation_result(True, None, None)


def suggest(intent_request):
    slots = intent_request['sessionState']['intent']['slots']
    location = slots['Location']['value']['interpretedValue']
    diningtime = slots['DiningTime']['value']['interpretedValue']
    cuisine = slots['Cuisine']['value']['interpretedValue']
    diningdate = slots['Date']['value']['interpretedValue']
    numberofpeople = slots['NumberOfPeople']['value']['interpretedValue']
    phonenumber = slots['PhoneNumber']['value']['interpretedValue']
    #confirmation_status = intent_request['currentIntent']['confirmationStatus']
    session_attributes = intent_request['sessionState']['sessionAttributes'] if intent_request['sessionState']['sessionAttributes'] is not None else {}
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggestions(location, diningtime, diningdate, cuisine, numberofpeople, phonenumber)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the session attributes back.
        output_session_attributes = intent_request['sessionState']['sessionAttributes'] if intent_request['sessionState']['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request), "DiningSuggestionsIntent")
   
    # Fulfill the dining suggestions, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.

    record(slots)
    return close(intent_request['sessionState']['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'You\'re all set. Expect my suggestions shortly! Have a good day.'}, "DiningSuggestionsIntent")

   
def greeting(intent_request):
    return close(intent_request['sessionState']['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hello there! What can I help you with today?'}, "GreetingIntent")    
   
def thank(intent_request):
    return close(intent_request['sessionState']['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'You\'re welcome.'}, "ThankYouIntent")

""" --- Dispatch intents --- """

def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
   
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['sessionId'], intent_request['sessionState']['intent']['name']))

    intent_name = intent_request['sessionState']['intent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return greeting(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thank(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return suggest(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

""" --- Main handler --- """

def lambda_handler(event, context):
    #msg_from_user = event['messages'][0]
    # change this to the message that user submits on
    # your website using the 'event' variable
    #msg_from_user = "Hello"
    #print(f"Message from frontend: {msg_from_user}")
    # Initiate conversation with Lex
    #response = client.recognize_text(
    #        botId='2QV4ZAIFXV', # MODIFY HERE
    #        botAliasId='2XV03FHRWS', # MODIFY HERE
    #        localeId='en_US',
    #        sessionId='testuser',
    #        text=msg_from_user)
   
    #msg_from_lex = response.get('messages', [])
    #if msg_from_lex:
       
    #    print(f"Message from Chatbot: {msg_from_lex[0]['content']}")
    #    print(response)
    #    resp = {
            #'statusCode': 200,
            #'body': "Hello from LF0!"
        #}
        # modify resp to send back the next question Lex would ask from the user
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

        #logger.debug('event.bot.name={}'.format(event['bot']['name']))
        # format resp in a way that is understood by the frontend
        # HINT: refer to function insertMessage() in chat.js that you uploaded
        # to the S3 bucket
    return dispatch(event)
