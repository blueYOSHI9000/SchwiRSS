import datetime
import time

def ms_to_struct(ms):
    """Converts Unix time (milliseconds since epoch) to the time.struct_time.

    Args:
        ms (number): milliseconds since epoch,can be in string form since int() is used on it first
    Returns:
        a time.struct_time object with the converted time
    """
    ms = int(ms)
    return time.gmtime(ms/1000.)

def ms_to_datetime(ms):
    """Converts Unix time (milliseconds since epoch) to datetime.datetime.

    Args:
        ms (number): milliseconds since epoch,can be in string form since int() is used on it first
    Returns:
        a datetime.datetime object with the converted time
    """
    ms = int(ms)
    return datetime.datetime.fromtimestamp(time.mktime(time.gmtime(ms/1000.)))

def struct_to_ms(struct):
    """Converts time.struct_time to Unix time (milliseconds since epoch)

    Args:
        struct (time.struct_time object): the time.struct_time object to be converted
    Returns:
        the converted time in milliseconds since epoch
    """
    # copied from several stackoverflow - comments are just what I assume happens

    # convert struct to datetime since apparently you can't convert it directly? or at least no one ever asked on stackoverflow about it
    dt = datetime.datetime.fromtimestamp(time.mktime(struct))
    # get epoch in datetime format
    epoch = datetime.datetime.utcfromtimestamp(0)
    # subtract epoch from our converted datetime so we get the time since epoch, then get seconds and multiply by 1000 to convert to milliseconds
    return (dt - epoch).total_seconds() * 1000.0

def datetime_to_ms(dt):
    """Converts datetime.datetime to Unix time (milliseconds since epoch)

    Args:
        dt (datetime.datetime object): the datetime.datetime object to be converted
    Returns:
        the converted time in milliseconds since epoch
    """
    # get epoch in datetime format
    epoch = datetime.datetime.utcfromtimestamp(0)
    # subtract epoch from our converted datetime so we get the time since epoch, then get seconds and multiply by 1000 to convert to milliseconds
    return (dt - epoch).total_seconds() * 1000.0


def struct_to_datetime(struct):
    """Converts time.struct_time to datetime.datetime

    Args:
        struct (time.struct_time object): the time.struct_time object to be converted
    Returns:
        the datetime.datetime object
    """
    return datetime.datetime.fromtimestamp(time.mktime(struct))


def datetime_to_struct(dt):
    """Converts datetime.datetime to time.struct_time

    Args:
        dt (datetime.datetime object): the datetime.datetime object to be converted
    Returns:
        a time.struct_time object with the converted time
    """
    return dt.timetuple()

def get_current_time():
    """Gets current UTC time as a time.struct_time object

    Returns:
        The current time as a time.struct_time object
    """
    current = datetime.datetime.utcnow()
    return current.timetuple()