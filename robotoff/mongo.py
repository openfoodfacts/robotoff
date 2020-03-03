from pymongo import MongoClient

from robotoff import settings

mongo_client = MongoClient(settings.MONGO_URI)
