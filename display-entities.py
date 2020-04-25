from pymongo import MongoClient
from collections import defaultdict


client = MongoClient()
db = client["phase3"]

positive = defaultdict(int)
negative = defaultdict(int)
neutral = defaultdict(int)


print("Following are the topics in the repository: ")
for collection_ in db.list_collection_names():
    if "csv" in collection_:
        continue
    print(collection_)

topic = input(
    "Please enter the name of the topic for which you want entities' analysis \n")
collection = topic

entity_set = set()

rows = db[collection].find()

for row in rows:
    entities = row["entities"]
    sentiment = row["sentiment_label"]
    if sentiment == 'positive':
        for entity in entities:
            positive[entity] += 1
            entity_set.add(entity)
    elif sentiment == 'negative':
        for entity in entities:
            negative[entity] += 1
            entity_set.add(entity)
    else:
        for entity in entities:
            neutral[entity] += 1
            entity_set.add(entity)

print('Entity    |    Positive    |    Negative    |    Neutral')
for entity in entity_set:
    print(entity, positive.get(entity, 0), negative.get(
        entity, 0), neutral.get(entity, 0))
