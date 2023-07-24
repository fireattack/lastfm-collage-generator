import re
from pathlib import Path

import tweepy
from PIL import Image, ImageDraw, ImageFont
from requests_oauthlib import OAuth1
from util import download, dump_json, requests_retry_session

API_KEY = 'b7cad0612089bbbfecfc08acc52087f1'

def make_square(image, size):
    # Calculate aspect ratio
    width, height = image.size
    aspect_ratio = width / height

    # Resize while maintaining aspect ratio
    if width > height:
        new_width = int(size * aspect_ratio)
        new_height = size
    else:
        new_width = size
        new_height = int(size / aspect_ratio)

    image = image.resize((new_width, new_height))

    # Crop to square
    width, height = image.size
    left = (width - size) / 2
    top = (height - size) / 2
    right = (width + size) / 2
    bottom = (height + size) / 2

    image = image.crop((left, top, right, bottom))

    return image

def get_info(username, period, limit):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettopalbums&user={username}&period={period}&api_key={API_KEY}&limit={limit}&format=json"

    response = requests_retry_session().get(url)
    data = response.json()

    return data['topalbums']['album']

def create_collage(data, side_length, rows, cols, show_name, output='collage.jpg'):
    # side_length = SIDE_LENGTHS[size]
    collage_width = side_length * cols
    collage_height = side_length * rows

    collage = Image.new('RGB', (collage_width, collage_height))
    draw = ImageDraw.Draw(collage)

    max_fontsize = side_length // 15
    line_height = max_fontsize * 1.2
    stroke_width = max(max_fontsize//25, 1)
    print(f'[DEBUG] max_fontsize: {max_fontsize}, stroke_width: {stroke_width}')

    for i in range(rows):
        for j in range(cols):
            index = i * cols + j
            if album := data[index]:
                # download cover if exists
                if album['image'][-1]['#text']:
                    image_url = album['image'][-1]['#text'].replace('300x300/', '')
                    download(image_url, save_path='img_cache', dupe='skip', verbose=0)
                    img = Image.open('img_cache/' + image_url.split('/')[-1])
                    # resize image to fit the side length
                    img = make_square(img, side_length)
                    collage.paste(img, (j * side_length, i * side_length))

                if show_name:
                    # print(f'[DEBUG] adding text {album_name}, {artist_name}')
                    album_name = album['name']
                    artist_name = album['artist']['name']

                    textX = j * side_length + side_length // 2
                    textY = i * side_length + side_length // 2

                    for idx, text in enumerate([album_name, artist_name]):
                        local_max_fontsize = max_fontsize if idx == 0 else round(max_fontsize / 1.2) # artist line is smaller
                        fontsize = (min(int((side_length * 1.2) // len(text)), local_max_fontsize))
                        if fontsize != local_max_fontsize:
                            print(f'[DEBUG] long text: {text}, fontsize: {fontsize}')
                        font = ImageFont.truetype('SourceHanSans-Regular.otf', fontsize)
                        textY_shift = textY - line_height // 2 + line_height * idx
                        draw.text((textX, textY_shift), text, fill="white", font=font, stroke_fill='black', stroke_width=stroke_width, anchor="mm", align="center")

    collage.save(output, format='JPEG', quality=94, optimize=True, subsampling=0)

def load_keys():
    # format: consumer_key, consumer_secret, access_token, access_token_secret, each on a line
    auth_file = Path('auth_twitter.txt')
    with auth_file.open('r') as f:
        return f.read().splitlines()

def tweet(text, file):
    keys = load_keys()
    tweepy_auth = tweepy.OAuth1UserHandler(
        *keys
    )
    tweepy_api = tweepy.API(tweepy_auth)
    post = tweepy_api.simple_upload(file)
    text = str(post)
    print(f'[DEBUG] twitter media upload response: {text}')
    media_id = re.search(r"media_id=(.+?),", text)[1]
    print(f'[DEBUG] media_id: {media_id}')
    payload = {"media": {"media_ids": ["{}".format(media_id)]}}
    payload['text'] = text
    dump_json(payload, 'payload.json')

    r = requests_retry_session().post("https://api.twitter.com/2/tweets", json=payload, auth=OAuth1(*keys))
    print(f'[DEBUG] twitter tweet status code: {r.status_code}')
    print(f'[DEBUG] twitter tweet response: {r.text}')

def main():
    username = 'fireattack'
    period = '7day' # 7day | 1month | 3month | 6month | 12month | overall
    rows = 3
    cols = 3
    show_name = True
    size = 500

    data = get_info(username, period, limit=rows*cols)

    output = f'collage_{size}.jpg'
    create_collage(data, size, rows, cols, show_name, output=output)

    text = f'My fav albums this week https://last.fm/user/{username}'
    tweet(text, output)

if __name__ == '__main__':
    main()