from bs4 import BeautifulSoup

Item = lambda x: {
    'Name': x['itemName'],
    'Icon': 'https://www.bungie.net' + x['icon'],
    'Description': BeautifulSoup(x['itemDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['itemDescription'] else None,
    # in order from left to right: Removes html tags, removes newlines (breaks the table), fixes charset for reddit, makes sure there's actually something for the above to happen on
} 

Activity = lambda x: {
    'Name': x['activityName'],
    'Icon': 'https://www.bungie.net' + x['icon'],
    'Description': BeautifulSoup(x['activityDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['activityDescription'] else None,
}

Vendor = lambda x: {
    'Name': x['summary']['vendorName'],
    'Icon': x['summary']['vendorIcon'],
    'Description': BeautifulSoup(x['summary']['vendorDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['summary']['vendorDescription'] else None,
}

Grimorire_Theme = lambda x: {
    'Name': x['Key'], # lol why tho
    'Icon': 'https://www.bungie.net' + x['Value']['highResolution']['image']['sheetPath'],
    'Description': BeautifulSoup(x['Value']['themeDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['Value']['themeDescription'] else None,
}

Grimoire_Page = lambda x: {
    'Name': x['page']['pageName'],
    'Icon': 'https://www.bungie.net' + x['page']['highResolution']['image']['sheetPath'],
    'Description': BeautifulSoup(x['page']['pageDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['page']['pageDescription'] else None,
}

Grimoire_Card = lambda x: {
    'Name': x['card']['cardName'], #oh that actually makes sense
    'Icon': 'https://www.bungie.net' + x['card']['highResolution']['image']['sheetPath'],
    'Description': BeautifulSoup(x['card']['cardDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['card']['cardDescription'] else None,
}

Destination = lambda x: {
    'Name': x['destinationName'],
    'Icon': 'https://www.bungie.net' + x['icon'],
    'Description': BeautifulSoup(x['destinationDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['destinationDescription'] else None,
}

Place = lambda x: {} #I can't figure out what a Place is and how it's different from a destination

Perk = lambda x: {
    'Name': x['displayName'],
    'Icon': 'https://www.bungie.net' + x['displayIcon'],
    'Description': BeautifulSoup(x['displayDescription'], 'html.parser').text.replace("\n", "").encode("ascii", "xmlcharrefreplace") if x['displayDescription'] else None,
}

_DataPull = {
    0: Item,
    1: Activity,
    2: Vendor,
    3: Grimorire_Theme,
    4: Grimoire_Page,
    5: Grimoire_Card,
    6: Destination,
    #7: Place,
    8: Perk,
}

#Don't worry about anything above this, just call this with the raw json from the response.
Datapull = lambda x: _DataPull[x['type']](x['object']) if x['relevance'] > 300 and x['type'] in _DataPull else x['relevance']