#!/usr/bin/env python

'''Check that index.html is valid and print out warnings and errors
when the header is malformed.

Checks for:
1.  There should be the right number of categories
2.  Categories are allowed to appear only once
3.  Contact email should be valid (letters + @ + letters + . + letters)
4.  Latitute/longitude should be 2 floating point numbers separated by comma
5.  startdate should be a valid date; if enddate is present, it should be valid as well
6.  country should be a string with no spaces
7.  instructor and helper lists should be valid Python/Ruby lists
8.  Template header should not exist
9.  humandate should have three-letter month and four-letter year
10. layout should be 'workshop'
11. root must be '.'
12. humantime should have 'am' or 'pm' or both
13. address, venue should be non-empty
'''

import sys
import os
import re

import yaml
from collections import Counter

__version__ = '0.6'

EMAIL_PATTERN = r'[^@]+@[^@]+\.[^@]+'
HUMANTIME_PATTERN = r'((0?\d|1[0-1]):[0-5]\d(am|pm)(-|to)(0?\d|1[0-1]):[0-5]\d(am|pm))|((0?\d|1\d|2[0-3]):[0-5]\d(-|to)(0?\d|1\d|2[0-3]):[0-5]\d)'
EVENTBRITE_PATTERN = r'\d{9,10}'
URL_PATTERN = r'https?://.+'

DEFAULT_CONTACT_EMAIL = 'admin@software-carpentry.org'

USAGE = 'Usage: swc_index_validator.py [filename]'

ERROR = 'ERROR:\t{0}\n'
SUB_ERROR = '\t{0}\n'

def look_for_fixme(func):
    '''Decorator to see whether a value starts with FIXME.'''
    def inner(arg):
        if (arg is not None) and isinstance(arg,str) and arg.lstrip().startswith('FIXME'):
            return False
        return func(arg)
    return inner

@look_for_fixme
def check_layout(layout):
    '''Checks whether layout equals "workshop".'''
    return layout == 'workshop'

@look_for_fixme
def check_root(root):
    '''Checks root - can only be "."'''
    return root == '.'

@look_for_fixme
def check_country(country):
    '''A valid country has no spaces, is one string, isn't empty'''
    return (country is not None) and (' ' not in country)

@look_for_fixme
def check_humandate(date):
    '''A valid human date starts with a three-letter month and ends with four-letter year,
    Example: "Feb 18-20, 2525"
    other example: "Feb 18 and 20, 2014"
    '''
    if "," not in date:
        return False

    month_dates, year = date.split(",")

    # The first three characters of month_dates are not empty
    month = month_dates[:3]
    if any(char == " " for char in month):
        return False

    # But the fourth character is empty ("February" is illegal)
    if month_dates[3] != " ":
        return False

    # year contains *only* numbers
    try:
        int(year)
    except:
        return False

    return True

@look_for_fixme
def check_humantime(time):
    '''A valid humantime contains at least one number'''
    return bool(re.match(HUMANTIME_PATTERN, time.replace(" ","")))

def check_date(this_date):
    '''A valid date is YEAR-MONTH-DAY, example: 2014-06-30'''
    from datetime import date
    # yaml automatically loads valid dates as datetime.date
    return isinstance(this_date, date)

@look_for_fixme
def check_latitude_longitude(latlng):
    '''A valid latitude/longitude listing is two floats, separated by comma'''
    try:
        # just one of them has to break
        lat, lng = latlng.split(',')
        float(lat)
        float(lng)
    except ValueError:
        return False
    return True

def check_instructors(instructors):
    '''Checks whether instructor list is of format ['First name', 'Second name', ...']'''
    # yaml automatically loads list-like strings as lists
    return isinstance(instructors, list) and len(instructors) > 0

def check_helpers(helpers):
    '''Checks whether helpers list is of format ['First name', 'Second name', ...']'''
    # yaml automatically loads list-like strings as lists
    return isinstance(helpers, list) and len(helpers) >= 0

@look_for_fixme
def check_email(email):
    '''A valid email has letters, then an @, followed by letters, followed by a dot, followed by letters.'''
    return bool(re.match(EMAIL_PATTERN, email)) and email != DEFAULT_CONTACT_EMAIL

@look_for_fixme
def check_eventbrite(eventbrite):
    '''A valid EventBrite key is 9 or more digits.'''
    if not isinstance(eventbrite,str):
        eventbrite=str(eventbrite)
    return bool(re.match(EVENTBRITE_PATTERN, eventbrite))

@look_for_fixme
def check_etherpad(etherpad):
    '''A valid Etherpad URL is just a URL.'''
    return bool(re.match(URL_PATTERN, etherpad))

@look_for_fixme
def check_pass(value):
    '''A test that always passes, used for things like addresses.'''
    return True

