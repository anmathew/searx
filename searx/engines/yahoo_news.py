# SPDX-License-Identifier: AGPL-3.0-or-later
"""
 Yahoo (News)
"""

import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from lxml import html
from searx.engines.yahoo import parse_url, language_aliases
from searx.engines.yahoo import _fetch_supported_languages, supported_languages_url  # NOQA # pylint: disable=unused-import
from dateutil import parser
from searx.utils import extract_text, extract_url, match_language

# about
about = {
    "website": 'https://news.yahoo.com',
    "wikidata_id": 'Q3044717',
    "official_api_documentation": 'https://developer.yahoo.com/api/',
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

# engine dependent config
categories = ['news']
paging = True

# search-url
search_url = 'https://news.search.yahoo.com/search?{query}&b={offset}&{lang}=uh3_news_web_gs_1&pz=10&xargs=0&vl=lang_{lang}'  # noqa

# specific xpath variables
results_xpath = '//ol[contains(@class,"searchCenterMiddle")]//li'
url_xpath = './/h3/a/@href'
title_xpath = './/h3/a'
content_xpath = './/div[@class="compText"]'
publishedDate_xpath = './/span[contains(@class,"tri")]'
suggestion_xpath = '//div[contains(@class,"VerALSOTRY")]//a'


# do search-request
def request(query, params):
    offset = (params['pageno'] - 1) * 10 + 1

    if params['language'] == 'all':
        language = 'en'
    else:
        language = match_language(params['language'], supported_languages, language_aliases).split('-')[0]

    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'p': query}),
                                      lang=language)

    # TODO required?
    params['cookies']['sB'] = '"v=1&vm=p&fl=1&vl=lang_{lang}&sh=1&pn=10&rw=new'\
        .format(lang=language)
    return params


def sanitize_url(url):
    if ".yahoo.com/" in url:
        return re.sub("\\;\\_ylt\\=.+$", "", url)
    else:
        return url


# get response from search-request
def response(resp):
    results = []

    dom = html.fromstring(resp.text)

    # parse results
    for result in dom.xpath(results_xpath):
        urls = result.xpath(url_xpath)
        if len(urls) != 1:
            continue
        url = sanitize_url(parse_url(extract_url(urls, search_url)))
        title = extract_text(result.xpath(title_xpath)[0])
        content = extract_text(result.xpath(content_xpath)[0])

        # parse publishedDate
        publishedDate = extract_text(result.xpath(publishedDate_xpath)[0])

        # still useful ?
        if re.match("^[0-9]+ minute(s|) ago$", publishedDate):
            publishedDate = datetime.now() - timedelta(minutes=int(re.match(r'\d+', publishedDate).group()))
        elif re.match("^[0-9]+ days? ago$", publishedDate):
            publishedDate = datetime.now() - timedelta(days=int(re.match(r'\d+', publishedDate).group()))
        elif re.match("^[0-9]+ hour(s|), [0-9]+ minute(s|) ago$", publishedDate):
            timeNumbers = re.findall(r'\d+', publishedDate)
            publishedDate = datetime.now()\
                - timedelta(hours=int(timeNumbers[0]))\
                - timedelta(minutes=int(timeNumbers[1]))
        else:
            try:
                publishedDate = parser.parse(publishedDate)
            except:
                publishedDate = datetime.now()

        if publishedDate.year == 1900:
            publishedDate = publishedDate.replace(year=datetime.now().year)

        # append result
        results.append({'url': url,
                        'title': title,
                        'content': content,
                        'publishedDate': publishedDate})

    # return results
    return results
