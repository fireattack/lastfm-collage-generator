import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from util import download, requests_retry_session

# Constants
METHOD_ALBUMS = 1
METHOD_ARTISTS = 2

API_KEY = 'b7cad0612089bbbfecfc08acc52087f1'  # Replace with your API key
SIDE_LENGTHS = [34, 64, 174, 300]


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

def get_info(method, username, period, rows, cols):
    limit = rows * cols
    url = None

    # Construct the URL
    if method == METHOD_ALBUMS:
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettopalbums&user={username}&period={period}&api_key={API_KEY}&limit={limit}&format=json"
    elif method == METHOD_ARTISTS:
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettopartists&user={username}&period={period}&api_key={API_KEY}&limit={limit}&format=json"

    # Make the API call
    response = requests_retry_session().get(url)
    data = response.json()

    # Extract the image links and titles
    if method == METHOD_ALBUMS:
        links = [album['image'][-1]['#text'] for album in data['topalbums']['album']]
        titles = [f"{album['name']}\n{album['artist']['name']}" for album in data['topalbums']['album']]
    else:
        links = [artist['image'][-1]['#text'] for artist in data['topartists']['artist']]
        titles = [artist['name'] for artist in data['topartists']['artist']]

    return links, titles




def create_collage(links, titles, side_length, rows, cols, show_name):
    # side_length = SIDE_LENGTHS[size]
    collage_width = side_length * cols
    collage_height = side_length * rows

    collage = Image.new('RGB', (collage_width, collage_height))
    draw = ImageDraw.Draw(collage)

    for i in range(rows):
        for j in range(cols):
            index = i * cols + j
            if links[index]:
                image_url = links[index].replace('300x300/', '')
                download(image_url, save_path='img_cache', dupe='skip')
                img = Image.open('img_cache/' + image_url.split('/')[-1])
                # resize image to fit the side length
                img = make_square(img, side_length)
                collage.paste(img, (j * side_length, i * side_length))

            if show_name and titles[index]:
                print(f'[DEBUG] processing {titles[index]}')
                textX = j * side_length + side_length // 2
                textY = i * side_length + side_length // 2

                lines = [(idx, text, int(min((side_length * 1.3) // len(text),side_length // 15))) for idx, text in enumerate(titles[index].split('\n'))]
                line_height = max([line[2] for line in lines]) + 20

                for idx, text, fontsize in lines:
                    print(f'[DEBUG] text: {text}, size: {fontsize}')
                    font = ImageFont.truetype('D:\\SourceHanSans-Regular.otf', fontsize)
                    textY_shift = textY - line_height // 2 + line_height * idx
                    draw.text((textX, textY_shift), text, fill="white", font=font, stroke_fill='black', stroke_width=2, anchor="mm", align="center")

    collage.save('collage.png')

# Use the functions
username = 'fireattack'  # Replace with a username
period = '7day'    # Replace with a period # overall | 7day | 1month | 3month | 6month | 12month
size = 3         # Replace with a size
rows = 3          # Replace with the number of rows
cols = 3          # Replace with the number of cols
method = METHOD_ARTISTS  # Replace with a method
show_name = True  # Replace with a boolean indicating whether to show names

links, titles = get_info(method, username, period, rows, cols)
create_collage(links, titles, 500, rows, cols, show_name)