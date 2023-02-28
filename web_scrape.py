import yelpapi
from yelpapi import YelpAPI
import json
import boto3
from decimal import Decimal
import requests
import datetime
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table("yelp-restaurants")

region = 'us-east-1'
service = 'es'

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-restaurant-abarocnh7j6sf2dw5gbwnyyzsq.us-east-1.es.amazonaws.com'

index = 'restaurants'

type = 'restaurant'

url = host + '/' + index + '/_doc'

headers = { "Content-Type": "application/json" }

# # write private api_key to access yelp here
api_key = 'jmwQyjyE9RSslx70g0fdFYqV2J17onKFxQJdGZhQUaRA-yiFL-tW83YrbWFUO8VTBeXdsrAN4gyo2nBeNtkg6m-vt4LdXrANwETy7KN5PSeunv0Ob_DDXRbSTHv6Y3Yx'

yelp_api = YelpAPI(api_key)

data = ['id', 'name', 'review_count', 'rating', 'coordinates', 'display_address', 'zip_code', 'phone']
es_data = ['id']

cuisines = ["chinese", "indian", "mexican", "american", "italian"]

COUNT = 1

def populate_database(response, cuisine):
    print(response)
    json_response = json.loads(json.dumps(response), parse_float=Decimal)
    print(json_response["businesses"][0])
    for restaurant in json_response["businesses"]:
        dict = {'restaurant_id':restaurant['id']}
        dict['name'] = restaurant.get('name', '')
        dict['review_count'] = restaurant.get('review_count', 0) 
        dict['rating'] = restaurant.get('rating', 0) 
        dict['coordinates'] = restaurant.get('coordinates', {}) 
        dict['display_address'] = restaurant.get('location', '').get('display_address','')
        dict['zipcode'] = restaurant.get('location', '').get('zipcode','')
        dict['phone'] = restaurant.get('phone', '') 
        dict['cuisine'] = cuisine
        dict['insertedAtTimestamp'] = str(datetime.datetime.now())
        
        # print(dict)
        # table.put_item(Item=dict)
        es_dict = { 'restaurant_id': dict['restaurant_id'], 'cuisine':cuisine}

        docs = json.loads(json.dumps(es_dict))
        
        print(docs)
        r = requests.post(url, auth= awsauth, json=docs, headers=headers)
        print(r.text)
        

    
def lambda_handler(event=None, context=None):
    limit = 50
    for cuisine in cuisines:
        for x in range(0, 1000, 50):
            response = yelp_api.search_query(term=cuisine, location='Manhattan', limit=limit, offset=x)
            populate_database(response, cuisine)
    
    # print('Received event: ' + json.dumps(event))
    # results = query('American')
    # return {
    #     'statusCode': 200,
    #     'headers': {
    #         'Content-Type': 'application/json',
    #         'Access-Control-Allow-Headers': 'Content-Type',
    #         'Access-Control-Allow-Origin': '*',
    #         'Access-Control-Allow-Methods': '*',
    #     },
    #     'body': json.dumps({'results': results})
    # }
