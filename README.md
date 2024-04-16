Last.fm Top Albums Collage Generator
====================================

Inspired by [original JS version](https://github.com/awhite/lastfm-collage-generator), but rewrote in Python.

Usage
-----

```
usage: lastfm_collage_generator.py [-h] [--username USERNAME] [--period {7day,1month,3month,6month,12month,overall}] [--rows ROWS] [--cols COLS] [--show-name] [--no-show-name] [--size SIZE] [--font FONT]
                                   [{fetch,collage,tweet,all}]

positional arguments:
  {fetch,collage,tweet,all}
                        Specify the action to perform: fetch data, create collage, tweet, or all combined. If not given, it will be interactive.

options:
  -h, --help            show this help message and exit
  --username USERNAME, -u USERNAME
                        Username of the LastFM user.
  --period {7day,1month,3month,6month,12month,overall}
                        Time period for which to fetch the LastFM data [default: 7day].
  --rows ROWS           Number of rows in the collage [default: 3].
  --cols COLS           Number of columns in the collage [default: 3].
  --show-name           Display the name on the collage [default: True].
  --no-show-name        Do not display the name on the collage.
  --size SIZE           Size of each image in the collage [default: 500].
  --font FONT           Font file to use for text [default: SourceHanSans-Regular.otf].
```

Note: it by default uses an open-source font called Source Han Sans for better CJK support, which is included in the repo for your convenience. If you want to use another font, you can change it using `--font path/to/fontfile`.

Interactive mode
----------------

If you run the script without any "action" command, it will be interactive.

It will firstly fetch the data from Last.fm, then shows you a list about which ones are missing the cover art. It will then automatically open these albums on the website so you can upload the cover art (this way, others would be benefited as well). Afterwards, you can re-fetch the data and try again.

Alternatively, you can also manually edit 'data.json' to remove some entries, or automatically remove all the entries without cover art, or just proceed without any changes.

In the next step, it will generate the collage and show you the preview. You can then tweet it if you want.


Tweet action
------------

To enable the tweet action, you need to create a Twitter Developer account and create an app. Then you need to copy your secrets into `auth_twitter.txt` file in the following format:

```
consumer_key
consumer_secret
access_token
access_token_secret
```