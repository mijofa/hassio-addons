#!/usr/bin/python3
"""
Query TramTracker's ReST-like API for stop & route information.

FIXME: Turn this into a HACS compatible custom_component instead of a command_line sensor.
"""
import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request

argparser = argparse.ArgumentParser(description=__doc__)
argparser.add_argument('--stop-id', type=int, required=True,
                       help="TramTracker stop ID")
argparser.add_argument('--route-id', type=int, required=False, default=0,
                       help='[OPTIONAL, only useful with some commands] TramTracker route ID')
argparser.add_argument('--route-direction', type=int, required=False, choices=('up', 'down'),
                       help='[OPTIONAL, only useful with some commands] TramTracker route direction (up = towards city)')

argparser.add_argument('command', type=str, default=None, nargs='?',
                       help='The TramTracker API command to query')

# NOTE: This must end with a forwards slash otherwise the urljoins make a mess
argparser.add_argument('--base-url', type=str, default='http://tramtracker.com/Controllers/',
                       help=argparse.SUPPRESS)


def _date2str_serialiazer(input_date: datetime.datetime):
    """Convert a datetime object into a string for json serialization."""
    if not isinstance(input_date, datetime.datetime):
        raise TypeError(f'Object of type {input_date.__class__.__name__} is not JSON serializable')
    else:
        # FIXME: Is this the best format for Home Assistant or should I just use Epoch time?
        return input_date.isoformat()


def _maybe_parse_tramtracker_timestamp(input_string):
    if not (input_string.startswith('/Date(') and input_string.endswith(')/')):
        return input_string
    else:
        timepart = input_string[len('/Data('):-len(')/')]

        # Bit of a messy way of turning "+1030" style timezone offset into a tzinfo object
        tzinfo = datetime.timezone(datetime.timedelta(
            hours=int(timepart[-5:-2]),
            minutes=int(timepart[-5] + timepart[-2:])))

        milliseconds = int(timepart[:-5])
        seconds = milliseconds / 1000

        # This is a timezone-aware datetime object.
        # We probably want to print this in UTC for better portability, but that's a problem for a separate function
        timestamp = datetime.datetime.fromtimestamp(seconds, tz=tzinfo)

        # # datetime.datetime.now() is not timezone aware, so can't be calculated against timestamp as-is
        # now_timezoneaware = datetime.datetime.now().astimezone()
        # print(timestamp - now_timezoneaware, file=sys.stderr)

        return timestamp


def _fix_dict_timestamps(input_dict):
    # FIXME: This whole function should be part of the JSON serializer... is writing one of those myself easy?
    output_dict = input_dict.copy()
    for k, v in input_dict.items():
        if isinstance(v, str):
            output_dict[k] = _maybe_parse_tramtracker_timestamp(v)
        elif isinstance(v, list):
            # FIXME: What if it's a list of dicts?
            output_dict[k] = [_maybe_parse_tramtracker_timestamp(i) for i in v]
        elif isinstance(v, dict):
            output_dict[k] = _fix_dict_timestamps(input_dict[k])
        # FIXME: Where does 'NoneType' come from?
        # NOTE: I thought float & int were the same object type nowadays in py3?
        elif isinstance(v, (int, float, bool, type(None))):
            pass
        else:
            raise NotImplementedError("Unrecognized object type in dict " + repr(type(v)))

    return output_dict


def _tramtracker_query(endpoint: str, **kwargs):
    if not base_url:
        raise RuntimeError("base_url must be set before running any queries")

    tramtracker_url = urllib.parse.urljoin(base_url, endpoint) + '.ashx'

    form_data = urllib.parse.urlencode(kwargs).encode()
    print(tramtracker_url, form_data)
    with urllib.request.urlopen(tramtracker_url, data=form_data) as req:
        response_data = json.loads(req.read())
        # I've only seen 'HasError' with 'GetPassingRoutes' and 'GetStopInformation'
        assert 'hasError' in response_data or 'HasError' in response_data
        if (response_data.get('hasError')) or (response_data.get('HasError')):
            # FIXME: Define my own exception type for this
            if 'errorMessage' in response_data:
                raise RuntimeError(response_data['errorMessage'])
            else:
                # I've only seen 'ResponseString' with 'GetPassingRoutes' and 'GetStopInformation'
                raise RuntimeError(response_data['ResponseString'])
        elif 'hasResponse' in response_data and response_data['hasResponse']:
            if isinstance(response_data['responseObject'], list):
                return [_fix_dict_timestamps(i) if isinstance(i, dict) else i for i in response_data['responseObject']]
            elif isinstance(response_data['responseObject'], dict):
                return _fix_dict_timestamps(response_data['responseObject'])
            else:
                return response_data['responseObject']
        elif 'ResponseObject' in response_data:
            # For some reason 'GetPassingRoutes' and 'GetStopInformation' just behaves completely different from the rest
            if isinstance(response_data['ResponseObject'], list):
                return [_fix_dict_timestamps(i) if isinstance(i, dict) else i for i in response_data['ResponseObject']]
            elif isinstance(response_data['ResponseObject'], dict):
                return _fix_dict_timestamps(response_data['ResponseObject'])
            else:
                return response_data['ResponseObject']
        else:
            print(response_data, file=sys.stderr)
            raise NotImplementedError('TramTracker had no error or response data')