HANDLERS = {
    'layout' :       (True,  check_layout, 'layout isn\'t "workshop".'),
    'root' :         (True,  check_root, 'root can only be ".".'), 
    'country' :      (True,  check_country, 'country invalid. Please check whether there are spaces inside the country-name.'),
    'humandate' :    (True,  check_humandate, 'humandate invalid. Please use three-letter months like "Jan" and four-letter years like "2025".'),
    'humantime' :    (True,  check_humantime, 'humantime doesn\'t include numbers.'),
    'startdate' :    (True,  check_date, 'startdate invalid. Must be of format year-month-day, i.e., 2014-01-31.'),
    'enddate' :      (False, check_date, 'enddate invalid. Must be of format year-month-day, i.e., 2014-01-31.'),
    'latlng' :       (True,  check_latitude_longitude, 'latlng invalid. Check that it is two floating point numbers, separated by a comma.'),
    'instructor' :   (True,  check_instructors, 'instructor list isn\'t a valid list of format ["First instructor", "Second instructor",..].'),
    'helper' :       (True,  check_helpers, 'helper list isn\'t a valid list of format ["First helper", "Second helper",..].'),
    'contact' :      (True,  check_email, 'contact email invalid or still set to "{0}".'.format(DEFAULT_CONTACT_EMAIL)),
    'eventbrite' :   (False, check_eventbrite, 'Eventbrite key appears invalid.'),
    'etherpad' :     (False, check_etherpad, 'Etherpad URL appears invalid.'),
    'venue' :        (False, check_pass, 'venue name not specified'),
    'address' :      (False, check_pass, 'address not specified')
}

# REQUIRED is all required categories.
REQUIRED = set([k for k in HANDLERS if HANDLERS[k][0]])

# OPTIONAL is all optional categories.
OPTIONAL = set([k for k in HANDLERS if not HANDLERS[k][0]])

def check_validity(data, function, error):
    '''Wrapper-function around the various check-functions.'''
    valid = function(data)
    if not valid:
        sys.stderr.write(ERROR.format(error))
        sys.stderr.write(SUB_ERROR.format('Offending entry is: "{0}"'.format(data)))
    return valid

def check_categories(left, right, message):
    result = left - right
    if result:
        sys.stderr.write(ERROR.format(message))
        sys.stderr.write(SUB_ERROR.format('Offending entries: {0}'.format(result)))
        return False
    return True

def check_double_categories(seen_categories, message):
    category_counts = Counter(seen_categories)
    double_categories = [category for category in category_counts if category_counts[category] > 1]
    if double_categories:
        sys.stderr.write(ERROR.format(message))
        sys.stderr.write(SUB_ERROR.format('"{0}" appears more than once.\n'.format(double_categories)))
        return False
    return True

def get_header(index_fh):
    '''Parses index.html file, returns just the header'''
    # We stop the header once we see the second '---'
    header_counter = 0
    header = []
    this_categories = []
    for line in index_fh:
        line = line.rstrip()
        if line == '---':
            header_counter += 1
            continue
        if header_counter != 2:
            # Work around PyYAML Ticket #114
            if not line.startswith('#'):
                header.append(line)
                this_categories.append(line.split(":")[0].strip())

        if "This page is a template for workshop home pages." in line:
            sys.stderr.write('WARN:\tYou seem to still have the template header in your index.html. Please remove that.\n')
            sys.stderr.write('\tLook for: "<!-- Remove the block below. -->" in the index.html.\n')
            break # we can stop here - for now, just check header and template header

    return yaml.load("\n".join(header)), this_categories

def check_file(index_fh):
    '''Gets header from index.html, calls all other functions and checks file for validity.
    Returns True when 'index.html' has no problems and False when there are problems.
    '''
    header_data, seen_categories = get_header(index_fh)

    if not header_data:
        msg = 'Cannot find header in given file "{0}". Please check path, is this the bc index.html?\n'.format(filename)
        sys.stderr.write(ERROR.format(msg))
        sys.exit(1)

    is_valid = True

    # Look through all header entries.  If the category is in the input
    # file and is either required or we have actual data (as opposed to
    # a commented-out entry), we check it.  If it *isn't* in the header
    # but is required, report an error.
    for category in HANDLERS:
        required, handler_function, error_message = HANDLERS[category]
        if category in header_data:
            if required or header_data[category]:
                is_valid &= check_validity(header_data[category], handler_function, error_message)
        elif required:
            sys.stderr.write(ERROR.format('index file is missing mandatory key "{0}".'.format(category)))
            is_valid &= False

    # Do we have double categories?
    is_valid &= check_double_categories(seen_categories, 'There are categories appearing twice or more.')

    # Check whether we have missing or too many categories
    seen_categories = set(seen_categories)
    is_valid &= check_categories(REQUIRED, seen_categories, 'There are missing categories.')
    is_valid &= check_categories(seen_categories, REQUIRED.union(OPTIONAL), 'There are superfluous categories.')

    return is_valid

if __name__ == '__main__':
    filename = None
    if len(sys.argv) == 1:
        if os.path.exists('./index.html'):
            filename = './index.html'
        elif os.path.exists('../index.html'):
            filename = '../index.html'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    if filename is None:
        sys.stderr.write('Usage: "python check" or "python check path/to/index.html"\n')
        sys.exit(1)

    sys.stderr.write('Testing "{0}".\n'.format(filename))

    with open(filename) as index_fh:
        is_valid = check_file(index_fh)

    if is_valid:
        sys.stderr.write('Everything seems to be in order.\n')
        sys.exit(0)
    else:
        sys.stderr.write('There were problems, please see above.\n')
        sys.exit(1)
