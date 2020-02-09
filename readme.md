# SpaceX Smart-Tweets

A simple tweet processor for automatically and intelligently sorting tweets related to SpaceX. 

## Dependencies

* Requires Python >= 3.6
* Requires the following python modules in environment:
  * `os`
  * `python-twitter`
  * `re`
  * `json`
  * `requests`
  * `time`
  * `pytz`
  * `datetime`
  * `nltk`

## Install

1. Begin in your home folder:

    `cd ~`
2. Create a new folder named "github" and enter it:

    `mkdir github && cd github`
3. Clone the repo and enter it:

    `git clone insert-repository-url-here && cd spacex_smartweets`
4. Install NLTK modules:

    `echo -e "import nltk\nnltk.download('punkt')\nnltk.download('averaged_perceptron_tagger')\nnltk.download('wordnet')" | /path/to/python`
5. Create empty text files:

    `touch log.txt seen_tweets.txt keys.json`
6. Populate "keys.json" file with the following entries:

    ```
    {
        "twitter": {
		"consumer_key": "twitter_consumer_key_here",
		"consumer_secret": "twitter_consumer_secret_here",
		"access_token_key": "twitter_access_token_key_here",
		"access_token_secret": "twitter_access_token_secret_here"
        },
        "discord": {
		"webhook": "discord_webhook_url_here"
        }
    }
    ```

## Run

1. You can run the script manually:

    `/path/to/python tweetsearch.py`

2. Or you can run it on a schedule with a cron task such as (insert the following into your Cron file):

    `*/2 * * * *	cd /path/to/home/github/spacex_smartweets && /path/to/python ./tweetsearch.py`

    NOTE: The above cron task will run every 2 minutes
