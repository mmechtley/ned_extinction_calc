"""
Programmatic interface to the NED Galactic Redding and Extinction Calculator.
Creates an HTTP request based on supplied coordinates and parses the response.
"""
from __future__ import division
import httplib
import urllib
import re
from warnings import warn

__author__ = 'Matt Mechtley'
__copyright__ = '2012, Creative Commons Attribution-ShareAlike 3.0'

_server = 'ned.ipac.caltech.edu:80'
_request_url = '/cgi-bin/calc?'


class HTTPResponseError(Exception):
    def __init__(self, response):
        self.response = response
        self.message = 'Bad response from server\n{} {}'.format(
            response.status, response.reason)


def request_extinctions(ra, dec, filters=('SDSS g',), coord_system='Equatorial',
                        equinox='J2000.0', obs_epoch='2000', as_dict=False):
    """
    Requests Galactic dust extinction values from the NED Galactic Reddening and
    Extinction Calculator. The values returned are those from the Schlafly &
    Finkbeiner 2011 recalibration of the Schlegel, Finkbeiner, & Davis 1998
    extinction map.
    http://ned.ipac.caltech.edu/forms/calculator.html
    Schlafly & Finkbeiner 2011, ApJ, 737, 103
    Schlegel, Finkbeiner, & Davis 1998, ApJ, 500, 525

    :param ra: Right Ascension (or Galactic longitude). (any NED format)
    :param dec: Declination (or Galactic latitude)
    :param filters: list or tuple of filter name strings. The script tries to
        intelligently match to those on the NED output page. If there are
        multiple matches, the average will be returned.
        Examples: 'F125W', 'WFC3 F125W', 'CTIO V', 'SDSS g'
    :param coord_system: Any accepted by NED (Equatorial, Galactic, Ecliptic,
        Supergalactic) Default is Equatorial
    :param equinox: B1950.0 or J2000.0. Default is J2000.0
    :param obs_epoch: observation epoch
    :param as_dict: Return dictionary {input filter: A_lambda} instead of list
    :returns: list of extinction values corresponding to the provided list of
        filters. If a filter is ambiguous and has multiple matches (e.g. 'V'),
        the average of all matches is returned. This allows an estimate even
        if the specific filter is not listed. Returns None (and warns) if
        filter is not found
    """
    try:
        float(ra)
        ra = str(ra) + 'd'
    except ValueError:
        pass
    try:
        float(dec)
        ra = str(dec) + 'd'
    except ValueError:
        pass
    list_out = True
    if isinstance(filters, basestring):
        list_out = False
        filters = [filters]
    get_params = {'lon': str(ra),
                  'lat': str(dec),
                  'pa': '0.0',
                  'in_csys': str(coord_system),
                  'in_equinox': str(equinox),
                  'obs_epoch': str(obs_epoch),
                  'out_csys': 'Equitorial',
                  'out_equinox': 'J2000.0'}

    conn = httplib.HTTPConnection(_server)
    conn.request('GET', _request_url + urllib.urlencode(get_params),
                 headers={'Content-type': 'application/x-www-form-urlencoded'})
    response = conn.getresponse()
    html_output = response.read().split('\n')
    conn.close()
    if response.status != httplib.OK:
        raise HTTPResponseError(response)

    extinctions = []
    for filt in filters:
        filt_s = [re.escape(comp) for comp in filt.split()]
        tdtd = re.escape('</td><td>')
        pat = re.escape('<tr>')+ '.*' + re.escape('<td>') + '\s*'
        pat += ('\s*' + tdtd + '\s*').join(filt_s)
        pat += '\s*' + tdtd + '.*' + tdtd + '\s*([0-9.]+)\s*'
        pat += re.escape('</td></tr>')
        pat = re.compile(pat)
        matches = [pat.search(line) for line in html_output]
        matches = [float(mat.group(1)) for mat in matches if mat is not None]

        if len(matches) == 0:
            warn('No filter found matching "{}".'.format(filt))
            extinctions = [None]
        else:
            if len(matches) > 1:
                warn('Multiple filters found matching "{}".'.format(filt) +
                     'Averaging {} values.'.format(len(matches)))
            extinctions += [sum(matches) / len(matches)]

    if as_dict:
        return dict(zip(filters, extinctions))
    else:
        return extinctions if list_out else extinctions[0]


if __name__ == '__main__':
    import sys
    try:
        filt = sys.argv[1]
        with open(sys.argv[2]) as f:
            lines = f.readlines()
    except (IOError, IndexError):
        print __doc__
        exit(1)

    for line in lines:
        ra, dec = line.strip().split()
        print request_extinctions(ra, dec, filters=[filt])
