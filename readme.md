# SpaceX Smart-Tweets

A simple tweet processor for automatically and intelligently sorting tweets related to SpaceX.

## Dependencies

* Requires Python >= 3.9
* Requires poetry available in the environment

## Install

1. Clone the repo and enter it:
    `git clone insert-repository-url-here && cd spacex_smartweets`
2. Install required modules:
    `poestry install`
3. Install NLTK modules:
    `poetry run python -m nltk.downloader punkt averaged_perceptron_tagger wordnet omw-1.4`
4. Create empty text files:
    `touch log.txt seen_tweets.txt keys.json`
5. Populate "keys.json" file with the following entries:

    ```json
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

    `poetry run python tweetsearch.py`

2. Or you can run it on a schedule with a cron task such as (insert the following into your Cron file using `crontab -e`):

    ```crontab
    PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/path/to/home/.poetry/bin

    */2 * * * * cd /path/to/home/github/spacex_smartweets && poetry run python tweetsearch.py
    ```

    Remember to have `/path/to/home/.poetry/bin`, and where `python3` resides in the PATH inside the crontab.

    NOTE: The above cron task will run every 2 minutes
