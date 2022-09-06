#!/usr/bin/python3
"""Find any new episodes available for Jellyfin's list of TV shows."""
import sys
import argparse
import collections
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

INFINITE_AGE = datetime.datetime(datetime.MINYEAR, 1, 1).date()
# ref: https://github.com/jellyfin/jellyfin-web/blob/master/src/controllers/playback/video/index.js#L30
TICKS_PER_MINUTE = 600000000


def str_endswith_forwardslash(s):
    """Just make sure the string ends with a '/'."""
    return s if s.endswith('/') else s + '/'


argparser = argparse.ArgumentParser(description=__doc__)
argparser.add_argument('--base-url', type=str_endswith_forwardslash, default='http://media/',
                       help="Jellyfin's base URL")
argparser.add_argument('--user-id', type=str, required=True,
                       help="User ID to check for watched status")
argparser.add_argument('--ignore-specials', action='store_true',
                       help='Ignore episodes in season 00, usually non-canon behind-the-scenes stuff or Christmas specials')
group = argparser.add_mutually_exclusive_group(required=True)
group.add_argument('--token', type=str,
                   help="Jellyfin API key to use")
group.add_argument('--token-file', type=pathlib.Path,
                   help="File handle to get the Jellyfin API key from")

args = argparser.parse_args()

if args.token:
    # FIXME: Can we do a '!secret foo' to query it from Home Assistant directly?
    # print("WARNING: It is recommended you use --token-file instead of --token", file=sys.stderr)
    api_key = args.token
else:
    with args.token_file.open('r') as token_file:
        api_key = token_file.read().strip()

endpoint_url = urllib.parse.urljoin(args.base_url, 'Items')

base_headers = {'accept': 'application/json', 'X-Emby-Token': api_key}

# FIXME: I can't use lists or repeat keys
base_search_query = {
    # NOTE: Nothing runs *as* this user, it just queries for library items this user has access to.
    #       I would like to just query for items the given session has permission to see, but it doesn't work that way.
    'userId': args.user_id,
    'enableImages': False,  # Unused, so don't add the extra effort
    'recursive': True,  # Look at the episodes themselves, not just the show
}

###
### Get data for all episodes
###

# "missing" episodes don't get given a parentId,
# and I can't search by "seriesId" which they do get.
# So in order to find them properly I have to actually find *all* episodes and go from there.
#
# I probably should be using the seriesId instead of the seriesName,
# but seriesName has looked unique so far and it makes things a bit easier when debugging.
allepisodes_query_str = urllib.parse.urlencode(dict(includeItemTypes='Episode',  # Only want episodes
                                                    isUnaired=False,  # That haven't aired yet
                                                    fields='Path,SeriesStudio,RunTimeTicks,ImageTags',
                                                    **base_search_query))
allepisodes_req = urllib.request.Request(endpoint_url + '?' + allepisodes_query_str,
                                         headers=base_headers,
                                         method='GET')

episodes_by_series = collections.defaultdict(lambda: [])
with urllib.request.urlopen(allepisodes_req) as allepisodes_response:
    allepisodes_data = json.loads(allepisodes_response.read().decode())

    for episode in allepisodes_data['Items']:
        # The includeItemTypes above ensures this, but let's double check anyway
        assert episode['Type'] == 'Episode', episode

        # We often don't care about "specials" in season 00,
        # so just don't even process them at all.
        if args.ignore_specials and episode['ParentIndexNumber'] == 0 and episode['SeasonName'] == 'Specials':
            continue

        # Turn the PremiereDate into something we can use programmatically later
        # FIXME: Should I convert any other things while I'm at it?
        episode['PremiereDate'] = datetime.datetime.strptime(episode['PremiereDate'], '%Y-%m-%dT%H:%M:%S.%f0Z').date()
        episodes_by_series[episode['SeriesName']].append(episode)

###
### Process that data one series at a time
###

# The only reason for doing this 2nd query is so we can ignore the series that aren't "Continuing".
# Since that data is not visible in the episodes query above at all
allseries_query_str = urllib.parse.urlencode(dict(includeItemTypes='Series',  # Don't want episode items here
                                                  seriesStatus='Continuing',  # Don't care about ended series
                                                  fields='ExternalUrls,Genres,ImageTags',
                                                  **base_search_query))
