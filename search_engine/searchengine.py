import re
import urllib2
from pysqlite2 import dbapi2 as sqlite
from urlparse import urljoin

import bs4 as bs

ignorewords = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it'])


class Crawler:
    # Initialize the crawler with the name of database
    def __init__(self, dbname):
        self.conn = sqlite.connect(dbname)

    def __del__(self):
        self.conn.close()

    def dbcommit(self):
        self.conn.commit()

    def get_entry_id(self, table, field, value, createnew=True):
        """
        Auxiliary function for getting an entry ID and adding it
        if it's not present.
        
        :param table: table in database
        :param field: field in table
        :param value: value to check
        :param createnew: (default True) -> create new row if not found
        :return: found row in database or newly created
        """
        cursor = self.conn.execute(
            "SELECT rowid FROM %s WHERE %s = '%s'" % (table, field, value)
        )
        result_set = cursor.fetchone()
        if result_set is None and createnew is True:
            cursor = self.conn.execute(
                "INSERT INTO %s (%s) VALUES ('%s')" % (table, field, value)
            )
            return cursor.lastrowid
        else:
            return result_set[0]

    def add_to_index(self, url, soup):
        """
        Indexing an individual page        
        
        :param url: Web page url
        :param soup: BeautifulSoup object of a web page
        """
        if self.is_indexed(url):
            return
        print 'Indexing:', url

        # Get individual words
        text = self.get_text(soup)
        print 'TEXT\n', text
        words = self.separate_words(text)

        # Get URL id
        urlid = self.get_entry_id('urllist', 'url', url)

        # Link each word to this url
        # todo make it more efficient
        for i in range(len(words)):
            word = words[i]
            if word in ignorewords:
                continue
            wordid = self.get_entry_id('wordlist', 'word', word)
            self.conn.execute(
                'INSERT INTO wordlocation(urlid, wordid, location) VALUES (%d, %d, %d)' % (urlid, wordid, i)
            )

    def get_text(self, soup):
        """
        Extract the text from an HTML page with no tags
        
        :param soup: BeautifulSoup object of a web page.
        :return: Plain text from HTML
        """
        text = soup.string
        if text is None:
            contents = soup.contents
            resulttext = ''
            for cont in contents:
                subtext = self.get_text(cont)
                resulttext += subtext + '\n'
            return resulttext
        else:
            return text.strip()

    def separate_words(self, text):
        """
        Returning list of words by separating non-whitespace character
        
        :param text: plain text from HTML page
        :return: list of words
        """
        splitter = re.compile('\\W*')
        return [s.lower() for s in splitter.split(text) if s != '']

    def is_indexed(self, url):
        """
        Return True if url is alredy indexed
        
        :param url: url name
        :return: Boolean
        """
        u = self.conn.execute(
            "SELECT rowid FROM urllist WHERE url = '%s'" % url
        ).fetchone()
        if u is not None:
            # Check if it has actually been crawled
            v = self.conn.execute(
                'SELECT * FROM wordlocation WHERE urlid = %d' % u[0]
            ).fetchone()
            if v is not None:
                return True
        return False

    def add_link_ref(self, url_from, url_to, link_text):
        """
        Adding link in database(link) between parent and child url
        
        A child url is url found in parent web page.
        :param url_from: parent url
        :param url_to: child url
        :param link_text: link text from html
        """
        words = self.separate_words(link_text)
        fromid = self.get_entry_id('urllist', 'url', url_from)
        toid = self.get_entry_id('urllist', 'url', url_to)
        if fromid == toid:
            return
        cur = self.conn.execute(
            "INSERT INTO link(fromid, toid) VALUES (%d, %d)" % (fromid, toid)
        )
        # Get ID from the previously inserted link
        linkid = cur.lastrowid
        for word in words:
            if word in ignorewords:
                continue
            # Add word from link_text or retrieve existing word ID
            wordid = self.get_entry_id('wordlist', 'word', word)
            # Insert word from link_text and it's link ID to linkwords table
            self.conn.execute(
                "INSERT INTO linkwords(linkid, wordid) VALUES (%d, %d)" % (linkid, wordid)
            )

    def crawl(self, pages, depth=2):
        """
        Starting with a list of pages do a breadth
        first search to the given depth, indexing pages as we go
        
        :param pages: list of pages to start crawling from
        :param depth: maximum depth for crawling pages
        """
        for i in range(depth):
            new_pages = set()
            for page in pages:
                try:
                    c = urllib2.urlopen(page)
                except:
                    print 'Can\'t open %s' % page
                    continue
                soup = bs.BeautifulSoup(c.read(), 'html.parser')
                self.add_to_index(page, soup)

                links = soup('a')
                for link in links:
                    if 'href' in dict(link.attrs):
                        url = urljoin(page, link['href'])
                        if url.find("'") != -1:
                            # example: javascript:printOrder('http://www.serbianrailways.com/active/.../print.html')
                            continue
                        url = url.split('#')[0]  # remove location portion
                        if url[0:4] == 'http' and not self.is_indexed(url):
                            new_pages.add(url)
                        link_text = self.get_text(link)
                        self.add_link_ref(page, url, link_text)
                self.dbcommit()
            pages = new_pages

    def create_index_tables(self):
        """
        Toxic method to create db schema and database tables 
        """
        self.conn.execute('CREATE TABLE urllist(url)')
        self.conn.execute('CREATE TABLE wordlist(word)')
        self.conn.execute('CREATE TABLE wordlocation(urlid, wordid, location)')
        self.conn.execute('CREATE TABLE link(fromid INTEGER, toid INTEGER )')
        self.conn.execute('CREATE TABLE linkwords(wordid, linkid)')
        self.conn.execute('CREATE INDEX wordidx ON wordlist(word)')
        self.conn.execute('CREATE INDEX urlidx ON urllist(url)')
        self.conn.execute('CREATE INDEX wordurlidx ON wordlocation(wordid)')
        self.conn.execute('CREATE INDEX urltoidx ON link(toid)')
        self.conn.execute('CREATE INDEX urlfromidx ON link(fromid)')
        self.dbcommit()

    def calculate_pagerank(self, iterations=20):
        """
        Creates pagerank table in database and calculates 
        PageRank scores for all indexed urls.
        
        :param iterations: Number of iterations for calculating precise PR score
        """
        # Clear out current PageRank tables
        self.conn.execute('DROP TABLE IF EXISTS pagerank')
        self.conn.execute('CREATE TABLE pagerank(urlid PRIMARY KEY, score)')

        # Init every url with a PageRank of 1
        self.conn.execute('INSERT INTO pagerank SELECT rowid, 1.0 FROM urllist')
        self.dbcommit()

        for i in range(iterations):
            print 'PageRank Iteration: %d' % i
            url_list = self.conn.execute('SELECT rowid FROM urllist')  # query urlid from urllist
            for (urlid,) in url_list:
                pr = 0.15

                # Loop through al the parent pages that link to this one
                parent_list = self.conn.execute(
                    'SELECT DISTINCT fromid FROM link WHERE toid=%d' % urlid
                )
                for (parent_id,) in parent_list:
                    # Get the PageRank of the parent
                    cursor = self.conn.execute(
                        'SELECT score FROM pagerank WHERE urlid=%d' % parent_id
                    )
                    parent_pagerank = cursor.fetchone()[0]

                    # Get the total number of links to other pages from the parent page
                    temp = self.conn.execute(
                        'SELECT COUNT(*) FROM link WHERE fromid=%d' % parent_id
                    )
                    parent_link_count = temp.fetchone()[0]
                    pr += 0.85 * (parent_pagerank / parent_link_count)
                self.conn.execute(
                    'UPDATE pagerank SET score=%f WHERE urlid=%d' % (pr, urlid)
                )
            self.dbcommit()


