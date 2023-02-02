#!/usr/bin/python
"""Find any new episodes available for Jellyfin's list of TV shows."""
import sys
import argparse
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

TODAY = datetime.datetime.now().date()
MAX_EPISODES_TO_DISPLAY = 5
# ref: https://github.com/jellyfin/jellyfin-web/blob/master/src/controllers/playback/video/index.js#L30
TICKS_PER_MINUTE = 600000000

# A user that has "Display missing episodes within seasons" enabled in their profile
# FIXME: WTF?! Just tell every user to do this, it's not actually annoying in the UX
USER_WITH_MISSING = 'FIXME'


def str_endswith_forwardslash(s):
    """Just make sure the string ends with a '/'."""
    return s if s.endswith('/') else s + '/'


def str_lower_type(value: str):
    """Lower case string type for ArgParse."""
    return value.lower()


def _get_IMDBid(series):
    # FIXME: Is rpartition really the best way to do this?
    return series['ExternalUrls']['IMDb'].rpartition('/')[-1] if 'IMDb' in series['ExternalUrls'] else None


def print_for_humans(series: dict, missing_series_episodes: list):
    """Human-readable output method for sending in emails."""
    # FIXME: Theoretically this URL belongs inside Jellyfin, but that requires a whole plugin and I CBFed
    ExternalUrls = {e['Name']: e['Url'] for e in series['ExternalUrls']}
    IMDBid = _get_IMDBid(series)
    # NOTE: RARBG gives a 404 if there's no '/' on the end of this URL
    # NOTE: RARBG is sometimes a bit delayed at adding episodes to this "TV browser", maybe just stick with the search URL?
    ExternalUrls['RARBG'] = (urllib.parse.urljoin("http://rarbg.to/tv/", IMDBid + '/') if IMDBid else
                             "http://rarbg.to/torrents.php?" + urllib.parse.urlencode({'search': series['Name']}))

    print(f"{series['Name']} ({ExternalUrls['RARBG']})")
    count = 0
    for episode in missing_series_episodes:
        if count >= MAX_EPISODES_TO_DISPLAY:
            # Don't let 1 series fill the screen
            print(f"* ... and {len(missing_series_episodes) - MAX_EPISODES_TO_DISPLAY} more")
            break
        else:
            count += 1
        print(f"* {episode['SeasonName']}",
              f"S{episode.get('ParentIndexNumber', 0):02}E{episode.get('IndexNumber', 0):02}",
              f"{episode['Name']}  (Premiered: {episode['PremiereDate']})",
              sep=' - ')


def print_for_homeassistant(series: dict, missing_series_episodes: list):
    """Machine-readable output method for use with Home Assistant's command line sensor."""
    # We only actually care about one per show for this output
    episode = missing_series_episodes[0]

    imdb_id = _get_IMDBid(series)

    rating = episode.get('OfficialRating', series.get('OfficialRating', None))
    comm_rating = episode.get('CommunityRating', series.get('CommunityRating', None))

    item = {
        "title": episode['SeriesName'],
        "episode": episode['Name'],
        "flag": False,  # FIXME: What does this mean? Seen? None of these are seen, maybe I can use it for something else?
        # FIXME: Do I really need to combine the time into it?
        "airdate": datetime.datetime.combine(episode['PremiereDate'], datetime.datetime.min.time()).isoformat(),
        # FIXME: Use an f-string
        "number": "S{se:02}E{ep:02}".format(se=episode.get('ParentIndexNumber', 0), ep=episode.get('IndexNumber', 0)),
        "runtime": int(episode['RuntimeTicks'] / TICKS_PER_MINUTE) if 'RuntimeTicks' in episode else None,
        "studio": f"{episode['SeriesStudio']} - {imdb_id}" if 'SeriesStudio' in episode else imdb_id,
        "release": episode['PremiereDate'].strftime('%d/%m/%Y'),
        # "poster": f"{args.home_assistant}/Items/{episode['Id']}/Images/Primary?MaxWidth=500&format=jpg",
        "poster": urllib.parse.urljoin(args.home_assistant,
                                       f"Items/{episode['Id']}/Images/Primary?MaxWidth=500&format=jpg")
                  if 'Primary' in episode.get('ImageTags', {}) else urllib.parse.urljoin(
                      args.home_assistant, f"Items/{series['Id']}/Images/Primary?MaxWidth=500&format=jpg"),
        "fanart": None,  # FIXME
        "genres": series.get('Genres', []),  # FIXME: Should this be a string?
        # "genres": ', '.join(series.get('Genres', [])),
        "rating": f"{rating} - {comm_rating}" if rating and comm_rating else rating or comm_rating,
        "stream_url": None,  # This will never be usable as we are specifically getting missing episodes
        "info_url": urllib.parse.urljoin(args.home_assistant, f"web/index.html#!/details?id={episode['Id']}"),
    }

    json.dump(item, sys.stdout)


argparser = argparse.ArgumentParser(description=__doc__)
argparser.add_argument('--base-url', type=str_endswith_forwardslash, default='http://media/',
                       help="Jellyfin's base URL")
argparser.add_argument('--user', type=str_lower_type, nargs='*',
                       help="Jellyfin user name")
argparser.add_argument('--ignore-specials', action='store_true',
                       help='Ignore episodes in season 00, usually non-canon behind-the-scenes stuff or Christmas specials')
argparser.add_argument('--home-assistant', metavar='base HTTPS URL for images', type=str,
                       help=('Generate output for use with a Home Assistant command line sensor to populate an "Upcoming Media'
                             'Card" from https://github.com/custom-cards/upcoming-media-card'))
