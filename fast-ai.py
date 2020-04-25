import configparser
import io
import os
from functools import partial
from hashlib import sha1

import fastai
import nltk
import numpy as np
import pandas as pd
from fastai import *
from fastai.text import *
from nltk.corpus import stopwords
from pymongo import MongoClient
from sklearn.datasets import fetch_20newsgroups
from sklearn.model_selection import train_test_split

file_path = input('Please enter path of the file.\n')
df = pd.read_csv(
    filepath_or_buffer=file_path,
    header=None
)

# CATEGORISING THE SENTIMENT TABLE
# NEUTRAL -> 0 | NEGATIVE -> 1 | POSITIVE -> 2
df[1] = df[1].astype('category')
df[1] = df[1].cat.codes

# NUMBER OF SAMPLES FOR EACH CATEGORY
print(df[1].value_counts())

#df = pd.DataFrame({'label':dataset.target, 'text':dataset.data})
df = pd.DataFrame({'label': df[1], 'text': df[0]})
print(df.shape)

df['text'] = df['text'].str.replace("[^a-zA-Z]", " ")
print(df.head(5))

nltk.download('stopwords')
stop_words = stopwords.words('english')

# tokenization
tokenized_doc = df['text'].apply(lambda x: x.split())

# remove stop-words
tokenized_doc = tokenized_doc.apply(
    lambda x: [item for item in x if item not in stop_words])

# de-tokenization
detokenized_doc = []
for i in range(len(df)):
    t = ' '.join(tokenized_doc[i])
    detokenized_doc.append(t)

df['text'] = detokenized_doc


df_trn, df_val = train_test_split(
    df, stratify=df['label'], test_size=0.15, random_state=12)
print(df_trn.shape, df_val.shape)


# Language model data
data_lm = TextLMDataBunch.from_df(train_df=df_trn, valid_df=df_val, path="")

# Classifier model data
data_clas = TextClasDataBunch.from_df(
    path="", train_df=df_trn, valid_df=df_val, vocab=data_lm.train_ds.vocab, bs=32)


learn = language_model_learner(data_lm, arch=AWD_LSTM, drop_mult=0.7)

# train the learner object with learning rate = 1e-2
learn.fit_one_cycle(1, 1e-2)

learn.save_encoder('ft_enc')


learn = text_classifier_learner(data_clas, arch=AWD_LSTM, drop_mult=0.7)
learn.load_encoder('ft_enc')


learn.fit_one_cycle(1, 1e-2)


# get predictions
preds, targets = learn.get_preds()

predictions = np.argmax(preds, axis=1)
pd.crosstab(predictions, targets)

config = configparser.ConfigParser()
config.read('config.txt')
hash_tags_dict = dict(config['HASHTAGS'].items())
for key in hash_tags_dict.keys():
    source_collection = hash_tags_dict[key]


client = MongoClient()
db = client.phase3

file_path = os.path.basename(file_path)
collection_name = '{}'.format(file_path.replace('.', '_'))

for i in range(1, len(df_val)+1):
    tweet = df_val[i-1:i]['text'].array[0]
    neutral = preds[i-1:i][0][0]
    negative = preds[i-1:i][0][1]
    positive = preds[i-1:i][0][2]
    if neutral > positive and neutral > negative:
        sentiment = 'neutral'
    elif negative > neutral and negative > positive:
        sentiment = 'negative'
    else:
        sentiment = 'positive'
    db[collection_name].insert_one(
        {
            "tweet": tweet,
            "sentiment": sentiment
        }
    )
    if i % 100 == 0:
        print(i)
