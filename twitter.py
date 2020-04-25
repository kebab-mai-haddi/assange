import configparser
import json
import logging
import re
import datetime
from hashlib import sha1

import pandas as pd
import tweepy
from pymongo import MongoClient

from watson import Watson

logger = logging.getLogger('streaming')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('streaming.log')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)


def convert_hashtags_dict_to_list(hashtag_dict):
    hashtag_list = []
    for key in hashtag_dict:
        hashtag_list.append(hashtag_dict[key])

    return hashtag_list


class StreamListener(tweepy.StreamListener):
    '''Streaming Class'''

    def __init__(self, api, file_name):
        self.api = api
        self.file_name = file_name
        self.tweet = {}
        self.idSelf = 0
        self.tweets = []
        self.watson = Watson()
        self.columns = [
            'Keyword',
            'Sentiment',
            'Score'
        ]
        self.loop_counter = 0
        self.client = MongoClient()
        self.db = self.client['phase3']
        self.db_collection = self.file_name
        self.db_data = []

    def write_tweet_to_file(self, file_data):
        df = pd.DataFrame(file_data, columns=self.columns)
        df.to_csv(self.file_name, mode="a", index=False, header=False)

    def write_tweet_to_database(self, file_data):
        try:
            self.db[self.file_name].insert_many(file_data, ordered=False)
        except Exception as e:
            logger.warn(e)
            pass

    def analyze_tweet(self, tweet):
        tweet_analysis = self.watson.set_response(tweet["tweet"])
        file_data = {}
        sentiment_score = tweet_analysis['sentiment']['document']['score']
        sentiment_label = tweet_analysis['sentiment']['document']['label']
        entities = []
        for entity in tweet_analysis['entities']:
            if entity['type'] != 'Person':
                continue
            entities.append(
                entity['text']
            )
        file_data["tweet"] = tweet["tweet"]
        file_data["sentiment_label"] = sentiment_label
        file_data["sentiment_score"] = sentiment_score
        file_data["entities"] = entities
        file_data["tweet_hash"] = sha1(
            tweet["tweet"].encode('utf-8')).hexdigest()
        file_data["timestamp"] = tweet["timestamp"]
        self.db_data.append(file_data)
        if len(self.db_data) == 100:
            self.write_tweet_to_database(self.db_data)
            self.db_data = []
        if not file_data:
            # logger.info("No person entities were found.")
            return

    def on_status(self, status):
        if status.retweeted:
            return
        if status.truncated:
            tweetText = status.extended_tweet['full_text']
        else:
            tweetText = status.text
        tweetText = tweetText.encode('utf8').decode('utf8')
        # logger.info("Tweet text is: {}".format(tweetText))
        try:
            self.idSelf += 1
            self.tweet["tweet"] = tweetText
            self.tweet["timestamp"] = status.created_at
        except Exception as e:
            logging.info("Error inside status")
            logging.error(e)
        finally:
            tweet = {
                "tweet": self.tweet["tweet"], "timestamp": self.tweet['timestamp']
            }
            self.analyze_tweet(tweet)
        # if self.loop_counter % 100 == 0:
            # logger.info('{} loops over.'.format(self.loop_counter))
        # self.loop_counter += 1

    def on_error(self, status_code):
        logging.error(status_code)
        return True


if __name__ == '__main__':
    # Setup logging

    config = configparser.ConfigParser()
    config.read('config.txt')

    # Read Twitter Credentials
    consumer_key = config['TWITTER']['consumerKey']
    consumer_secret = config['TWITTER']['consumerSecret']
    access_key = config['TWITTER']['accessToken']
    access_secret = config['TWITTER']['accessTokenSecret']

    # Auth Object
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    logger.info("Twitter API Auth successful")

    # Streaming Config
    # hash_tags_dict = dict(config['HASHTAGS'].items())
    # collection = config['FIXTURE']['collection']

    # hash_tags_to_track = convert_hashtags_dict_to_list(hash_tags_dict)
    hash_tags_to_track = input("Please enter the topic name: \n")
    hash_tags_to_track = [ hash_tags_to_track ]
    logger.info("Tracking %s", hash_tags_to_track)

    # Finally Streaming
    loop_counter = 0
    while loop_counter < 1000000:
        loop_counter += 1
        # logger.info('{} loops over.'.format(loop_counter))
        try:
            logger.info("Trying")
            stream = tweepy.Stream(
                auth=api.auth,
                listener=StreamListener(
                    api=api, file_name='{}'.format(
                        hash_tags_to_track[0]
                    )
                )
            )
            logger.info("Connection Made")
            stream.filter(languages=["en"], track=hash_tags_to_track)
        except Exception as e:
            logger.error(e)