# FIXME: If I make an object class, can all these be generated at run time instead?
# FIXME: I know the actual TramTracker API hasn't standardised on argument names, but I probably should.
#        s == StopNo; r == RouteNo == routeNow
def GetStopInformation(s: int):
    """Get misc info for the given stop."""
    return _tramtracker_query('GetStopInformation', s=s)


def GetPassingRoutes(s: int):
    """Get the routes that pass through the given stop."""
    return _tramtracker_query('GetPassingRoutes', s=s)


def GetRouteColour(RouteNo: int):
    """Get background colour for the given route."""
    return _tramtracker_query('GetRouteColour', routeNo=RouteNo)


def GetRouteTextColour(RouteNo: int):
    """Get foreground colour for the given route."""
    return _tramtracker_query('GetRouteTextColour', routeNo=RouteNo)


def GetNextPredictionsForStop(stopNo: int, routeNo: int = 0, isLowFloor: bool = False):
    """Get ETA of the next few trams stopping at the given stop."""
    return _tramtracker_query('GetNextPredictionsForStop', stopNo=stopNo, routeNo=routeNo, isLowFloor=isLowFloor)


# Currently unused
def GetAllRoutes():
    """Get all routes."""
    return _tramtracker_query('GetAllRoutes')


# Currently unused
def GetStopsByRouteAndDirection(r: int, u):
    """Get all stops for a given route & direction."""
    # FIXME: What's 'u'? Presumably direction, yeah? Should I just query both?
    #        I think this corresponds to GetAllRoutes()'s "IsUpDirection" which presumably means "city-bound"?
    return _tramtracker_query('GetStopsByRouteAndDirection', r=r, u=True)


# My own function because this should just be one call
def stop_info(stop_id: int):
    """Get useful info for the given stop."""
    # FIXME: Is there a colour or hex object I can/should use instead?
    # NOTE: The official website repeats these colour requests once per line every single timing update.
    #       Equivalent to doing individual requests in the for loop below.
    #       So even though this might look a bit messy & inefficient, I'm still doing better than them.
    route_background_colours = {c['RouteNo']: ('#' + c['Colour']) for c in (GetRouteColour(**r)
                                                                            for r in GetPassingRoutes(s=args.stop_id))}
    route_foreground_colours = {c['RouteNo']: ('#' + c['Colour']) for c in (GetRouteTextColour(**r)
                                                                            for r in GetPassingRoutes(s=args.stop_id))}
    predictions = GetNextPredictionsForStop(stopNo=args.stop_id)
    for tram in predictions:
        assert 'RouteColour' not in tram and 'RouteTextColour' not in tram
        tram['RouteColour'] = route_background_colours[tram['RouteNo']]
        tram['RouteTextColour'] = route_foreground_colours[tram['RouteNo']]

    # NOTE: The oficial website usually just queries the stop info once, then the predictions every N seconds (20s from what I saw)
    #       Since this will be rerunning both requests every time it's a **little** harsher on the StopInfo endpoint than them,
    #       but it's nicer enough in other ways that I don't currently care.
    # FIXME: Longer term I could use a custom_components integration, or multiple command_line sensors to separate these calls
    stop_info = GetStopInformation(s=stop_id)
    assert 'Predictions' not in stop_info
    stop_info['Predictions'] = predictions

    return stop_info


if __name__ == '__main__':
    args = argparser.parse_args()
    base_url = args.base_url

    if args.command:
        if args.command == 'GetAllRoutes':
            json.dump(GetAllRoutes(), fp=sys.stdout,
                      default=_date2str_serialiazer,  # Fallback serializer for objects that can't be JSON serialized
                      indent=4,  # Avoids the need for pprint.pprint without breaking `|jq .`
                      )
        elif args.command == 'GetNextPredictionsForStop':
            json.dump(GetNextPredictionsForStop(stopNo=args.stop_id, routeNo=args.route_id), fp=sys.stdout,
                      default=_date2str_serialiazer,  # Fallback serializer for objects that can't be JSON serialized
                      indent=4,  # Avoids the need for pprint.pprint without breaking `|jq .`
                      )
        else:
            raise NotImplementedError("Coming soon.")
        # FIXME: It's not as simple as: pprint.pprint(_tramtracker_query(args.command, stopNo=args.stop_id))
        #        because some endpoints require certain args even if empty, such as 'GetNextPredictionsForStop'.
        #        This is handled in the other calls by setting arg defaults in the Python functions,
        #        so I should just call those python functions... somehow.
        #        Perhaps if I create TramTracker object class I can then run 'eval(globals=None,locals=dict(...)) on that?
    else:
        # FIXME: This should output as JSON, but I need to solve datetime serialization first.
        #        Home Assistant can fairly easily convert '.isoformat()' back into a usable datetime object.
        json.dump(stop_info(stop_id=args.stop_id), fp=sys.stdout,
                  default=_date2str_serialiazer,  # Fallback serializer for objects that can't be JSON serialized
                  indent=4,  # Avoids the need for pprint.pprint without breaking `|jq .`
                  )
    # pprint.pprint(GetPassingRoutes(s=args.stop_id))
    # for kwargs in GetPassingRoutes(s=args.stop_id):
    #     pprint.pprint(GetRouteColour(**kwargs))
    #     pprint.pprint(GetRouteTextColour(**kwargs))
    # pprint.pprint(GetNextPredictionsForStop(stopNo=args.stop_id))
