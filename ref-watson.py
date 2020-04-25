# -*- coding: utf-8 -*-
def process_and_save_tweets_pickably(tweet_object):
    process_and_save_tweets(tweet_object)


from collections import defaultdict
import sys
import ast
import csv
import datetime
from itertools import chain
import json
from multiprocessing import Pool
import operator
import os
import re
import sys
import time
import ast

from bson import ObjectId

from kafka.errors import KafkaError
from kafka import KafkaConsumer
import pymongo
from pymongo import MongoClient
from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions, CategoriesOptions

import configparser
import logging

## ===== Logging Config ==== #
logger = logging.getLogger('processing')
logger.setLevel(logging.CRITICAL)

fh = logging.FileHandler('processing.log')
fh.setLevel(logging.CRITICAL)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

## ===================== ##

## ===== CONFIG ===  ##
config = configparser.ConfigParser()
config.read('config.txt')
fixture_id = config['FIXTURE']['collection']
trending_collection = config['FIXTURE']['trending_collection']

mongo_database = config['DB_CONFIG']['database']
fixture_collection = config['DB_CONFIG']['fixture_collection']
entities_collection = config['DB_CONFIG']['entities_collection']

watson_username = config['WATSON']['username']
watson_password = config['WATSON']['password']
## ================ ##

## === Mongo Config === ##
db = MongoClient("localhost", 27017)[mongo_database]
db[trending_collection].create_index([("sequence", -1)])
### ==================  ##

## === Watson Config === ##
natural_language_understanding = NaturalLanguageUnderstandingV1(
    username=watson_username,
    password=watson_password,
    version='2018-03-16')
### ==================== ##

fixture = db[fixture_collection].find_one({"_id": ObjectId(fixture_id)})
team_one = fixture["teamOne"]
team_two = fixture["teamTwo"]

entities_cursor = db[entities_collection].find(
    {
        "$or": [
            {"team": team_one}, {"team": team_two}, {
                "key": team_one}, {"key": team_two}
        ]
    }
)

entities = []
document_to_be_appended = {}
for entity in entities_cursor:
    splitted_key = entity["key"].split("_")
    full_name = ""
    for x in range(0, len(splitted_key) - 1):
        full_name += splitted_key[x] + " "
    full_name += splitted_key[-1]
    splitted_key.append(full_name)
    document_to_be_appended[entity["key"]] = splitted_key

entity_dict_final = defaultdict(list)
for k, v in chain(document_to_be_appended.items()):
    entity_dict_final[k].append(v)


def connect_mongo():
    return MongoClient("localhost", 27017)[mongo_database]


def analyze_from_watson(text):
    try:
        analysis = natural_language_understanding.analyze(
            text=text,
            features=Features(
                entities=EntitiesOptions(
                    emotion=True,
                    sentiment=True,
                    limit=2),
                keywords=KeywordsOptions(
                    emotion=True,
                    sentiment=True,
                    limit=2)),
            language='en'
        )

        return analysis
    except Exception as e:
        print e
        print "Error in analyzing from Watson"


def get_sentiment(sentiment_object):
    if sentiment_object["label"] == "positive":
        return sentiment_object["score"]*100
    elif sentiment_object["label"] == "negative":
        return 100*(1 - abs(sentiment_object["score"]))
    else:
        return 50


def get_max_emotion(emotion_dict):
    return max(emotion_dict.items(), key=operator.itemgetter(1))[0]


def save_tweet(tweet_object):
    try: 
        db = connect_mongo()
        db[fixture_id].insert(tweet_object)
    
    except Exception:
        logger.exception("Tweet saving failed")

def update_trending(tweet_object):
    try: 
        db = connect_mongo()
        last_object_in_trending = db[trending_collection].find({}).sort([("sequence", -1)]).limit(1)

        until_now_dict = {}
        trending_dict = {}

        key = tweet_object['key']
        sentiment = tweet_object['sentiment']

        if last_object_in_trending and key in last_object_in_trending['until_now']:
                until_now_dict[key]['count'] = last_object_in_trending[key]['count'] + 1
                until_now_dict[key]['sentiment'] = sentiment
        else:
            until_now_dict[key] = {'count': 1, 'sentiment': sentiment}

        
        trending_dict = {
        'sequence': tweet_object['sequence'],
        'timeStamp': tweet_object['timeStamp'],
        'until_now': until_now_dict,
        }

        db[trending_collection].insert(trending_dict)

    except Exception:
        logger.exception("Trending failed")
       

def process_and_save_tweets(tweet_object):

    try:
        watson_analysis = analyze_from_watson(tweet_object['tweet'])

        for entity in watson_analysis['entities']:
            if "emotion" not in entity.keys():
                logger.info("No emotion")
                continue

            for sampled_entity_key in entity_dict_final:
                for sampled_entity_key_permutation in entity_dict_final[sampled_entity_key]:
                    print "matching " + \
                        str(entity["text"]) + " with " + \
                        str(sampled_entity_key_permutation)

                    if(entity["text"] in sampled_entity_key_permutation):

                        tweet_object['emotion'] = get_max_emotion(
                            entity['emotion'])

                        tweet_object['sentiment'] = get_sentiment(
                            entity['sentiment'])

                        tweet_object['key'] = sampled_entity_key

                        save_tweet(tweet_object)
                        update_trending(tweet_object)

    except Exception as e:
        logger.exception("Processing and Saving Tweets Failed")
       


def format_raw_tweet_object_from_kakfa(raw_tweet_object_in_string):
    try:
        formatted_raw_tweet_object = raw_tweet_object_in_string.replace(
            '\n', '\\n')
        return eval(formatted_raw_tweet_object)
    except Exception as e:
        logger.exception("Formatting Error")


def check_tweet_contains_RT(text):
    return text[:2] == "RT"


def main():

    p = Pool(4)
    tweets_batch = []
    consumer = KafkaConsumer(
        fixture_id, bootstrap_servers='localhost:9092', auto_offset_reset='earliest')

    for message in consumer:

        tweet_object = format_raw_tweet_object_from_kakfa(message.value)
        if check_tweet_contains_RT(tweet_object['tweet']):
            continue

        print tweet_object
        tweets_batch.append(tweet_object)

        if(len(tweets_batch) == 4):
            p.map(process_and_save_tweets_pickably, tweets_batch)
            del tweets_batch[:]


if __name__ == "__main__":
    main()