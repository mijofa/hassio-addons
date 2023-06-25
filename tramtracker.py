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
argparser.add_argument('--stop-id', type=int, required=False,
                       help="TramTracker stop ID")
argparser.add_argument('--route-id', type=int, required=False, default=0,
                       help='[OPTIONAL, only useful with some commands] TramTracker route ID')
argparser.add_argument('--route-direction', type=str, required=False, choices=('up', 'down'),
                       help='[OPTIONAL, only useful with some commands] TramTracker route direction (up = towards city)')

argparser.add_argument('command', type=str, default=None, nargs='?',
                       help='The TramTracker API command to query')

# NOTE: This must end with a forward slash otherwise the urljoins make a mess
argparser.add_argument('--base-url', type=str, default=None,
                       help=argparse.SUPPRESS)


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""

    def default(self, input_date: datetime.datetime) -> str:
        """Convert a datetime object into a string for json serialization."""
        if not isinstance(input_date, (datetime.datetime, datetime.date)):
            raise TypeError(f'Object of type {input_date.__class__.__name__} is not JSON serializable')
        else:
            # FIXME: Is this the best format for Home Assistant or should I just use Epoch time?
            return input_date.isoformat()


class JSONDecoder(json.JSONDecoder):
    """Custom JSON decoder to handle Microsoft's JSON date format."""

    def __init__(self, **kwargs):
        """Just call upstream's JSONDecoder with the local object hook."""
        super().__init__(**kwargs, object_hook=self._str2date_object_hook)

    def _str2date_object_hook(self, input_object: dict) -> dict:
        """Take a dict, and turn any '/Date(...)/' strings into datetime objects."""
        if not isinstance(input_object, dict):
            raise NotImplementedError("I didn't think it worked thhis way.""")

        output_object = input_object.copy()
        for k, v in input_object.items():
            if isinstance(v, str):
                # FIXME: Should I just use a regex here?
                if v.startswith('/Date(') and v.endswith(')/'):
                    timepart = v[len('/Data('):-len(')/')]
                    # Bit of a messy way of turning "+1030" style timezone offset into a tzinfo object
                    tzinfo = datetime.timezone(datetime.timedelta(
                        hours=int(timepart[-5:-2]),
                        minutes=int(timepart[-5] + timepart[-2:])))

                    milliseconds = int(timepart[:-5])
                    seconds = milliseconds / 1000

                    # This is a timezone-aware datetime object.
                    # We probably want to print this in UTC for better portability, but that's a problem for a separate function
                    output_object[k] = datetime.datetime.fromtimestamp(seconds, tz=tzinfo)
            elif isinstance(v, dict):
                # In theory we've already handled this since the objects pass through this function from the deepest levels first
                pass
            elif isinstance(v, (list, tuple)):
                # FIXME: Does this pass through here? How does this work?
                #        If it's a list of strings, should we be checking them for datetime strings?
                pass
            # FIXME: Where does 'NoneType' come from?
            elif isinstance(v, (int, float, bool, type(None))):
                # We don't care about these at all
                pass
            else:
                # This shouldn't even be possible
                raise NotImplementedError("Unrecognized object type in dict " + repr(type(v)))

        return output_object


class TramTracker(object):
    """TramTracker API object."""

    # NOTE: There is also 'https://tramtracker.com.au/Controllers/' which works just as well,
    #       but since there's nothing private about this data I might as well reduce the processing power and stick to http
    def __init__(self, base_url: str = 'http://tramtracker.com/Controllers/'):
        """Initialize the object."""
        self.base_url = base_url

    def _tramtracker_query(self, endpoint: str, **kwargs):
        tramtracker_url = urllib.parse.urljoin(self.base_url, endpoint) + '.ashx'

        form_data = urllib.parse.urlencode(kwargs).encode()
        with urllib.request.urlopen(tramtracker_url, data=form_data) as req:
            data = req.read()
            try:
                response_data = json.loads(data, cls=JSONDecoder)
            except:
                print(data, file=sys.stderr)
                raise
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
                return response_data['responseObject']
            elif 'ResponseObject' in response_data:
                # For some reason 'GetPassingRoutes' and 'GetStopInformation' just behaves completely different from the rest
                return response_data['ResponseObject']
            else:
                print(response_data, file=sys.stderr)
                raise NotImplementedError('TramTracker had no error or response data')

    def __getattr__(self, attr: str):
        """Turn every (undefined) function call into an API query."""
        return lambda **kwargs: self._tramtracker_query(attr, **kwargs)

    # # Currently unused
    # # FIXME: Should return TramTrackerRoute objects for all routes.
    # def GetAllRoutes(self):
    #     """Get all routes."""
    #     return self._tramtracker_query('GetAllRoutes')


