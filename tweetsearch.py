# Standard Library
from datetime import datetime
import json
import logging
import logging.config
import os
import re

# Third-party
from diskcache import Cache

# NLP tools
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import pytz
import requests
import twitter

MAX_TWEET_AGE = 60 * 60
"""Maximum age of tweets to look at in seconds"""

SPACEX_DIR = os.path.dirname(__file__)
"""Directory to save logs and caches"""

MAX_LOG_SIZE = 2**20
"""Max size of log file before rotation in bytes"""

MAX_LOG_FILES = 5
"""Max number of log files to keep"""


logging.config.dictConfig(
    {
        "version": 1,
        "formatters": {
            "simple": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "filename": "smartweets.log",
                "maxBytes": MAX_LOG_SIZE,
                "backupCount": MAX_LOG_FILES,
            },
        },
        "root": {"level": "DEBUG", "handlers": ["console", "file"]},
    }
)

logger = logging.getLogger()

lemma = WordNetLemmatizer()

# NB: splits off #s and @s; otherwise, use TweetTokenizer().tokenize
tokenizer = nltk.word_tokenize


keys = os.path.join(SPACEX_DIR, 'keys.json')

# get authorization keys
with open(keys, 'r') as infile:
    keys = json.load(infile)

# instance Twitter-API
api = twitter.Api(**keys['twitter'], tweet_mode='extended')

seen_cache = Cache(os.path.join(SPACEX_DIR, '.seen_tweets_cache'))


