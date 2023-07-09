def notify(cur, flight, origin_airport, destination_airport, twitter_details=None, hours_since=None):
    #Generate Flight Map Image
    from flight_map import create_flight_map
    origin_coords = (origin_airport['lat'], origin_airport['lon'])
    destination_coords = (destination_airport['lat'], destination_airport['lon'])
    flight_map_image_name = f"{flight['reg']}_{flight['id']}_flight_map.png"
    create_flight_map(origin_coords, destination_coords,flight_map_image_name)

    import datetime
    #Flight Time
    flight_time = flight['landing_time'] - flight['takeoff_time']
    hours, remainder = divmod(flight_time.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    min_syntax = "Mins" if minutes > 1 else "Min"
    if hours > 0:
        hour_syntax = "Hours" if hours > 1 else "Hour"
        landed_time_msg = (f"Apx. flt. time {int(hours)} {hour_syntax}" +  (f" : {int(minutes)} {min_syntax}. " if minutes > 0 else "."))
    else:
        landed_time_msg = (f"Apx. flt. time {int(minutes)} {min_syntax}.")

    #Start Secondary Output Creation, Miles and Fuel
    second_message = None

    if flight['origin'] != flight['destination']:
        from geopy.distance import geodesic
        distance_mi = float(geodesic(origin_coords, destination_coords).mi)
        distance_nm = distance_mi / 1.150779448
        second_message = f"{'{:,}'.format(round(distance_mi))} mile ({'{:,}'.format(round(distance_nm))} NM) flight from {origin_airport['iata_code'] if origin_airport['iata_code'] != '' else  origin_airport['ident']} to {destination_airport['iata_code'] if destination_airport['iata_code'] != '' else destination_airport['ident']}"
    import configparser
    conf = configparser.ConfigParser()
    conf.read('conf.ini')
    if conf.getboolean("OPTIONS", "FUEL_CO2"):
        from aircraft_type import get_ac_type
        ac_type = get_ac_type(cur, flight['reg'])
        if ac_type is not None:
            print("Running fuel info calc")
            flight_time_min = flight_time.total_seconds() / 60
            from fuel_calc import fuel_calculation, fuel_message
            fuel_info = fuel_calculation(cur ,ac_type, flight_time_min)
            if fuel_info is not None:
                if second_message:
                    second_message += f"\n{fuel_message(fuel_info)}"
                else:
                    second_message = f"{fuel_message(fuel_info)}"

    #Location Strings
    origin_location = f"{origin_airport['municipality']}, {origin_airport['region']}, {origin_airport['iso_country']}"
    destination_location =f"{destination_airport['municipality']}, {destination_airport['region']}, {destination_airport['iso_country']}"

    #Generate Final Flight Message
    time_ago_wording = "24 hours ago" if hours_since <= 25 else f"on {flight['landing_time'].strftime('%-m/%-d')}"
    message = f"""Flew from {origin_location} to {destination_location} {time_ago_wording}.\n{landed_time_msg}"""

    print(message)

    if twitter_details:
        print(f"Posting flight to @{twitter_details['@']}")
        import tweepy
        twitter_app_auth = tweepy.OAuthHandler(twitter_details['key'], twitter_details['secret'])
        twitter_app_auth.set_access_token(twitter_details['access_token'], twitter_details['access_token_secret'])
        v1_tweet_api = tweepy.API(twitter_app_auth, wait_on_rate_limit=True)
        twitter_media_map_obj = v1_tweet_api.media_upload(flight_map_image_name)
        alt_text = f"Reg: {flight['reg']} Flight Map,  SCK MY BALLS ELON "
        v1_tweet_api.create_media_metadata(media_id= twitter_media_map_obj.media_id, alt_text= alt_text)
        v2_tweet_api = tweepy.Client(
            consumer_key=twitter_details['key'],
            consumer_secret=twitter_details['secret'],
            access_token=twitter_details['access_token'],
            access_token_secret=twitter_details['access_token_secret']
        )
        try:
            tweet_rsp = v2_tweet_api.create_tweet(text=message, media_ids=[twitter_media_map_obj.media_id])
            tweet_id = tweet_rsp.data['id']
            if second_message:
                v2_tweet_api.create_tweet(text=second_message, in_reply_to_tweet_id=tweet_id)
        except Exception as e:
            if tweet_rsp.status_code == 429:
                print("x-rate-limit-reset:", tweet_rsp['x-rate-limit-reset'])
            raise(e)
    import os
    os.remove(flight_map_image_name)
