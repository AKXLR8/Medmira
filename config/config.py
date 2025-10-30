import os
from dotenv import load_dotenv
load_dotenv

class Config:
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS','api.json')


    MONGO_URL = os.getenv('MONGO_URL','mongodb://localhost:27017/')
    DATABASE_NAME = os.getenv('DATABASE_NAME','akshayDB')

    collections = os.getenv('collections','prescriptions')
  


    supported_formats = ['.jpg','.jpeg','.png','.pdf']
    max = 100*1024*1024 #10mb


