import feedparser
import bs4 as bs
import urllib
import re
from math import sqrt


# Returns title and dictionary of word counts for an RSS feed
def get_word_counts(url):
    # Parse the feed
    d = feedparser.parse(url)
    wc = {}

    # Loop over all the entries
    for e in d.entries:
        if 'summary' in e:
            summary = e.summary
        else:
            summary = e.description

        # Extract a list of words
        words = getwords(e.title + ' ' + summary)
        for word in words:
            wc.setdefault(word, 0)
            wc[word] += 1
    return d.feed.title, wc


# Get words from raw feed
def getwords(html):
    # Remove all html tags
    txt = re.compile(r'<[^>]+>').sub('', html)

    # Split words by all non-alpha characters
    words = re.compile(r'[^A-Z^a-z]+').split(txt)

    # Convert to lowercase
    return [word.lower() for word in words if word != '']


# Method for scraping rss links
def scrape_links(url='http://www.uen.org/feeds/lists.shtml'):
    # Init soup object
    soup = bs.BeautifulSoup(urllib.urlopen(url).read(), 'html.parser')
    # Find nested ul-s
    uls = soup.find('div', attrs={'id': 'container'}).find('div', attrs={'id': 'page'}).findAll('ul')
    urls = []
    for u in uls:
        lis = u.findAll('li')
        for l in lis:
            link = l.find('a').get('href').decode("utf-8").encode('ascii', 'ignore')
            urls.append(link)
    return urls


apcount = {}  # Nubmer of appearence of particular words in blogs
wordcounts = {}  # Frequence of the words
links = scrape_links()
for feedulr in links:
    try:
        title, wc = get_word_counts(feedulr)
    except Exception:
        continue
    wordcounts[title] = wc
    for word, count in wc.items():
        apcount.setdefault(word, 0)
        if count > 1:
            apcount[word] += 1

# Reducing words to those that appear neither too frequent neither too few
wordlist = []
feedlen = len(scrape_links())
for w, bc in apcount.items():
    frac = float(bc) / feedlen
    if 0.1 < frac < 0.5:
        wordlist.append(w)


# Write data matrix in file
out = file('blogdata.txt', 'w')
out.write('Blog')
# Print words in first row
for word in wordlist:
    out.write('\t%s' % word)
out.write('\n')


for blog, wc in wordcounts.items():
    # Write blog name in first column
    if blog == '' or blog is None:
        blog = 'Unknown'
    out.write(blog.encode('utf-8').strip())
    # Write wordcount for each blog
    for word in wordlist:
        if word in wc:
            out.write('\t%d' % wc[word])
        else:
            out.write('\t0')
    out.write('\n')





