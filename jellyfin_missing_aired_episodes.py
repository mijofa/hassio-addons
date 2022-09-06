#!/usr/bin/python
"""Find any new episodes available for Jellyfin's list of TV shows."""
import argparse
import collections
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

INFINITE_AGE = datetime.datetime(datetime.MINYEAR, 1, 1).date()


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
    print("WARNING: It is recommended you use --token-file instead of --token")
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
                                                    fields='Path',  # To determine if we already have it
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
                                                  fields='ExternalUrls',  # For IMDB IDs
                                                  **base_search_query))
allseries_req = urllib.request.Request(endpoint_url + '?' + allseries_query_str,
                                       headers=base_headers,
                                       method='GET')
with urllib.request.urlopen(allseries_req) as allseries_response:
    allseries_data = json.loads(allseries_response.read().decode())
    # Let's do this in alphabetical order
    # FIXME: Use a smarter key that understands "^The ..."
    allseries_data['Items'].sort(key=lambda i: i['Name'])

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
        # FIXME: Theoretically this URL belongs inside Jellyfin, but that requires a whole plugin and I CBFed
        ExternalUrls = {e['Name']: e['Url'] for e in series['ExternalUrls']}
        if 'IMDb' in ExternalUrls:
            # FIXME: Is rpartition really the best way to do this?
            # NOTE: RARBG gives a 404 if there's no '/' on the end of this URL
            # NOTE: RARBG is sometimes a bit delayed at adding episodes to this "TV browser", maybe just stick with the search URL?
            ExternalUrls['RARBG'] = urllib.parse.urljoin("http://rarbg.to/tv/", ExternalUrls['IMDb'].rpartition('/')[-1]) + '/'
        else:
            ExternalUrls['RARBG'] = "http://rarbg.to/torrents.php?" + urllib.parse.urlencode({'search': series['Name']})

        print("{series[Name]} ({RARBG_URL})".format(series=series, RARBG_URL=ExternalUrls['RARBG']))
        if len(missing_episodes_of_this_series) == len(episodes_by_series[series['Name']]):
            print("* All episodes missing.")
            print("* Have the episodes been deleted without the series itself?")
            continue
        else:
            count = 0
            for i in missing_episodes_of_this_series:
                if count >= 10:
                    # Don't let 1 series fill the screen
                    print("* ... and {0} more".format(len(missing_episodes_of_this_series) - 10))
                    break
                else:
                    count += 1
                print("* {SeasonName}".format(**i),
                      "S{ParentIndexNumber:02}E{IndexNumber:02}".format(
                          ParentIndexNumber=i.get('ParentIndexNumber', 0),
                          IndexNumber=i.get('IndexNumber', 0)),
                      "{Name}  (Premiered: {PremiereDate})".format(**i),
                      sep=' - ')
