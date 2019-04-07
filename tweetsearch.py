import twitter, re, spacy, json, requests, time
from datetime import datetime
nlp = spacy.load('en')

# configure frequency of tweet searches here
sleeptime = 60

def parseTweet(tweetstring):
    '''
    Lemmatize and lowercase tweet text.
    Returns a set of lemmas.
    '''
    return set(token.text.lower() for token in nlp(tweetstring))

def formatTweetURL(user, status_id):
    '''
    Returns formatted URL for tweets.
    '''
    return f'https://twitter.com/{user}/status/{status_id}'

# get authorization keys
with open('keys.json', 'r') as infile:
    keys = json.load(infile)
    
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

# People/tweets to track + their triggers
people = {'@elonmusk':{'real_name':'Elon Musk',
                       'triggers': starship|spacex},
          '@bocachicagal':{'real_name':'Mary',
                          'triggers': testing|starship|spacex
                         }
         }
    
def searchTweets():
    '''
    Runs the search process
    and posts to Slack group.
    '''

    for person, userdat in people.items():

        print(person)

        for tweet in api.GetUserTimeline(screen_name=person, include_rts=False):

            # skip tweets older than 1 min+
            now = datetime.now()
            tweet_time = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')        
            if (now-tweet_time).seconds > sleeptime+5: # extra time to account for the process itself
                continue

            # gather variables for condition evaluations
            tweet_parsed = parseTweet(tweet.full_text)
            try:
                tweet_reply = api.GetStatus(tweet.in_reply_to_status_id).full_text if tweet.in_reply_to_status_id else ''
                reply_to_parsed = parseTweet(tweet_reply)
            except: # if reply is missing
                reply_to_parsed = set()

            # conditions go here and evaled; ANY complete, true condition triggers the bot
            tweet_triggers = bool(tweet_parsed & userdat['triggers'])
            reply_triggers = bool(reply_to_parsed & userdat['triggers']) # if thread is under valid trigger

            # trigger a notification if match
            if any([tweet_triggers, reply_triggers]):

                print(tweet.created_at)
                print(tweet.full_text)
                print('-'*20)
                print()

                # format and post tweet
                tweet_url = formatTweetURL(person, tweet.id_str)
                requests.post(url=keys['slack']['webhook'], 
                              data=json.dumps({'text':tweet_url}))
                              
while True:
    searchTweets()
    time.sleep(sleeptime)