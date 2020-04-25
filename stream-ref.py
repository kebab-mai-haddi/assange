# -*- coding: utf-8 -*-
import logging
import re
import configparser
from kafka import KafkaProducer
from kafka.errors import KafkaError
import tweepy

# Logging Config
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
####


def check_for_http_and_https(text):
    httpsCheck = 'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    httpCheck = 'http?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'

    if(re.findall(httpCheck, text) or re.findall(httpsCheck, text)):
        return True
    else:
        return False


def convert_hashtags_dict_to_list(hashtag_dict):
    hashtag_list = []
    for key in hashtag_dict:
        hashtag_list.append(hashtag_dict[key])

    return hashtag_list


class StreamListener(tweepy.StreamListener):
    '''Streaming Class'''

    def __init__(self, api, kafka_topic):
        self.api = api
        self.kafka_topic = kafka_topic
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'], retries=5)
        self.tweet = {}
        self.idSelf = 0

    def on_status(self, status):
        if status.retweeted:
            return
        tweetText = status.text.encode('utf8')
        if (check_for_http_and_https(tweetText)):
            return
        try:
            self.idSelf += 1
            self.tweet["userProfileImageURL"] = status.user._json[
                "profile_image_url_https"]
            self.tweet["tweet"] = tweetText
            self.tweet["id"] = status.id
            self.tweet["sequence"] = self.idSelf
            self.tweet["timestamp"] = status.created_at

            logger.info("Tweet sequence: %d", self.idSelf)
            self.producer.send(self.kafka_topic, bytes(
                str(self.tweet).encode('utf8')))

        except Exception as e:
            logging.info("Error inside status")
            logging.error(e)
        finally:
            self.producer.flush()

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
    hash_tags_dict = dict(config['HASHTAGS'].items())
    collection = config['FIXTURE']['collection']

    hash_tags_to_track = convert_hashtags_dict_to_list(hash_tags_dict)
    logger.info("Tracking %s", hash_tags_to_track)

    # Finally Streaming
    while True:
        try:
            stream = tweepy.Stream(
                auth=api.auth, listener=StreamListener(api=api, kafka_topic=collection))
            logger.info("Connection Made")
            stream.filter(languages=["en"], track=hash_tags_to_track)
        except Exception as e:
            logger.error(e)