class Searcher:
    def __init__(self, dbname):
        self.conn = sqlite.connect(dbname)

    def __del__(self):
        self.conn.close()

    def get_match_rows(self, query):
        """
        Based on the query returns list of tuples 
        
        This means the method will return all locations of words from query in one url,
        and all url's that contain every word from the query. Basically each urlid appears multiple times, 
        once for every combination of locations.
        
        rows e.g.[(urlID, word_locations...), ...]
        wordids e.g [wordid, ...]
        
        :param query: string containing sentence for searching
        :returns: rows -> list of tuples, wordids -> list of word id's
        """
        # Strings to build the query
        field_list = 'w0.urlid'  # URL ID from first word from query
        table_list = ''
        clause_list = ''
        wordids = []

        # Split the words by spaces
        words = query.split(' ')
        table_number = 0

        for word in words:
            # Get word ID, returns a tuple
            wordrow = self.conn.execute(
                "SELECT rowid FROM wordlist WHERE word = '%s'" % word
            ).fetchone()
            if wordrow is not None:
                wordid = wordrow[0]  # Extract word ID from tuple
                wordids.append(wordid)
                # We need to concat query if there are more tables
                if table_number > 0:
                    table_list += ','
                    clause_list += ' and '
                    clause_list += 'w%d.urlid=w%d.urlid and ' % (table_number - 1, table_number)
                field_list += ',w%d.location' % table_number  # From table wordlocation
                table_list += 'wordlocation w%d' % table_number
                # Extract wordid for every word in wordlocation table
                clause_list += 'w%d.wordid=%d' % (table_number, wordid)
                table_number += 1
        # Create the query from the separate parts
        # All url's(urlid) contain every word in the query
        full_query = 'SELECT %s FROM %s WHERE %s' % (field_list, table_list, clause_list)
        # By the book
        # print full_query
        # cur = self.conn.execute(full_query)
        # rows = [row for row in cur]
        rows = self.conn.execute(full_query).fetchall()
        return rows, wordids

    def get_scored_list(self, rows, word_ids):
        """
        Scoring result (rows) with various algorithms.
        
        :param rows: list of tuples e.g. (urlid, w0.location, w1.location...)
        :param word_ids: list of word id's from query
        :return: dict e.g.{urlid: rank}
        """
        total_scores = dict([(row[0], 0) for row in rows])

        # Scoring functions
        weights = [
            (1.0, self.word_frequency_score(rows)),
            (1.0, self.location_score(rows)),
            (1.0, self.distance_score(rows)),
            (0.5, self.inbound_link_score(rows)),
            (1.0, self.pagerank_score(rows)),
            (1.0, self.link_text_score(rows, word_ids)),
        ]

        for (weight, scores) in weights:
            for url in total_scores:
                total_scores[url] += weight * scores[url]

        return total_scores

    def get_url_name(self, id):
        """
        Method returns url name based on urlid.
        
        :param id: ID of url
        :return: url name
        """
        cursor = self.conn.execute(
            "SELECT url FROM urllist WHERE rowid=%d" % id
        )
        return cursor.fetchone()[0]

    def query(self, q):
        """
        Method for querying indexed web pages and printing
        best matched url's.
        
        :param q: query string for search
        """
        rows, word_ids = self.get_match_rows(q)  # Get list of tuples (urlid, wordlocations...)
        scores = self.get_scored_list(rows, word_ids)
        # Sort urls for query
        ranked_scores = sorted([(score, url) for (url, score) in scores.items()], reverse=True)  # reverse = 1 btb
        # Print 10 most ranked results
        for (score, urlid) in ranked_scores[0:10]:
            print '%f\t%s' % (score, self.get_url_name(urlid))

    def normalize(self, scores, small_is_better=False):
        """
        Method takes a dictionary od IDs and scores and
        return a new dictionary with same IDs but with scores between 0 and 1
        
        :param scores: dict of ids and scores
        :param small_is_better: best type of value for scoring algorithm
        :return: dict of normalized scores
        """
        vsmall = 0.00001  # Avoid dividing by zero
        if small_is_better:
            minscore = min(scores.values())
            return dict([(u, float(minscore) / max(vsmall, l)) for (u, l) in scores.items()])
        else:
            maxscore = max(scores.values())
            if maxscore == 0:
                maxscore = vsmall
            return dict([(u, float(c) / maxscore) for (u, c) in scores.items()])

    def word_frequency_score(self, rows):
        """
        Returns score based on frequency of words in document.
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :return: dict of scores
        """
        # Create dict {urlid: init_score}
        counts = dict([(row[0], 0) for row in rows])
        # Increment score for every occurrence of urlid in row tuple
        for row in rows:
            counts[row[0]] += 1
        return self.normalize(counts)

    def location_score(self, rows):
        """
        Returns score based on how early words from query occurred
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :return: dict of scores
        """
        # Create dict {urlid: init_score}
        locations = dict([(row[0], 1000000) for row in rows])
        for row in rows:
            # Sum all word locations from row tuple
            loc = sum(row[1:])
            if loc < locations[row[0]]:
                locations[row[0]] = loc
        return self.normalize(locations, small_is_better=True)

    def distance_score(self, rows):
        """
        Returns score based on how close words in query appear
        to one another in document. Smallest distances are used
        for calculation.
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :return: dict of scores
        """
        # If there's only one word everyone wins!
        if len(rows[0]) <= 2:
            return dict([(row[0], 1.0) for row in rows])

        # Initialize dictionary with large values
        min_distance = dict([(row[0], 1000000) for row in rows])

        for row in rows:
            # Calculating sum of distances between word locations in row tuple.
            dist = sum([abs(row[i] - row[i - 1]) for i in range(2, len(row))])
            if dist < min_distance[row[0]]:
                min_distance[row[0]] = dist
        return self.normalize(min_distance, small_is_better=True)

    def inbound_link_score(self, rows):
        """
        Returns score based on how many times page appears in other
        web pages.
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :return: dict of scores
        """
        # Create unique set of url's (urlid)
        unique_urls = set([row[0] for row in rows])
        # Create dict that counts occurrences of page in
        # parent web pages with dict comprehension
        inbound_count = dict(
            [
                (
                    u, self.conn.execute(
                        'SELECT COUNT(*) FROM link WHERE toid=%d' % u
                    ).fetchone()[0]
                ) for u in unique_urls
            ]
        )
        return self.normalize(inbound_count)

    def pagerank_score(self, rows):
        """
        Returns score based on calculated PageRank algorithm.
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :return: dict of scores
        """
        pageranks = dict(
            [
                (
                    row[0], self.conn.execute(
                        'SELECT score FROM pagerank WHERE urlid=%d' % row[0]
                    ).fetchone()[0]
                ) for row in rows
            ]
        )
        # btb
        # max_rank = max(pageranks.values())
        # normalizedscores = dict([(u, float(l) / max_rank) for (u, l) in pageranks.items()])
        # return normalizedscores
        return self.normalize(pageranks)

    def link_text_score(self, rows, wordids):
        """
        Returns score based on a matching word id's with words
        in a link text. Score for page rises if parent page link text
        have query word occurrences
        
        :param rows: list of tuples [(urlid, w0.location, ...), ...]
        :param wordids: word id's from query
        :return: dict of scores
        """
        # Initialize dict {urlid: score}
        link_scores = dict([(row[0], 0) for row in rows])
        for wordid in wordids:
            # Get all results from link table which contains specific word(link_text) in linkwords table
            cursor = self.conn.execute(
                'SELECT link.fromid, link.toid FROM linkwords, link '
                'WHERE wordid = %d AND linkwords.linkid = link.rowid' % wordid
            )
            for (fromid, toid) in cursor:
                # Check if child page is in dict
                if toid in link_scores:
                    # Get parents pagerank score
                    pr = self.conn.execute(
                        'SELECT score FROM pagerank WHERE urlid = %d' % fromid
                    ).fetchone()[0]
                    # Add parent's pagerank score to child score
                    link_scores[toid] += pr
        return self.normalize(link_scores)

if __name__ == '__main__':
    crawler = Crawler('searchindex.db')
    e = Searcher('searchindex.db')
    # crawler.create_index_tables()
    # pages = ['https://en.wikipedia.org/wiki/Serbia']
    # crawler.crawl(pages)
    # print [row for row in crawler.conn.execute('select rowid from wordlocation where wordid=1')]

    # print e.get_match_rows('south slavic russia')
    print 'Top 10 results for: ', 'serbian city'
    e.query('serbian city')

    # crawler.calculate_pagerank()
    # cur = crawler.conn.execute('SELECT * FROM pagerank ORDER BY score DESC ')
    # # for i in range(3):
    # #     print cur.next()
    # print len(cur.fetchall())
    # print len(crawler.conn.execute('SELECT * FROM wordlocation').fetchall())
