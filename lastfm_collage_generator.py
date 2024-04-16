import argparse
import json
import webbrowser
from pathlib import Path

import requests
import tweepy
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth1
from rich.console import Console
from rich.table import Table
from urllib3.util.retry import Retry


API_KEY = 'b7cad0612089bbbfecfc08acc52087f1'


def requests_retry_session(
    retries=5,
    backoff_factor=0.2,
    status_forcelist=(502, 503, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def dump_json(mydict, filename):
    filename = Path(filename)
    if filename.suffix.lower() != '.json':
        filename = filename.with_suffix('.json')
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open('w', encoding='utf-8') as f:
        json.dump(mydict, f, ensure_ascii=False, indent=2)


def load_json(filename, encoding='utf-8'):
    filename = Path(filename)
    with filename.open('r', encoding=encoding) as f:
        data = json.load(f)
    return data


def download(url, save_dir='.'):
    f = Path(save_dir) / url.split('/')[-1]
    if f.exists():
        return
    if not Path(save_dir).exists():
        Path(save_dir).mkdir(parents=True, exist_ok=True)
    print(f'[DEBUG] downloading {url} to {f}')
    with requests_retry_session().get(url, stream=True) as r:
        r.raise_for_status()
        with f.open('wb') as fio:
            for chunk in r.iter_content(chunk_size=8192):
                fio.write(chunk)


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


def get_font_size(text, side_length):
    while True:
        font = ImageFont.truetype('SourceHanSans-Regular.otf', font_size)
        length = ImageDraw.textlength(text, font=font)
        if length > side_length:
            font_size -= 1
        else:
            break
    return font_size


def add_text(image, draw, x, y, text, font, stroke_width):
    blurred = Image.new('RGBA', image.size)
    blurred_draw = ImageDraw.Draw(blurred)
    blurred_draw.text(xy=(x, y), text=text, fill='white', font=font, anchor="mm", align="center")
    blurred = blurred.filter(ImageFilter.GaussianBlur(radius=10))
    # blurred_draw.text(xy=(x+5,y+5), text=text, fill='black', font=font, anchor="mm", align="center")
    image.paste(blurred, blurred)
    draw.text((x, y), text, fill="white", font=font, stroke_fill='black', stroke_width=stroke_width, anchor="mm", align="center")


def create_collage(data, side_length, rows, cols, output, font_path, show_name, show=False):
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
                    download(image_url, save_dir='img_cache')
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
                        local_max_fontsize = max_fontsize if idx == 0 else round(max_fontsize / 1.2)  # artist line is smaller

                        fontsize = local_max_fontsize
                        while True:
                            font = ImageFont.truetype(font_path, fontsize)
                            length = draw.textlength(text, font=font)
                            if length > side_length * 0.95:  # leave some margin
                                fontsize -= 1
                            else:
                                break

                        if fontsize != local_max_fontsize:
                            print(f'[DEBUG] long text: {text}, fontsize: {fontsize}')

                        textY_shift = textY - line_height // 2 + line_height * idx
                        add_text(collage, draw, textX, textY_shift, text, font, stroke_width)
                        # draw.text((textX, textY_shift), text, fill="white", font=font, stroke_fill='black', stroke_width=stroke_width, anchor="mm", align="center")

    collage.save(output, format='JPEG', quality=94, optimize=True, subsampling=0)
    if show:
        collage.show()


def tweet(text, file):
    def load_keys():
        # format: consumer_key, consumer_secret, access_token, access_token_secret, each on a line
        auth_file = Path('auth_twitter.txt')
        if not auth_file.exists():
            raise FileNotFoundError(f'Auth file {auth_file} not found')

        with auth_file.open('r') as f:
            return f.read().splitlines()

    try:
        keys = load_keys()
    except Exception as e:
        print('Cannot load keys:', e)
        return

    tweepy_auth = tweepy.OAuth1UserHandler(*keys)
    tweepy_api = tweepy.API(tweepy_auth)

    tweepy_api.session = requests_retry_session()

    media = tweepy_api.simple_upload(file)
    print(f'[DEBUG] twitter media upload response: {media}')
    media_id = media.media_id
    print(f'[DEBUG] media_id: {media_id}')
    payload = {"media": {"media_ids": [str(media_id)]}}
    payload['text'] = text
    dump_json(payload, 'payload.json')

    r = requests_retry_session().post("https://api.twitter.com/2/tweets", json=payload, auth=OAuth1(*keys))
    print(f'[DEBUG] twitter tweet status code: {r.status_code}')
    print(f'[DEBUG] twitter tweet response: {r.text}')
    res = r.json()
    tweet_id = res['data']['id']
    webbrowser.open(f'https://twitter.com/i/web/status/{tweet_id}')


def print_data(data):
    # print info
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim")
    table.add_column("Album")
    table.add_column("Artist")
    table.add_column("Play count", justify="right")
    table.add_column("Has cover")
    for i, album in enumerate(data):
        if album['image'][-1]['#text']:
            has_cover = '✅'
        else:
            has_cover = '❌'
            webbrowser.open(album['url'])
        table.add_row(str(i+1), album['name'], album['artist']['name'], str(album['playcount']), has_cover)
    console = Console()
    console.print(table)


def fetch_dump_print():
    data = get_info(args.username, args.period, limit=args.rows*args.cols+5)  # get a little bit more
    dump_json(data, 'data.json')
    print_data(data)
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', default=None, choices=['fetch', 'collage', 'tweet', 'all'], nargs='?', help='Specify the action to perform: fetch data, create collage, tweet, or all combined. If not given, it will be interactive.')
    parser.add_argument('--username', '-u', type=str, help='Username of the LastFM user.')
    parser.add_argument('--period', type=str, default='7day', choices=['7day', '1month', '3month', '6month', '12month', 'overall'], help='Time period for which to fetch the LastFM data [default: 7day].')
    parser.add_argument('--rows', type=int, default=3, help='Number of rows in the collage [default: 3].')
    parser.add_argument('--cols', type=int, default=3, help='Number of columns in the collage [default: 3].')
    parser.add_argument('--show-name', action='store_true', default=True, dest='show_name', help='Display the name on the collage [default: True].')
    parser.add_argument('--no-show-name', action='store_false', dest='show_name', help='Do not display the name on the collage.')
    parser.add_argument('--size', type=int, default=500, help='Size of each image in the collage [default: 500].')
    parser.add_argument('--font', type=str, default='SourceHanSans-Regular.otf', help='Font file to use for text [default: SourceHanSans-Regular.otf].')
    args = parser.parse_args()

    output = f'collage_{args.size}.jpg'
    data = None

    if args.action is None:
        action = 'fetch'
    else:
        action = args.action

    if action in ['fetch', 'all']:
        data = fetch_dump_print()

    if args.action is None:
        print('Data fetched and saved to data.json. Please make modifications if needed.')
        while True: # interactive
            user_input = input('[R] to re-fetch remote data, [P] to re-print local data, [I] to ignore data without images, [Enter] to continue generating collage: ')
            if user_input.lower() == 'r':
                data = fetch_dump_print()
            elif user_input.lower() == 'p':
                data = load_json('data.json')
                print_data(data)
            elif user_input.lower() == 'i':
                data = [album for album in data if album['image'][-1]['#text']]
                assert len(data) >= args.rows * args.cols, f'Not enough data with images: {len(data)}'
                print_data(data)
            elif user_input == '':
                break
        action = 'collage'

    if action in ['collage', 'all']:
        if not data:
            data = load_json('data.json')
        # show the image if the action is not "all"
        show = True if action == 'collage' else False
        create_collage(data, args.size, args.rows, args.cols, output, font_path=args.font, show_name=args.show_name, show=show)

    if args.action is None:
        print('Collage generated and saved to collage.jpg.')
        input('Press enter to tweet: ')
        action = 'tweet'

    if action in ['tweet', 'all']:
        text = f'My fav albums this week https://last.fm/user/{args.username}'
        assert Path(output).exists(), f'Collage {output} not found'
        tweet(text, output)