class TramTrackerRoute(object):
    """TramTracker route info."""

    # FIXME: This object should probably have a lot more info such as that returned by GetAllRoutes,
    #        but I can only query that for all routes at once, not one at a time.
    def __init__(self, route_id: int, api: TramTracker = TramTracker()):
        """Initialize the object."""
        self._api = api
        self.route_id = route_id

        # FIXME: Should this be a 3-tuple of ints? Or is there a "colour" object type I can use?
        self.Colour = '#' + self._api.GetRouteColour(RouteNo=self.route_id)['Colour']
        self.TextColour = '#' + self._api.GetRouteTextColour(RouteNo=self.route_id)['Colour']

    # Currently unused
    def GetStopsByDirection(self, IsUpDirection: bool):
        """Get all stops for this route in the given direction."""
        # NOTE: As far as I can tell 'u' here corresponds to the IsUpDirection from GetAllRoutes.
        #       Pretting sure "Up" in this case actually means "city-bound"
        return self._tramtracker_query('GetStopsByRouteAndDirection', r=self.route_id, u=IsUpDirection)


class TramTrackerStop(object):
    """TramTracker stop info."""

    def __init__(self, stop_id: int, api: TramTracker = TramTracker()):
        """Initialize the object."""
        self._api = api
        self.stop_id = stop_id

        self.Information = self._api.GetStopInformation(s=self.stop_id)
        self.PassingRoutes = {r['RouteNo']: TramTrackerRoute(r['RouteNo'], api=self._api)
                              for r in self._api.GetPassingRoutes(s=self.stop_id)}

    def GetNextPredictions(self, routeNo: int = 0, isLowFloor: bool = False):
        """Get the next predicted predictions for trams at this stop."""
        predictions = self._api.GetNextPredictionsForStop(stopNo=self.stop_id, routeNo=routeNo, isLowFloor=isLowFloor)
        for tram in predictions:
            assert 'RouteColour' not in tram and 'RouteTextColour' not in tram
            tram['RouteColour'] = self.PassingRoutes[tram['RouteNo']].Colour
            tram['RouteTextColour'] = self.PassingRoutes[tram['RouteNo']].TextColour

        return predictions

    def get_all(self):
        """Get all information for this stop, including predictions."""
        assert 'NextPredictions' not in self.Information
        data = self.Information.copy()
        data['NextPredictions'] = self.GetNextPredictions()

        return data


if __name__ == '__main__':  # noqa: C901
    args = argparser.parse_args()

    if args.base_url:
        TT = TramTracker(args.base_url)
    else:
        TT = TramTracker()

    if not args.command:
        if not args.stop_id:
            argparser.error("Stop ID required for default command")
        elif args.stop_id and not args.route_id:
            stop = TramTrackerStop(args.stop_id, api=TT)
            json.dump(stop.get_all(), fp=sys.stdout,
                      cls=JSONEncoder,
                      indent=4,
                      )
        elif args.stop_id and args.route_id:
            stop = TramTrackerStop(args.stop_id, api=TT)
            json.dump(stop.GetNextPredictions(routeNo=args.route_id),
                      cls=JSONEncoder,
                      indent=4, fp=sys.stdout)
    else:
        # FIXME: Make all API calls directly callable, and implement some sort of argument consistency.
        if args.command == 'GetAllRoutes':
            json.dump(TT.GetAllRoutes(),
                      cls=JSONEncoder,
                      indent=4, fp=sys.stdout)
        elif args.command == 'GetNextPredictionsForStop':
            if not args.stop_id:
                argparser.error("Stop ID required for this command")
            json.dump(TT.GetNextPredictionsForStop(stopNo=args.stop_id, routeNo=args.route_id, isLowFloor=False),
                      cls=JSONEncoder,
                      indent=4, fp=sys.stdout)
        elif args.command == 'GetStopsByRouteAndDirection':
            if not args.route_id or not args.route_direction:
                argparser.error("Route ID and direction required for this command")
            json.dump(TT.GetStopsByRouteAndDirection(r=args.route_id,
                                                     u=(True if args.route_direction == 'up' else False)),
                      cls=JSONEncoder,
                      indent=4, fp=sys.stdout)
        else:
            raise NotImplementedError("Coming soon. Maybe")
