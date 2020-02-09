import os, twitter, re, json, requests, time, pytz
from datetime import datetime

# NLP tools
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import TweetTokenizer
from nltk.corpus import wordnet
lemma = WordNetLemmatizer()
tokenizer = nltk.word_tokenize # NB: splits off #s and @s; otherwise, use TweetTokenizer().tokenize 

spacexdir = os.path.expanduser('~/github/spacex_smartweets/')
keys = os.path.join(spacexdir, 'keys.json')
seentweets = os.path.join(spacexdir, 'seen_tweets.txt')
log = os.path.join(spacexdir,'log.txt')

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
                  for w in tokenizer(tweetstring))
    return lemmas


def formatTweetURL(user, status_id):
    '''
    Returns formatted URL for tweets.
    '''
    return f'https://twitter.com/{user}/status/{status_id}'

# instance Twitter-API
api = twitter.Api(**keys['twitter'], tweet_mode='extended')


# Tweet Triggers, Organized by "domain"
starship = {
    'starship', 'hopper', 
    'starhopper', 'raptor', 
    'tether', 'dome', 'weld', 'barrel',
    'flight',
} 

spacecraft = {
    'thrust', 'rocket', 'ton', 
    'pad', 'engine', 'fairing', 'booster', 'crew',
    'propellant', 'CH4', 'turbopump'
}
spacexthings = {
    'falcon', 'merlin', 'ocisly', 'octagrabber', 'octograbber',
    'jrti', 'droneship', 'starlink', '39a', 'dragon', 'draco', 'superdraco',
}
boosters = {'b1055','b1057', 'b1052', 'b1053', 'b1047', 'b1048', 'b1053', 'b1051'}  
raptors = {'sn1', 'sn2', 'sn3'}
spacexthings |= boosters|raptors

space = {
    'space', 'mars', 'orbit', 'orbital', 'flight', 
    'crewed', 'bar'
}
moon = {'moon', 'lunar'}
space |= moon

bocachica = {'test','road', 'close', 'open', 'shut',
             'reopen', 'sheriff', 'vent', 'loud', 
             'sound', 'site', 'launch', 'hover', 'hop',
             'roar', 'rumble', 'lit', 'flash', 'flare',
             'explosion', 'explode', 'visible', 'shut',
             'block', 'roadblock', 'notam', 'tfr', 'tfrs',
             'hangar', 'foundation'}

mcgregor = {'mcgregor', 'raptor', 'test', 'loud', '#spacextests', 'roar'}

spacex_mentions = {'spacex'} 
elon_mentions = {'elonmusk'}
nasa_mentions = {'nasa'} 

