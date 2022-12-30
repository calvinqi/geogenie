import requests
import time
from typing import Tuple
import argparse

MAP = 'european-union'
DEFAULT_TOKENS_FILE = 'game_tokens.txt'

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
LOCATION_KEYS = ['lat', 'long', 'streakLocationCode']


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['tokens', 'data'], default='data')
    parser.add_argument('--game_tokens_file',
                        help='If not provided, will issue API rquests to generate game tokens from scratch',
                        type=str,
                        default=DEFAULT_TOKENS_FILE)
    parser.add_argument('--num_tokens_to_generate', type=int, default=2)
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


def request_guess(game_token: str, lat: float = 51.1, long: float = 3.3) -> any:
    json_data = {'token': game_token, 'lat': lat, 'long': long}
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
        time.sleep(0.1)
        rounds = request_next_round(game_token).json()['rounds']
        time.sleep(0.1)
    print(rounds)
    return rounds


def main():
    args = parse_args()
    if args.mode == 'tokens':
        generate_game_tokens(args)
        return
    get_rounds_for_game('dWnNLb05UeXg0Syt')


if __name__ == '__main__':
    main()