from math import tanh
from pysqlite2 import dbapi2 as sqlite


class SearchNet:
    def __init__(self, dbname):
        self.conn = sqlite.connect(dbname)

    def __del__(self):
        self.conn.close()

    def make_tables(self):
        # Table used for checking existing word query combinations
        self.conn.execute('CREATE TABLE hiddennode(create_key)')
        # Input to hidden weights
        self.conn.execute('CREATE TABLE wordhidden(fromid, toid, strength)')
        # Hidden to output weights
        self.conn.execute('CREATE TABLE hiddenurl(fromid, toid, strength)')
        self.conn.commit()

    def get_strength(self, fromid, toid, layer):
        """
        Returns weight between two nodes.
        
        :param fromid: Relative input node id
        :param toid: Relative output node id
        :param layer: Layer in feedforward net
        """
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'
        # Get weight from proper table
        cursor = self.conn.execute(
            'SELECT strength FROM %s WHERE fromid = %d AND toid = %d' % (table, fromid, toid)
        )
        result = cursor.fetchone()
        if result is None:
            if layer == 0:
                # Word to hidden default negative for additional new words - layer 0
                return - 0.2
            if layer == 1:
                return 0
        return result[0]

    def set_strength(self, fromid, toid, layer, strength):
        """
        Check if connection already exists and update or create
        connection with a new strength.
        
        :param fromid: Relative input node id 
        :param toid: Relative output node id
        :param layer: Layer in feedforward net
        :param strength: Weight in connection
        """
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'
        cursor = self.conn.execute(
            'SELECT rowid FROM %s WHERE fromid = %d AND toid = %d' % (table, fromid, toid)
        )
        result = cursor.fetchone()
        if result is None:
            self.conn.execute(
                'INSERT INTO %s (fromid, toid, strength) VALUES (%d, %d, %f)' % (table, fromid, toid, strength)
            )
        else:
            rowid = result[0]
            self.conn.execute(
                'UPDATE %s SET strength = %f WHERE rowid = %d' % (table, strength, rowid)
            )

    def generate_hidden_node(self, wordids, urls):
        """
        Creates new node in the hidden layer every time it gets
        new combination of words.
        
        :param wordids: word id's from query
        :param urls: 
        """
        if len(wordids) > 3:
            return None # todo wtf
        # Check if we alredy created a node for this set of words
        create_key = '_'.join(sorted([str(wi) for wi in wordids]))
        cursor = self.conn.execute(
            "SELECT rowid FROM hiddennode WHERE create_key = '%s'" % create_key
        )
        result = cursor.fetchone()

        # If not -> create it
        if result is None:
            cursor1 = self.conn.execute(
                "INSERT INTO hiddennode (create_key) VALUES ('%s')" % create_key
            )
            hiddenid = cursor1.lastrowid
            # Put in default weights
            for wordid in wordids:
                self.set_strength(wordid, hiddenid, 0, 1.0/len(wordids))

            for urlid in urls:
                self.set_strength(hiddenid, urlid, 1, 0.1)
            self.conn.commit()


if __name__ == "__main__":
    mynet = SearchNet('nn.db')
    # mynet.make_tables()
    # wWorld, wRiver, wBank = 101, 102, 103
    # uWorldBank, uRiver, uEarth = 201, 202, 203
    # mynet.generate_hidden_node([wWorld, wBank], [uWorldBank, uRiver, uEarth])
    #
    # for c in mynet.conn.execute('select * from wordhidden'):
    #     print c
    # print 'Shithole'
    # for c in mynet.conn.execute('select * from hiddenurl'):
    #     print c
