import csv
import requests
import pdb
import time
from typing import Tuple
from google.cloud import storage
import argparse
import map_utils
import constants as c
import os

MAP = 'european-union'
DEFAULT_TOKENS_FILE = 'game_tokens.txt'
DATASET_FILE = 'dataset.csv'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--mode',
        choices=['tokens', 'data'],
        help='First generate a list of game tokens using `tokens` mode'
        'Then, using these games, `data` mode fetches images and coordinates to generate the complete dataset',
        default='data')
    ### Game token generation ###
    parser.add_argument('--game_tokens_file',
                        help='If not provided, will issue API rquests to generate game tokens from scratch',
                        type=str,
                        default=DEFAULT_TOKENS_FILE)
    parser.add_argument('--num_tokens_to_generate', type=int, default=10)

    ### Google Cloud args ###
    parser.add_argument('--project', help='GCP project', type=str, default='geogenius-project')
    parser.add_argument('--bucket', help='GCP bucket', type=str, default='geogenius-data')
    parser.add_argument('--image_data_prefix', help='For versioning the image data', type=str, default='v1_europe')
    parser.add_argument('--maps_key', help='API key', type=str, default='')

    ### Data generation ###

    args = parser.parse_args()
    return args


cookies = {
    '_ncfa':
        'PjNKO6aaw02lFvzm99wbBi24k7AUBrLfVMVxCzdtWLg%3D3t3YJIx4d9P9bryliRurjNh4pyORilxLRnECs6cVxuxG%2FGA1jYblm%2FuMPovniKLE',
    'devicetoken':
        '8B6F172135',
}


# 'cookie': '_ncfa=PjNKO6aaw02lFvzm99wbBi24k7AUBrLfVMVxCzdtWLg%3D3t3YJIx4d9P9bryliRurjNh4pyORilxLRnECs6cVxuxG%2FGA1jYblm%2FuMPovniKLE; devicetoken=8B6F172135',
def get_headers(referer: str) -> dict:
    return {
        'authority': 'www.geoguessr.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://www.geoguessr.com',
        'referer': referer,
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': USER_AGENT,
        'x-client': 'web',
    }


def request_start_game() -> any:
    json_data = {
        'map': MAP,
        'type': 'standard',
        'timeLimit': 0,
        'forbidMoving': False,
        'forbidZooming': False,
        'forbidRotating': False,
    }
    headers = get_headers(referer='https://www.geoguessr.com/maps/european-union/play')
    response = requests.post('https://www.geoguessr.com/api/v3/games', cookies=cookies, headers=headers, json=json_data)
    return response


def request_guess(game_token: str, lat: float = 51.1, lng: float = 3.3) -> any:
    json_data = {'token': game_token, 'lat': lat, 'lng': lng}
    headers = get_headers(referer=f'https://www.geoguessr.com/game/{game_token}')
    response = requests.post(f'https://www.geoguessr.com/api/v3/games/{game_token}',
                             cookies=cookies,
                             headers=headers,
                             json=json_data)
    return response


def request_next_round(game_token: str) -> any:
    # no json_data body for next_round request
    headers = get_headers(referer=f'https://www.geoguessr.com/game/{game_token}')
    response = requests.get(f'https://www.geoguessr.com/api/v3/games/{game_token}', cookies=cookies, headers=headers)
    return response


def generate_game_tokens(args):
    num = args.num_tokens_to_generate
    tokens_file = args.game_tokens_file
    print(f'Generating {num} new game tokens and appending to: {tokens_file}')
    tokens = []
    for _ in range(num):
        resp = request_start_game()
        token = resp.json()['token']
        print(token)
        with open(tokens_file, 'a') as f:
            f.write(token + '\n')
        time.sleep(1)

    return tokens


def get_rounds_for_game(game_token: str) -> dict:
    rounds = request_next_round(game_token).json()['rounds']
    # while game isn't complete, repeatedly issue guesses to complete it
    for _ in range(5):
        if len(rounds) >= 5:
            break
        request_guess(game_token)
        time.sleep(0.2)
        rounds = request_next_round(game_token).json()['rounds']
        time.sleep(0.2)
    return rounds


def generate_data_for_games(args):
    client = storage.Client(args.project)
    bucket = client.bucket(args.bucket)

    tokens_file = args.game_tokens_file
    with open(DATASET_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(c.DATA_KEYS)
        with open(tokens_file) as f:
            for game_idx, game_token in enumerate(f):
                game_token = game_token.strip()
                blobs_with_prefix = list(
                    client.list_blobs(bucket, prefix=os.path.join(args.image_data_prefix, game_token)))
                if len(blobs_with_prefix) > 0:
                    print(f'Found game token {game_token} already existing, not re-fetching')
                    continue
                print(f'Fetching round info game {game_idx}, {game_token}')

                rounds = get_rounds_for_game(game_token)
                for round_idx, round_location in enumerate(rounds):
                    location_vals = [round_location[key] for key in c.LOCATION_KEYS]
                    filename = f'{game_token}_{round_idx}.jpeg'
                    blob_filename = os.path.join(args.image_data_prefix, filename)
                    blob = bucket.blob(blob_filename)
                    img_data = map_utils.get_maps_img(args, round_location)
                    blob.upload_from_string(img_data)

                    # url = os.path.join('gs://', args.bucket, blob_filename)
                    row = location_vals + [game_token, round_idx, blob_filename]
                    writer.writerow(row)


def main():
    args = parse_args()
    if args.mode == 'tokens':
        generate_game_tokens(args)
        return
    elif args.mode == 'data':
        generate_data_for_games(args)
        return


if __name__ == '__main__':
    main()