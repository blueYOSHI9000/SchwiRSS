import discord

import feedparser
import json
import time

import modules.convert_time as ct
from modules.log import log
import modules.misc as misc

def scan_feed(url):
    """Simply scans a feed and returns it. Does NOT check whether

    Args:
        url (string): the url to scan
    Returns:
        The feedparser object incl. all feed items.
    """
    return feedparser.parse(url)

def get_new_items_from_feed(*, feed=False, url=False, last_checked):
    """Scans a feed for new items and returns a list of them.

    Args:
        feed: an already scanned feed
        url (string): url to scan in case a feed isn't given directly
        last_checked (time.struct_time object): last time it got checked for new items
    Returns:
        list of all new items
    """
    # if
    if feed == False:
        feed = scan_feed(url)

    # check if the feed exists - otherwise return False to indicate that the page likely doesn't exist (anymore)
    try:
        feed.entries[0]
    except (NameError, AttributeError, IndexError):
        return False

    final = []
    # dont stop scanning after the items are older since some new items might've been lower in the list (like for Manga, some special in-between chapters might've been released later on and as such are lower in the list where they technically belong despite being new)
    for i in feed.entries:
        if i.published_parsed > ct.ms_to_struct(last_checked):
            final.append(i)

    # TODO: add the last 10 titles or something to the database as a double check

    return final

def get_embed_from_item(*, item, db_item, feed, channel_item, client):
    """Creates an embed from an rss feed.

    Args:
        item: the rss feed item that should be used
        db_item: the corresponding feed in the database (used in case name & url can't be parsed)
        feed: the full rss feed, not just the item (used for thumbnail)
        channel_item: the 'channels' item from the database, used to get 'guildID'
    Returns:
        discord.Embed object
    """
    embed = {}
    date_format = json.load(open('settings/config.json', 'r'))['rss']['dateFormat']

    if hasattr(item, 'title'):
        embed['title'] = item.title
    else:
        embed['title'] = db_item['name']

    if hasattr(item, 'summary'):
        # cut if summary is above 350 characters
        embed['description'] = item.summary[:350]
    else:
        embed['description'] = '[no description found]'

    if hasattr(item, 'link'):
        embed['url'] = item.link
    else:
        embed['url'] = db_item['url']

    embed['color'] = misc.get_embed_color(default_color=client.get_guild(channel_item['guildID']).me.color)


    embed = discord.Embed(**embed)

    if hasattr(item, 'published_parsed'):
        embed.set_footer(text=time.strftime(date_format, item.published_parsed))
    else:
        embed.set_footer(text='[could not parse time published]')

    image_found = False

    try:
        for i in item.media_content:
            if i['medium'] == 'image':
                embed.set_image(url = i['url'])
                image_found = True
    except (NameError, AttributeError, IndexError):
        pass

    # if no image was found, set the thumbnail as image instead
    try:
        if image_found == True:
            embed.set_thumbnail(url = feed.feed.image.href)
        else:
            embed.set_image(url = feed.feed.image.href)
    except (NameError, AttributeError, IndexError):
        pass

    return embed

def already_checked(last_checked, interval, current_time=ct.get_current_time()):
    """Checks if feed has already scanned in the last interval.

    Args:
        last_checked (number): the time it has last been checked in ms since epoch
        interval (number): the interval in seconds
        current_time (time.time_struct object): overwrite the current time
    """
    # multiply interval by 1000 to convert from seconds to ms
    # subtract 5s from interval to make sure that a scheduled scan doesn't hit it
    last_checked = last_checked + (interval * 1000 - 5000)
    last_checked = ct.ms_to_struct(last_checked)

    return last_checked > current_time