group = argparser.add_mutually_exclusive_group(required=True)
group.add_argument('--token', type=str,
                   help="Jellyfin API key to use")
group.add_argument('--token-file', type=pathlib.Path,
                   help="File handle to get the Jellyfin API key from")

args = argparser.parse_args()

if args.token:
    if not args.home_assistant:
        print("WARNING: It is recommended you use --token-file instead of --token")
    api_key = args.token
else:
    with args.token_file.open('r') as token_file:
        api_key = token_file.read().strip()


endpoint_url = urllib.parse.urljoin(args.base_url, 'Items')

base_headers = {'accept': 'application/json', 'X-Emby-Token': api_key}

users_req = urllib.request.Request(urllib.parse.urljoin(args.base_url, 'Users?isHiden=False&isDisabled=False'),
                                   headers={'accept': 'application/json', 'X-Emby-Token': api_key}, method='GET')
with urllib.request.urlopen(users_req) as users_resp:
    users = json.loads(users_resp.read())
    if not args.user:
        user_ids = set(u['Id'] for u in users if u['HasPassword'])
    else:
        user_ids = set(u['Id'] for u in users if u['Name'].lower() in args.user)

###
### Get relevant user's played episodes and active series
###
active_series = set()
all_played_ids = set()
for user in user_ids:
    user_played_query_str = urllib.parse.urlencode(dict(includeItemTypes='Episode',
                                                        fields='Id,SeriesId',
                                                        IsPlayed=True,
                                                        userId=user,
                                                        recursive=True,
                                                        enableImages=False))
    with urllib.request.urlopen(urllib.request.Request(endpoint_url + '?' + user_played_query_str,
                                                       headers=base_headers, method='GET')) as user_played_response:
        for ep in json.loads(user_played_response.read().decode())['Items']:
            all_played_ids.add(ep['Id'])
            active_series.add(ep['SeriesId'])

###
### Drop any series that are not still going
###
continuing_series_query = urllib.parse.urlencode(dict(includeItemTypes='Series',  # Don't want episode items here
                                                      seriesStatus='Continuing',  # Don't care about ended series
                                                      fields='ExternalUrls',  # For IMDB IDs
                                                      enableImages=False,
                                                      recursive=True))
continuing_series_req = urllib.request.Request(endpoint_url + f'?userId={USER_WITH_MISSING}&' + continuing_series_query,
                                               headers=base_headers,
                                               method='GET')
with urllib.request.urlopen(continuing_series_req) as continuing_series_resp:
    series_data = {series['Id']: series for series in json.loads(continuing_series_resp.read())['Items']}
    active_series.intersection_update(series['Id'] for series in series_data.values())

# At this point 'active_series' is only series IDs that have had any episodes watched, and have a status of "continuing"

###
### Get *all* episodes for each active series
###
# FIXME: This is horrible
if args.home_assistant:
    print('{"data": [')
    json.dump({'title_default': '$title',
               'line1_default': '$number - $episode',
               'line2_default': '$release',
               'line3_default': '$rating',
               'line4_default': '$studio',
               'icon': 'mdi:arrow-down-bold-circle'}, sys.stdout)

series_episodes_query = urllib.parse.urlencode(dict(includeItemTypes='Episode',  # Only want episodes
                                                    fields='Path',  # To determine if we already have it
                                                    enableImages=False,
                                                    enableUserData=False,
                                                    recursive=True))
for series_id in active_series:
    series = series_data[series_id]
    series_url = urllib.parse.urljoin(endpoint_url,
                                      f'Shows/{series_id}/Episodes?userId={USER_WITH_MISSING}&' + series_episodes_query)
    series_episodes_req = urllib.request.Request(series_url, headers=base_headers, method='GET')
    with urllib.request.urlopen(series_episodes_req) as series_episodes_resp:
        series_episodes = json.loads(series_episodes_resp.read())['Items']

    # Change the PremiereDate field into a more useful object type
    for episode in series_episodes:
        episode['PremiereDate'] = datetime.datetime.strptime(episode.get(
            'PremiereDate', f'{datetime.MAXYEAR}-12-31T00:00:00.0000000Z'), '%Y-%m-%dT%H:%M:%S.%f0Z').date()

    # Sort the list in reverse PremiereDate and remove "future" episodes
    series_episodes = sorted([ep for ep in series_episodes if ep['PremiereDate'] <= TODAY],
                             key=lambda ep: (ep['PremiereDate'], ep['ParentIndexNumber'], ep.get('IndexNumber', 0)),
                             reverse=True)  # In reverse so we can start from the newest and work backwards until we stop

    ###
    ### Find the missing episodes for this series
    ###
    missing_series_episodes = []
    for episode in series_episodes:
        # Ignore special episodes from the list if we don't care on this run
        if args.ignore_specials and episode['ParentIndexNumber'] == 0 and episode['SeasonName'] == 'Specials':
            continue
        elif 'Path' not in episode and episode['Id'] not in all_played_ids:
            # This episode is missing and has not been watched by any users.
            #
            # Insert to the beginning of the list to invert the reversed sort.
            # This just makes it more human-readable
            missing_series_episodes.insert(0, episode)
        else:
            # Found an episode that isn't missing, and hasn't been watched by any user.
            # Stop scanning here and assume everything older has been seen.
            # This way season 1 can be deleted while watching season 2 without constant pestering that season 1 is missing
            break

    if missing_series_episodes and not args.home_assistant:
        print_for_humans(series, missing_series_episodes)
    elif missing_series_episodes and args.home_assistant:
        print(', ')
        print_for_homeassistant(series, missing_series_episodes)

# FIXME: This is horrible
if args.home_assistant:
    print(']}')
