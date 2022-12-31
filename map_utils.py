import requests
import constants as c
from google.cloud import storage

URL = 'https://maps.googleapis.com/maps/api/streetview'


def get_maps_img(args, location_info: dict) -> bytes:
    assert args.maps_key != '', 'Please provide maps API key'
    lat, lng = location_info['lat'], location_info['lng']
    params = {
        'key': args.maps_key,
        'size': '512x512',
        'location': f'{lat},{lng}',
        'heading': str(location_info['heading']),
        'pitch': str(location_info['pitch']),
        # 'fov': '90'
    }
    response = requests.get(URL, params)
    assert response.status_code == 200, params

    return response.content


"""
lat, long = coords
heading = 0
pitch = 0
params = {
    'key': KEY,
    'size': '512x512',
    'location': f'{lat},{long}',
    'heading': str(heading),
    'pitch': str(pitch),
    # 'fov': '90'
}


print(response.status_code)
with open(f'street_view.jpg', "wb") as file:
    file.write(response.content)
"""