async def scan_all_feeds(*, client):
    """Scans all RSS feeds

    Args:
        client: the discord.py client object required for logging and posting new items
    """

    with open('settings/database.json', 'r+') as f:
        database = json.load(f)
        feeds = database['feeds']
        config = json.load(open('settings/config.json', 'r'))

        combine_posts = config['rss']['combinePosts']
        oldest_posts_first = config['rss']['oldestFirst']
        interval = config['rss']['interval'] * 60

        if interval < 600:
            interval = 600

        # convert both to seconds
        scan_delay = config['rss']['scanDelay'] / 1000
        post_delay = config['rss']['postDelay'] / 1000

        if scan_delay < 0:
            scan_delay = 0

        if post_delay < 0:
            post_delay = 0


        current_time = ct.get_current_time()

        last_checked = database['general']['lastChecked']

        # check if already scanned during the last interval
        if already_checked(last_checked, interval, current_time):
            await log(f" Skip scanning all feeds ({int(interval / 60)}min interval)..", 'info', client=client)
            return

        await log('Start scanning all feeds.', 'info', client=client)

        # go through all feeds that have to be scanned
        # use range() because the original feeds variable has to be edited
        for i in range(len(feeds)):
            time.sleep(scan_delay)

            last_checked = feeds[i]['lastChecked']

            # check if already scanned during the last interval
            if already_checked(last_checked, interval, current_time):
                await log(f" Skip scanning {feeds[i]['name']} ({int(interval / 60)}min interval).", 'spamInfo', client=client)
                continue

            await log(f"Start scanning {feeds[i]['name']}.", 'spamInfo', client=client)

            try:
                feed = scan_feed(feeds[i]['url'])
                results = get_new_items_from_feed(feed=feed, url=feeds[i]['url'], last_checked=feeds[i]['lastChecked'])
            except:
                await log(f"Failed to scan {feeds[i]['url']}.", 'warn', client=client)
                continue;

            # if feed is unavailable, mark it as such with the current time
            if results == False:
                await log(f"{feeds[i]['name']} is not available (url: '{feeds[i]['url']}'.", 'spamInfo', client=client)
                # only mark it with the current time if it wasn't already marked as unavailable before
                if feeds[i]['unavailable'] == False:
                    feeds[i]['unavailable'] = ct.struct_to_ms(current_time)

                    for c in feeds[i]['channels']:
                        time.sleep(post_delay)

                        channel = client.get_channel(c['channelID'])
                        try:
                            await channel.send(f"**{c['feedName']}** is not available (this message won't be posted again until it's available again). Feed URL: {feeds[i]['url']}")
                        except:
                            await log(f"Could not send {feeds[i]['name']} as the channel is likely deleted.", 'warn', client=client)

                continue

            # mark feeds as available
            feeds[i]['unavailable'] = False

            # check if posts should be combined
            if len(results) > combine_posts and combine_posts != 0:
                if oldest_posts_first == True:
                    first_item = results[len(results) - 1]
                else:
                    first_item = results[0]

                for c in feeds[i]['channels']:
                    time.sleep(post_delay)

                    embed = get_embed_from_item(item=first_item, db_item=feeds[i], feed=feed, channel_item=c, client=client)

                    channel = client.get_channel(c['channelID'])
                    try:
                        await channel.send(embed=embed)
                        await channel.send(f"...and {len(results) - combine_posts} more from {c['feedName']}.")
                    except:
                        await log(f"Could not send {feeds[i]['name']} as the channel is likely deleted.", 'warn', client=client)

            # post all items
            else:

                # reverse the results list so the oldest items come first
                if oldest_posts_first == True:
                    results = results[::-1]

                for c in feeds[i]['channels']:
                    time.sleep(post_delay)

                    channel = client.get_channel(c['channelID'])
                    for r in results:
                        embed = get_embed_from_item(item=r, db_item=feeds[i], feed=feed, channel_item=c, client=client)
                        try:
                            await channel.send(embed=embed)
                        except:
                            await log(f"Could not send {feeds[i]['name']} as the channel is likely deleted.", 'warn', client=client)

            feeds[i]['lastChecked'] = ct.struct_to_ms(ct.get_current_time())
            await log(f" Done scanning {feeds[i]['name']}.", 'spamInfo', client=client)

        database['feeds'] = feeds
        database['general']['lastChecked'] = ct.struct_to_ms(ct.get_current_time())
        # reset file position to the beginning - stackoverflow copy, dont ask
        f.seek(0)
        json.dump(database, f, indent=4)
        f.truncate()
        await log('All feeds scanned.', 'info', client=client)
        return