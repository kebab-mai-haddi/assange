import json

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_watson.natural_language_understanding_v1 import (CategoriesOptions,
                                                          Features, EntitiesOptions, KeywordsOptions, SentimentOptions)
import configparser


class Watson:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.txt')
        api_key = config['WATSON']['api_key']
        self.authenticator = IAMAuthenticator(
            api_key)
        self.natural_language_understanding = NaturalLanguageUnderstandingV1(
            version='2019-07-12', authenticator=self.authenticator)

    def set_response(self, tweet_text):
        response = self.natural_language_understanding.analyze(
            text=tweet_text,
            features=Features(
                sentiment=SentimentOptions(
                    document=True
                ),
                entities=EntitiesOptions(sentiment=True)
            ),
            language='en'
        ).get_result()
        return response


# watson = Watson()
# print(watson.set_response('Modi will make India come out of COVID-19 crisis!'))
