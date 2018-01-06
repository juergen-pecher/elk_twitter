import json
import logging
import logging.handlers
import tweepy
import datetime
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
# tweepy.debug()

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
        if tweet.sentiment.polarity < -0.25:
            sentiment = "negative"
        elif  -0.25 <= tweet.sentiment.polarity <= 0.25:
            sentiment = "neutral"
        else:
            sentiment = "positive"

        # uncomment the following line for debugging purposes
        # logger.info(sentiment)

        # date-formated variable for weekly indexes in elasticsearch
        now = datetime.datetime.now()
        index_suffix = now.strftime("-%Y-%m-%U")

        # date-formated variable for weekly indexes in elasticsearch
        # we need the format yyyy/MM/dd HH:mm:ss Z
        created_temp = datetime.datetime.utcfromtimestamp(float(dict_data["timestamp_ms"]) / 1e3)
        created = created_temp.strftime("%Y/%m/%d %H:%M:%S")

        # index settings and mappings
        createindex_body = {
            'settings': {
                'number_of_shards': 5,
                'number_of_replicas': 1
            },
            'mappings': {
                'tweet': {
                    'date_detection': True,
                    'properties': {
                        'date_formated': { 'type': 'date', 'format': 'yyyy/MM/dd HH:mm:ss' },
                    }
                }
            }
        }

        if 'retweeted_status' in dict_data:
            id_origin = dict_data["retweeted_status"]["id_str"]
            doc_exists = es.exists(index=elastic_index + index_suffix,
                                   doc_type="tweet",
                                   id=id_origin,
                                   )
            docindex_body = {"user": dict_data["retweeted_status"]["user"],
                             "tweet_id": dict_data["retweeted_status"]["id_str"],
                             "favorite_count": dict_data["retweeted_status"]["favorite_count"],
                             "tweet_text": dict_data["retweeted_status"]["text"],
                             "retweet_count": dict_data["retweeted_status"]["retweet_count"],
                             }
        elif 'quoted_status' in dict_data:
            id_origin = dict_data["quoted_status"]["id_str"]
            doc_exists = es.exists(index=elastic_index + index_suffix,
                                   doc_type="tweet",
                                   id=id_origin,
                                   )
            docindex_body = {"user": dict_data["quoted_status"]["user"],
                             "tweet_id": dict_data["quoted_status"]["id_str"],
                             "favorite_count": dict_data["quoted_status"]["favorite_count"],
                             "tweet_text": dict_data["quoted_status"]["text"],
                             "quote_count": dict_data["quoted_status"]["quote_count"],
                             }
        else:
            id_origin = dict_data["id_str"]
            docindex_body = {"user": dict_data["user"],
                             "date": dict_data["created_at"],
                             "date_formated": created,
                             "lang": dict_data["lang"],
                             "tweet_id": dict_data["id_str"],
                             "timestamp": dict_data["timestamp_ms"],
                             "tweet_date": dict_data["created_at"],
                             "is_quote_status": dict_data["is_quote_status"],
                             "in_reply_to_status_id": dict_data["in_reply_to_status_id"],
                             "in_reply_to_screen_name": dict_data["in_reply_to_screen_name"],
                             "favorite_count": dict_data["favorite_count"],
                             "tweet_text": dict_data["text"],
                             "retweeted": dict_data["retweeted"],
                             "retweet_count": dict_data["retweet_count"],
                             "is_quote_status": dict_data["is_quote_status"],
                             "quote_count": dict_data["quote_count"],
                             "reply_count": dict_data["reply_count"],
                             "place": dict_data["place"],
                             "coordinates": dict_data["coordinates"],
                             "entities": dict_data["entities"],
                             "polarity": tweet.sentiment.polarity,
                             "subjectivity": tweet.sentiment.subjectivity,
                             "sentiment": sentiment
                             }

        # add text and sentiment info to elasticsearch
        # see for available values:
        # https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/tweet-object

        if es.indices.exists(elastic_index + index_suffix):
            if 'retweeted_status' in dict_data and doc_exists == True:
                es.update(index=elastic_index + index_suffix,
                          doc_type="tweet",
                          id=id_origin,
                          body={"doc":docindex_body}
                          )
            elif 'quoted_status' in dict_data and doc_exists == True:
                 es.update(index=elastic_index + index_suffix,
                           doc_type="tweet",
                           id=id_origin,
                           body={"doc":docindex_body}
                           )
            else:
                es.index(index=elastic_index + index_suffix,
                         doc_type="tweet",
                         id=id_origin,
                         body=docindex_body
                       )

        else:
            es.indices.create(index=elastic_index + index_suffix,
                              body = createindex_body
                              )

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
