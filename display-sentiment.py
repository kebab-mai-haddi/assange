from pymongo import MongoClient

client = MongoClient()
db = client["phase3"]

print("Following topics are available in the repository: ")
for collection_ in db.list_collection_names():
    if "csv" in collection_:
        continue
    print(collection_)

topic = input(
    "Enter the name of the topic for which you want the sentiment analysis: \n")

collection = topic.replace(' ', '_') + "_csv"

total_count = db[collection].count_documents({})
positive_count = db[collection].count_documents({"sentiment": "positive"})
negative_count = db[collection].count_documents({"sentiment": "negative"})
neutral_count = db[collection].count_documents({"sentiment": "neutral"})

positive_count_percentage = (positive_count/total_count)*100
negative_count_percentage = (negative_count/total_count)*100
neutral_count_percentage = (neutral_count/total_count)*100

print('{}% were positive, {}% were negative, and {}% were neutral tweets about {} which has a total of {} tweets'.format(
    positive_count_percentage, negative_count_percentage, neutral_count_percentage, topic, total_count))