allseries_req = urllib.request.Request(endpoint_url + '?' + allseries_query_str,
                                       headers=base_headers,
                                       method='GET')
with urllib.request.urlopen(allseries_req) as allseries_response:
    allseries_data = json.loads(allseries_response.read().decode())
    # Let's do this in alphabetical order
    # FIXME: Use a smarter key that understands "^The ..."
    allseries_data['Items'].sort(key=lambda i: i['Name'])

# I don't actually understand what this first data entry is
# Presumably some sort of template for rendering the rest of it
data = [{
    'title_default': '$title',
    'line1_default': '$number - $episode',
    'line2_default': '$release',
    'line3_default': '$rating',
    'line4_default': '$studio',
    'icon': 'mdi:arrow-down-bold-circle',
}]
for series in allseries_data['Items']:
    # The includeItemTypes above ensures this, but let's double check anyway
    assert series['Type'] == 'Series', series

    episodes_by_series[series['Name']].sort(
        key=lambda i: (i['PremiereDate'], i['ParentIndexNumber'], i.get('IndexNumber', 0)),  # Sort episodes by PremiereDate
        reverse=True)  # In reverse so we can start from the newest and work backwards until we stop

    missing_episodes_of_this_series = []
    for episode in episodes_by_series[series['Name']]:
        if 'Path' not in episode and not episode['UserData'].get('Played'):
            # This episode is missing and has been not watched by the specified user.
            #
            # Insert to the beginning of the list to invert the reversed sort.
            # This really just makes it more human-readable
            missing_episodes_of_this_series.insert(0, episode)
        else:
            # Found an episode that isn't missing, and hasn't been watched by the specific user.
            # Stop scanning here and assume everything older has been seen.
            # This way season 1 can be deleted while watching season 2 without constant pestering that season 1 is missing
            break
    if missing_episodes_of_this_series:
        episode = missing_episodes_of_this_series[0]
        del missing_episodes_of_this_series

        imdb_url, = (url['Url'] for url in series.get('ExternalUrls', []) if url.get('Name') == 'IMDb')
        imdb_id = imdb_url.rpartition('/')[-1]

        rating = episode.get('OfficialRating', series.get('OfficialRating', None))
        comm_rating = episode.get('CommunityRating', series.get('CommunityRating', None))

        data.append({
            "title": episode['SeriesName'],
            "episode": episode['Name'],
            "flag": False,  # FIXME: What does this mean? Seen? None of these are seen, that's the point
            # FIXME: Do I really need to combine the time into it?
            "airdate": datetime.datetime.combine(episode['PremiereDate'], datetime.datetime.min.time()).isoformat(),
            # FIXME: Use an f-string
            "number": "S{se:02}E{ep:02}".format(se=episode.get('ParentIndexNumber', 0), ep=episode.get('IndexNumber', 0)),
            "runtime": int(episode['RuntimeTicks'] / TICKS_PER_MINUTE) if 'RuntimeTicks' in episode else None,
            "studio": f"{episode['SeriesStudio']} - {imdb_id}" if 'SeriesStudio' in episode else imdb_id,
            "release": episode['PremiereDate'].strftime('%d/%m/%Y'),
            # "poster": f"{args.base_url}/Items/{episode['Id']}/Images/Primary?MaxWidth=500&format=jpg",
            "poster": urllib.parse.urljoin(args.base_url,
                                           f"Items/{episode['Id']}/Images/Primary?MaxWidth=500&format=jpg")
                      if 'Primary' in episode.get('ImageTags', {}) else urllib.parse.urljoin(
                          args.base_url, f"Items/{series['Id']}/Images/Primary?MaxWidth=500&format=jpg"),
            "fanart": None,  # FIXME
            "genres": series.get('Genres', []),  # FIXME: Should this be a string?
            # "genres": ', '.join(series.get('Genres', [])),
            "rating": f"{rating} - {comm_rating}" if rating and comm_rating else rating or comm_rating,
            "stream_url": None,  # This will never be usable as we are specifically getting missing episodes
            "info_url": urllib.parse.urljoin(args.base_url, f"web/index.html#!/details?id={episode['Id']}"),
        })

json.dump({'data': data}, sys.stdout)