# People/tweets to track + their triggers
people = {'@elonmusk':{'real_name':'Elon Musk',
                       'triggers': starship|spacexthings|spacecraft|space|spacex_mentions|nasa_mentions,
                       'retweets': False,
                       'replies': True,
                       'bio': 'the one and only'
                      },
          '@bocachicagal':{'real_name':'Mary',
                          'triggers': bocachica|starship,
                           'retweets': False,
                           'replies': False,
                           'bio': 'posts updates on tests'
                         },
          '@RGVReagan': {'real_name': 'Mark Reagan',
                         'triggers': spacex_mentions|starship|elon_mentions,
                          'retweets': False,
                          'replies': True,
                          'bio': 'journalist with @Brownsvillenews'},
#          '@SpacePadreIsle': {'real_name': 'Spadre',
#                              'triggers': spacex_mentions|starship|bocachica,
#                              'retweets': False,
#                              'replies': False,
#                              'bio': 'spadre surfing'},
          '@SpaceX':{'real_name': 'Space Exploration Technologies',
                     'triggers': set(),
                     'retweets': False,
                     'replies': True,
                     'bio': 'the big one'},
          '@austinbarnard45':{'real_name': 'Austin Barnard',
                              'triggers': bocachica|starship,
                              'retweets': False,
                              'replies': False,
                              'bio': 'Local who takes pictures and streams sometimes'},
          '@bluemoondance74':{'real_name': 'Reagan Beck',
                              'triggers': {'#spacextests'}, 
                              'retweets': False,
                              'replies': False,
                              'bio': 'Lives near McGregor test facility'},
          '@SpaceXFleet': {'real_name': 'Fleet Updates',
                           'triggers': spacexthings|spacecraft, 
                           'retweets': False,
                           'replies': False,
                           'bio': 'Posts fleet updates'},
          '@Teslarati': {'real_name': 'Teslarati',
                           'triggers': spacexthings|starship|nasa_mentions|spacex_mentions,
                           'retweets': False,
                           'replies': True,
                           'bio': 'News'},
          '@Erdayastronaut':{'real_name': 'Tim Dodd',
                             'triggers': spacexthings|starship,
                             'retweets': False,
                             'replies': False,
                             'bio': 'Space blogger'},
          '@SciGuySpace': {'real_name': 'Eric Berger',
                             'triggers': spacexthings|spacex_mentions|elon_mentions|{'starship'},
                             'retweets': False,
                             'replies': False,
                             'bio': 'Senior Space Editor at Ars Technica'},
          '@NASA':{'real_name': 'NASA',
                   'triggers': spacexthings|spacex_mentions|elon_mentions,
                   'retweets': False,
                   'replies': True,
                   'bio':'it is nasa'},
          '@JimBridenstine': {'real_name': 'Jim Bridenstine',
                             'triggers': spacex_mentions|elon_mentions|starship|moon|spacexthings,
                             'retweets': False,
                             'replies': False,
                             'bio': 'Administrator of NASA'}, 
          '@RogerLewisHolt': {'real_name': 'Roger Holt',
                              'triggers': spacex_mentions|starship|spacexthings,
                              'retweets': False,
                              'replies': False,
                              'bio': 'Tweets great spacex content'},
          '@EmreKelly': {'real_name': 'Emre Kelly',
                         'triggers': spacex_mentions|spacexthings|starship|elon_mentions,
                         'retweets': False,
                         'replies': False,
                         'bio': 'Space reporter @Florida_today & @usatoday'},
          '@SpaceTeam': {'real_name': 'Space Team',
                         'triggers': spacex_mentions|spacexthings|starship|elon_mentions,
                         'retweets': False,
                         'replies': False,
                         'bio': 'Reporting for @Florida_today on the space industry'},
          '@AstroBehnken': {'real_name': 'Bob Behnken',
                            'triggers': spacex_mentions|spacexthings|elon_mentions,
                            'retweets': False,
                            'replies': True,
                            'bio': 'Astronaut slated for DM-2'},
          'Astro_Doug': {'real_name': 'Doug Hurley',
                         'triggers': spacex_mentions|spacexthings|elon_mentions,
                         'retweets': False,
                         'replies': True,
                         'bio': 'Astronaut slated for DM-2'},
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

        for tweet in api.GetUserTimeline(screen_name=person, include_rts=userdat['retweets'], count=20):

            # skip seen tweets or those older than 30 mins (1800 secs)
            now = datetime.now(tz=pytz.utc) 
            tweet_time = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.utc)	
            tweet_age = (now - tweet_time).total_seconds()
            if tweet.id_str in seen_tweets or tweet_age > 1800:
                continue

            # gather variables for condition evaluations
            tweet_parsed = parseTweet(tweet.full_text)
            if userdat['replies']:
                try:
                    tweet_reply = api.GetStatus(tweet.in_reply_to_status_id).full_text if tweet.in_reply_to_status_id else ''
                    reply_to_parsed = parseTweet(tweet_reply)
                except: # if reply is missing
                    reply_to_parsed = set()
            else:
                reply_to_parsed = set()

            # conditions go here and evaled; ANY complete, true condition triggers the bot
            tweet_triggers = tweet_parsed & userdat['triggers']
            reply_triggers = reply_to_parsed & userdat['triggers'] # if thread is under valid trigger

            # trigger a notification if match
            # empty trigger sets are configured to match any tweets
            if any([tweet_triggers, reply_triggers, not userdat['triggers']]):
                
                # format and ship tweet and data
                tweet_url = formatTweetURL(person, tweet.id_str)
                clean_text = re.split('https://t.co', tweet.full_text, maxsplit=1)[0].strip() # rm twitter URLs; prevents Slack from double-preview
                person_name = tweet.user.name
                send_text = f'//{person_name}// {clean_text} {tweet_url}'

                # send Slack post
                requests.post(url=keys['slack']['webhook'], 
                             data=json.dumps({'text':send_text}))            
                # send Discord post
                requests.post(url=keys['discord']['webhook'],
                              data=json.dumps({'content':send_text}))

                seen_tweets.append(tweet.id_str)
                log_file += f'{datetime.now().__str__()}\t\ttrigger {tweet.id_str} ({person} ) | tweet triggers: {tweet_triggers} | reply triggers: {reply_triggers} | tweet_age: {tweet_age}\n'
    
    log_file += f'{datetime.now().__str__()}\t\tcompleted search\n'

    closeSession(log_file, ' '.join(seen_tweets))
    
# call the search
searchTweets()
