"""One-off CLI tool to run the OAuth1 PIN-based authorization flow for a single
X account against one app's consumer key/secret, printing the resulting
access_token/access_token_secret for manual insertion into x_accounts.

Usage:
    pipenv run python tools/authorize_x_account.py --key APP_KEY --secret APP_SECRET
"""

import argparse

from requests_oauthlib import OAuth1Session

REQUEST_TOKEN_URL = "https://api.x.com/oauth/request_token"
AUTHORIZE_URL = "https://api.x.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.x.com/oauth/access_token"


def authorize(consumer_key: str, consumer_secret: str) -> None:
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri="oob")

    request_token = oauth.fetch_request_token(REQUEST_TOKEN_URL)

    authorize_url = oauth.authorization_url(AUTHORIZE_URL)
    print("1. Log into the X account you want to authorize in your browser.")
    print("2. Open this URL and click 'Authorize app':")
    print(f"\n   {authorize_url}\n")

    pin = input("3. Enter the PIN X shows you: ").strip()

    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=request_token["oauth_token"],
        resource_owner_secret=request_token["oauth_token_secret"],
        verifier=pin,
    )
    tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)

    print("\nAuthorized successfully. Match this to the correct x_accounts row by screen_name:\n")
    print(f"  screen_name (@)      : {tokens.get('screen_name')}")
    print(f"  user_id              : {tokens.get('user_id')}")
    print(f"  access_token         : {tokens['oauth_token']}")
    print(f"  access_token_secret  : {tokens['oauth_token_secret']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, help="Consumer/API key of the target X app")
    parser.add_argument("--secret", required=True, help="Consumer/API secret of the target X app")
    args = parser.parse_args()

    authorize(args.key, args.secret)


if __name__ == "__main__":
    main()