def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts.

    Credit: https://www.machinelearningplus.com/nlp/lemmatization-examples-python/
    ^ which saved me some time from thinking through this...
    """
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {
        'J': wordnet.ADJ,
        'N': wordnet.NOUN,
        'V': wordnet.VERB,
        'R': wordnet.ADV,
    }
    return tag_dict.get(tag, wordnet.NOUN)


def lemmatizeTweet(tweetstring):
    """Lemmatize and lowercase tweet text.

    Returns a set of lemmas.
    """
    lower_words = [w.lower() for w in tokenizer(tweetstring)]
    pos_words = [get_wordnet_pos(w) for w in lower_words]
    lemmas = [lemma.lemmatize(w, pos) for w, pos in zip(lower_words, pos_words)]
    return lemmas


def matchWords(lemmas, regex):
    """Iterate through lemmas and look for match."""
    regex = re.compile(regex)
    for lemma in lemmas:
        match = regex.match(lemma)
        if match:
            return match
    return match


def matchTweet(tweet, match_terms):
    """Match tweets using regex.

    Args:
        tweet: twitter Status object
        match_terms: a set of terms to be
            joined on | for regex matching
    Returns:
        boolean on whether a match
    """
    if tweet is None:
        return None
    tweet_lemmas = lemmatizeTweet(tweet.full_text)
    match_pattern = '|'.join(match_terms)
    re_match = matchWords(tweet_lemmas, match_pattern)
    return re_match


def formatTweetURL(user, status_id):
    """Returns formatted URL for tweets."""
    return f'https://twitter.com/{user}/status/{status_id}'


# Tweet Triggers, Organized by "domain"
# Terms support regex pattern matching
# NB: all tweet strings are lowercased for matching
starship = {
    'starship',
    r'sn\d+',
    r'bn\d+',
    'superheavy',
    'raptor',
    'bellyflop' 'hopper',
    'tps',
}

bocachica = {'bay', 'highbay', 'midbay', 'boca', 'chica', 'starbase', 'shipyard'}

starbase = starship | bocachica

spacecraft = {
    'thrust',
    'rocket',
    'isp',
    'pad',
    'engine',
    'fairing',
    'booster',
    'propellant',
    'ch4',
    'turbopump',
    'nosecone',
    'tank',
    'flap',
}
spacexthings = {
    'falcon',
    'merlin',
    'ocisly',
    'octagrabber',
    'octograbber',
    'jrti',
    'droneship',
    'starlink',
    '39a',
    'dragon',
    'draco',
    'superdraco',
}

missions = {'dearmoon'}

spacexthings |= missions

space = {
    'space',
    'mars',
    'orbit',
    'orbital',
    'flight',
    'crewed',
    'launch',
    'moon',
    'lunar',
}

testing = {
    'test',
    'road',
    'close',
    'open',
    'shut',
    'reopen',
    'sheriff',
    'vent',
    'loud',
    'sound',
    'site',
    'launch',
    'hover',
    'hop',
    'roar',
    'rumble',
    'lit',
    'flash',
    'flare',
    'explosion',
    'explode',
    'visible',
    'shut',
    'block',
    'roadblock',
    'notam',
    'tfr',
    'tfrs',
    'hangar',
    'foundation',
}

mcgregor = {'mcgregor', 'raptor', 'test', 'loud', '#spacextests', 'roar'}

spacex_mentions = {'spacex'}
elon_mentions = {'elonmusk'}
nasa_mentions = {'nasa'}

# People/tweets to track + their triggers
people = {
    '@elonmusk': {
        'real_name': 'Elon Musk',
        'triggers': starbase
        | spacexthings
        | spacecraft
        | space
        | spacex_mentions
        | nasa_mentions,
        'replies': True,
        'bio': 'the one and only',
    },
    '@bocachicagal': {
        'real_name': 'Mary',
        'triggers': testing | starbase,
        'bio': 'posts updates on tests',
    },
    '@RGVReagan': {
        'real_name': 'Mark Reagan',
        'triggers': spacex_mentions | starbase | elon_mentions,
        'replies': True,
        'bio': 'journalist with @Brownsvillenews',
    },
    '@SpacePadreIsle': {
        'real_name': 'Spadre',
        'triggers': spacex_mentions | starbase | testing,
        'bio': 'spadre surfing',
    },
    '@SpaceX': {
        'real_name': 'Space Exploration Technologies',
        'triggers': set(),
        'all_tweets': True,
        'replies': True,
        'bio': 'the big one',
    },
    '@austinbarnard45': {
        'real_name': 'Austin Barnard',
        'triggers': testing | starbase,
        'bio': 'Local who takes pictures and streams sometimes',
    },
    '@bluemoondance74': {
        'real_name': 'Reagan Beck',
        'triggers': spacex_mentions | mcgregor,
        'bio': 'Lives near McGregor test facility',
    },
    '@Teslarati': {
        'real_name': 'Teslarati',
        'triggers': spacexthings | starbase | nasa_mentions | spacex_mentions,
        'replies': True,
        'bio': 'News',
    },
    '@Erdayastronaut': {
        'real_name': 'Tim Dodd',
        'triggers': spacexthings | starbase,
        'bio': 'Space Youtuber',
    },
    '@SciGuySpace': {
        'real_name': 'Eric Berger',
        'triggers': spacexthings | spacex_mentions | elon_mentions | starbase,
        'bio': 'Senior Space Editor at Ars Technica',
    },
    '@_brendan_lewis': {
        'real_name': 'Brendan',
        'triggers': starbase,
        'media': True,
        'bio': 'Tweets diagrams',
    },
    '@ErcXspace': {
        'real_name': '',
        'triggers': starbase,
        'media': True,
        'bio': 'Tweets renders',
    },
    '@Neopork85': {
        'real_name': '',
        'triggers': starbase,
        'media': True,
        'bio': 'Tweets renders',
    },
    '@C_Bass3d': {
        'real_name': 'Corey',
        'triggers': starship,
        'media': True,
        'bio': '3D models',
    },
    '@RGVaerialphotos': {
        'real_name': '',
        'triggers': spacex_mentions | starbase | spacexthings,
        'media': True,
        'bio': 'Tweets aerials',
    },
    '@EmreKelly': {
        'real_name': 'Emre Kelly',
        'triggers': spacex_mentions | spacexthings | starbase | elon_mentions,
        'bio': 'Space reporter @Florida_today & @usatoday',
    },
    '@fael097': {
        'real_name': 'Rafael Adamy',
        'triggers': starbase,
        'bio': 'builds SNX diagrams',
    },
    '@NASASpaceflight': {
        'real_name': 'Chris B',
        'triggers': starbase,
        'bio': 'Runs Nasaspaceflight',
    },
    '@nextspaceflight': {
        'real_name': 'Michael Baylor',
        'triggers': starbase,
        'bio': 'Works for Nasaspaceflight',
    },
    '@TheFavoritist': {
        'real_name': 'Brady Kenniston',
        'triggers': starbase,
        'bio': 'Works for Nasaspaceflight',
    },
    '@thejackbeyer': {
        'real_name': 'Jack Beyer',
        'triggers': starbase,
        'bio': 'Works for Nasaspaceflight',
    },
    '@BocaRoad': {
        'real_name': '',
        'triggers': {'closure'},
        'all_tweets': True,
        'bio': 'Posts road closures',
    },
    '@BocachicaMaria1': {
        'real_name': 'Maria Pointer',
        'triggers': spacex_mentions
        | starship
        | bocachica
        | spacexthings
        | elon_mentions,
        'retweets': False,
        'replies': True,
        'bio': (
            'BocaChicaMaria, not BocaChicaGal. Having fun documenting SpaceX. '
            '1st neighbor out our back door.'
        ),
    },
    '@planet4589': {
        'real_name': 'Jonathan McDowell',
        'triggers': set(),
        'all_tweets': True,
        'bio': 'Orbital Police',
    },
    '@cnunezimages': {
        'real_name': 'StarbaseSurfer',
        'triggers': spacex_mentions
        | starship
        | bocachica
        | spacexthings
        | elon_mentions,
        'media': True,
        'bio': 'Starbase photographer',
    },
    '@NicAnsuini': {
        'real_name': 'Nic Ansuini',
        'triggers': spacex_mentions
        | starship
        | bocachica
        | spacexthings
        | elon_mentions,
        'media': True,
        'bio': 'Photojournalist for NASASpaceflight.com',
    },
    '@LabPadre': {
        'real_name': 'LabPadre',
        'bio': 'LabPadre',
        'triggers': set(),
        'all_tweets': True,
        'retweets': True,
        'replies': True,
    },
}


def searchTweets():

    # check network connection
    try:
        requests.get('http://x.com')  # Elon's tiny website :)
    except requests.ConnectionError as e:
        logger.error('No Connection', e)
        return None

    seen_cache.expire()

    for person, userdat in people.items():
        # load all eligible tweets
        do_replies = userdat.get('replies', False)
        try:
            user_tweets = api.GetUserTimeline(
                screen_name=person,
                include_rts=userdat.get('retweets', False),
                exclude_replies=(not do_replies),
                count=20,
            )
        except Exception as e:
            logger.error(f'Unable to read timeline for {person}', e)
            continue

        user_tweets.sort(
            key=lambda tweet: datetime.strptime(
                tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y'
            )
        )
        # scan tweets for matches
        for tweet in user_tweets:
            # skip seen tweets or those older than {MAX_TWEET_AGE}
            now = datetime.now(tz=pytz.utc)
            tweet_time = datetime.strptime(
                tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y'
            ).replace(tzinfo=pytz.utc)
            tweet_age = (now - tweet_time).total_seconds()
            if tweet.id_str in seen_cache or tweet_age > MAX_TWEET_AGE:
                continue

            # if tweet is a reply:
            # check whether the reply is in response to a matching tweet
            if do_replies:
                try:
                    original_tweet = (
                        api.GetStatus(tweet.in_reply_to_status_id)
                        if tweet.in_reply_to_status_id
                        else None
                    )
                except Exception:  # if orig. tweet is missing
                    original_tweet = None
            else:
                original_tweet = None

            # search for tweet matches
            match_terms = userdat['triggers']
            tweet_match = matchTweet(tweet, match_terms)
            orig_match = matchTweet(original_tweet, match_terms)

            match_media = userdat.get('media', False) and bool(
                getattr(tweet, 'media', False)
            )

            match_alltweets = userdat.get('all_tweets', False)

            is_match = any(
                [
                    bool(tweet_match),
                    bool(orig_match),
                    match_alltweets,
                    match_media,
                ]
            )
            # trigger a notification if match
            if is_match:

                # format and ship tweet and data
                tweet_url = formatTweetURL(person, tweet.id_str)

                # format pushed message
                if tweet_match and tweet_match[0]:
                    trigger = f' __**{tweet_match[0]}**__'
                elif orig_match and orig_match[0]:
                    trigger = f' __**{orig_match[0]}**__'
                elif match_media:
                    trigger = ' __**media**__'
                else:
                    trigger = ''

                person_name = tweet.user.name

                send_text = f'{tweet_url}{trigger}'

                # add original tweet if the tweet is a reply to an unseen other tweet
                if orig_match and (original_tweet.id_str not in seen_cache):
                    orig_name = original_tweet.user.name
                    orig_text = original_tweet.full_text
                    send_text = (
                        f'`• {orig_name} •`\n{orig_text}\n' '|\n' '|\n' '|\n'
                    ) + send_text

                # push Slack post
                if 'slack' in keys:
                    requests.post(
                        url=keys['slack']['webhook'],
                        data=json.dumps({'text': send_text}),
                    )

                # push Discord post
                if 'discord' in keys:
                    requests.post(
                        url=keys['discord']['webhook'],
                        json={'content': send_text, 'username': person_name},
                    )

                # log match data
                tweet_match = tweet_match or ['']
                orig_match = orig_match or ['']
                seen_cache.add(tweet.id_str, tweet_age, expire=MAX_TWEET_AGE)
                logger.info(
                    f'trigger {tweet.id_str} ({person} ) '
                    f'| tweet matches: {tweet_match[0]} '
                    f'| reply matches: {orig_match[0]} '
                    f'| media match: {match_media} '
                    f'| tweet_age: {tweet_age}\n'
                )

    logger.debug('Completed search')
    seen_cache.close()


# call the search
searchTweets()
