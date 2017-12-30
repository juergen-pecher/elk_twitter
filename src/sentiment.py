import json
import logging
import logging.handlers
import tweepy
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from textblob import TextBlob
from elasticsearch import Elasticsearch

# import twitter keys and tokens
from config import *

# enable logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# elastic logging
es_logger = logging.getLogger('elasticsearch')
es_logger.setLevel(logging.INFO)

# enable debugging
tweepy.debug()

# create instance of elasticsearch
es = Elasticsearch(
    hosts=[{'host': elastic_host, 'port': elastic_port}]
)

class TweetStreamListener(StreamListener):

    # on success
    def on_data(self, data):

        # decode json
        dict_data = json.loads(data)
        # uncomment the following line for debugging purposes
        # logger.info(dict_data)

        # pass tweet into TextBlob
        tweet = TextBlob(dict_data["text"])

        # determine if sentiment is positive, negative, or neutral
        if tweet.sentiment.polarity < 0:
            sentiment = "negative"
        elif tweet.sentiment.polarity == 0:
            sentiment = "neutral"
        else:
            sentiment = "positive"

        # uncomment the following line for debugging purposes
        # logger.info(sentiment)


        # add text and sentiment info to elasticsearch
        es.index(index="ektdemo",
                 doc_type="tweet",
                 body={"author": dict_data["user"]["screen_name"],
                       "date": dict_data["created_at"],
                       "message": dict_data["text"],
                       "tweet_id": dict_data["id_str"],
                       "tweet_timestamp_ms": dict_data["timestamp_ms"],
                       "tweet_date": dict_data["created_at"],
                       "is_quote_status": dict_data["is_quote_status"],
                       "in_reply_to_status_id": dict_data["in_reply_to_status_id"],
                       "in_reply_to_screen_name": dict_data["in_reply_to_screen_name"],
                       "favorite_count": dict_data["favorite_count"],
                       "author": dict_data["user"]["screen_name"],
                       "tweet_text": dict_data["text"],
                       "retweeted": dict_data["retweeted"],
                       "retweet_count": dict_data["retweet_count"],
                       "geo": dict_data["geo"],
                       "place": dict_data["place"],
                       "coordinates": dict_data["coordinates"],
                       "polarity": tweet.sentiment.polarity,
                       "subjectivity": tweet.sentiment.subjectivity,
                       "sentiment": sentiment})
        return True

    # on failure
    def on_error(self, status_code):
        logger.warning(status_code)
        if status_code == 420:
            #returning False in on_data disconnects the stream
            return False

if __name__ == '__main__':

    # create instance of the tweepy tweet stream listener
    listener = TweetStreamListener()

    # set twitter keys/tokens
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    # create instance of the tweepy stream
    stream = Stream(auth, listener)
    # uncomment the following line for debugging purposes
    # logger.info("Twitter API Connection opened")

    # search twitter for keywords
    stream.filter(
        track=filter_words,
        languages=filter_languages
        )
