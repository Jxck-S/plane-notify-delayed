from typing import Optional

import requests
from requests_oauthlib import OAuth1

MEDIA_UPLOAD_URL = "https://api.x.com/2/media/upload"
MEDIA_METADATA_URL = "https://api.x.com/2/media/metadata"
POSTS_URL = "https://api.x.com/2/tweets"

REQUEST_TIMEOUT = 30


def _oauth1_session(x_details: dict) -> OAuth1:
    return OAuth1(
        x_details["key"],
        client_secret=x_details["secret"],
        resource_owner_key=x_details["access_token"],
        resource_owner_secret=x_details["access_token_secret"],
    )


def _raise_for_status_with_rate_limit_logging(resp: requests.Response) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        if resp.status_code == 429:
            print("x-rate-limit-reset:", resp.headers.get("x-rate-limit-reset"))
        print(f"X API error {resp.status_code}: {resp.text[:500]}")
        raise


def upload_media(x_details: dict, image_path: str, alt_text: str) -> str:
    """Upload an image to X via the v2 single-shot media upload endpoint and set alt text.

    Images are small enough not to need the chunked (INIT/APPEND/FINALIZE) flow,
    which X reserves for video.

    Returns the media_id.
    """
    auth = _oauth1_session(x_details)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    upload_resp = requests.post(
        MEDIA_UPLOAD_URL,
        auth=auth,
        data={"media_category": "tweet_image", "media_type": "image/png"},
        files={"media": ("image.png", image_bytes, "image/png")},
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status_with_rate_limit_logging(upload_resp)
    media_id = upload_resp.json()["data"]["id"]

    metadata_resp = requests.post(
        MEDIA_METADATA_URL,
        auth=auth,
        json={"id": media_id, "metadata": {"alt_text": {"text": alt_text}}},
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status_with_rate_limit_logging(metadata_resp)

    return media_id


def create_post(
    x_details: dict,
    text: str,
    media_ids: Optional[list] = None,
    in_reply_to_post_id: Optional[str] = None,
) -> str:
    """Create a post on X via API v2. Returns the new post id."""
    auth = _oauth1_session(x_details)

    body: dict = {"text": text}
    if media_ids:
        body["media"] = {"media_ids": media_ids}
    if in_reply_to_post_id:
        body["reply"] = {"in_reply_to_tweet_id": in_reply_to_post_id}

    resp = requests.post(POSTS_URL, auth=auth, json=body, timeout=REQUEST_TIMEOUT)
    _raise_for_status_with_rate_limit_logging(resp)

    return resp.json()["data"]["id"]
