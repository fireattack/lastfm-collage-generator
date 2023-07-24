from PIL import Image, ImageDraw, ImageFont
from util import download, requests_retry_session

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

def get_info(username, period, rows, cols):
    limit = rows * cols
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

# Use the functions
username = 'fireattack'  # Replace with a username
period = '7day'    # Replace with a period # overall | 7day | 1month | 3month | 6month | 12month
rows = 3          # Replace with the number of rows
cols = 3          # Replace with the number of cols
show_name = True  # Replace with a boolean indicating whether to show names

data = get_info(username, period, rows, cols)
for size in [500, 800, 1000, 1200]:
    create_collage(data, size, rows, cols, show_name, output=f'collage_{size}.jpg')