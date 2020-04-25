from pymongo import MongoClient


file_path = 'farzi'
client = MongoClient()
db = client.phase3

sentiment = 'positive'
collection_name = '{}'.format(file_path.replace('.', '_'))

i = 0
db[collection_name].insert(
    {
        "tweet": 'random_bitch_{}'.format(i),
        "sentiment": sentiment
    }
)
