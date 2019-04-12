import twitter, re, json, requests, time
from datetime import datetime

# NLP tools
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import TweetTokenizer
from nltk.corpus import wordnet
lemma = WordNetLemmatizer()
token = TweetTokenizer()

keys = 'keys.json'
seentweets = 'seen_tweets.txt'
log = 'log.txt'

# get authorization keys
with open(keys, 'r') as infile:
    keys = json.load(infile)
    
# get last collected tweets
with open(seentweets, 'r') as infile:
    seen_tweets = infile.read().split()
    
with open(log, 'r') as infile:
    log_file = infile.read()

def closeSession(log_file, seen_tweets):
    '''
    Write final files.
    '''
    with open(log, 'w') as outfile:
        outfile.write(log_file)
    with open(seentweets, 'w') as outfile:
        outfile.write(seen_tweets)

def get_wordnet_pos(word):
    '''
    Map POS tag to first character lemmatize() accepts.
    Credit: https://www.machinelearningplus.com/nlp/lemmatization-examples-python/
    ^ which saved me some time from thinking through this...
    '''
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {'J': wordnet.ADJ,
                'N': wordnet.NOUN,
                'V': wordnet.VERB,
                'R': wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)


def parseTweet(tweetstring):
    '''
    Lemmatize and lowercase tweet text.
    Returns a set of lemmas.
    '''
    lemmas = set(lemma.lemmatize(w.lower(), get_wordnet_pos(w)) 
                  for w in token.tokenize(tweetstring))
    return lemmas


def formatTweetURL(user, status_id):
    '''
    Returns formatted URL for tweets.
    '''
    return f'https://twitter.com/{user}/status/{status_id}'

# instance Twitter-API
api = twitter.Api(**keys['twitter'], tweet_mode='extended')

# Tweet Triggers, Organized by "domain"
starship = {'starship', 'hopper', 
            'starhopper', 'raptor', 
            'engine', 'tether', 'pad', 'rocket'}
spacex = {'spacex', 'falcon', 'merlin', 
          'thrust', 'rocket', 'ton'}
testing = {'test','road', 'close', 'open', 'shut',
           'reopen', 'sheriff', 'vent', 'loud', 
           'sound', 'site', 'launch', 'hover', 'hop',
           'roar', 'rumble', 'lit', 'flash', 'flare',
           'explosion', 'explode', 'visible', 'shut',
           'block', 'roadblock', 'notam', 'tfr', 'tfrs'}

spacex_mentions = {'@spacex'}
nasa_mentions = {'@nasa', 'nasa'}

# People/tweets to track + their triggers
people = {'@elonmusk':{'real_name':'Elon Musk',
                       'triggers': starship|spacex|spacex_mentions|nasa_mentions,
                       'retweets': True,
                      },
          '@bocachicagal':{'real_name':'Mary',
                          'triggers': testing|starship,
                           'retweets': False
                         }
         }


def searchTweets(log_file=log_file, seen_tweets=seen_tweets):
        
    # check network connection
    try:
        requests.get('http://x.com') # Elon's tiny website :)
    except requests.ConnectionError:
        log_file += f'{datetime.now().__str__()}\t\tno connection\n'
        closeSession(log_file, ' '.join(seen_tweets))
        return None

    for person, userdat in people.items():

        for tweet in api.GetUserTimeline(screen_name=person, include_rts=userdat['retweets']):

            if tweet.id_str in seen_tweets:
                continue

            # gather variables for condition evaluations
            tweet_parsed = parseTweet(tweet.full_text)
            try:
                tweet_reply = api.GetStatus(tweet.in_reply_to_status_id).full_text if tweet.in_reply_to_status_id else ''
                reply_to_parsed = parseTweet(tweet_reply)
            except: # if reply is missing
                reply_to_parsed = set()

            # conditions go here and evaled; ANY complete, true condition triggers the bot
            tweet_triggers = tweet_parsed & userdat['triggers']
            reply_triggers = reply_to_parsed & userdat['triggers'] # if thread is under valid trigger

            # trigger a notification if match
            if any([tweet_triggers, reply_triggers]):

                # format and post tweet
                tweet_url = formatTweetURL(person, tweet.id_str)
                requests.post(url=keys['slack']['webhook'], 
                             data=json.dumps({'text':tweet_url}))            
                seen_tweets.append(tweet.id_str)
                log_file += f'{datetime.now().__str__()}\t\ttrigger {tweet.id_str} ({person} ) | tweet triggers: {tweet_triggers} | reply triggers: {reply_triggers}\n'
    
    log_file += f'{datetime.now().__str__()}\t\tcompleted search\n'

    closeSession(log_file, ' '.join(seen_tweets))