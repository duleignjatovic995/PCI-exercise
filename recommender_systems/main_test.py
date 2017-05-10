from recommendations import *
from util import *

# print recommendations.sim_pearson(recommendations.critics,'Lisa Rose','Gene Seymour')

# print recommendations.top_matches(recommendations.critics, 'Toby', n=3)

# print recommendations.get_recommendations(recommendations.critics,'Toby')

# movies = recommendations.transform_prefs(recommendations.critics)
# print recommendations.top_matches(movies, 'Superman Returns')

"""
from deliciousrec import *
import random


delusers = initialize_user_dict('programming')
delusers['tsegaran']={} #Add yourself to the dictionary if you use delicious
fillItems(delusers)

user = delusers.keys()[random.randint(0, len(delusers)-1)]
rec = recommendations.top_matches(delusers,user)
print user
print rec
"""

# itemsim = recommendations.calculate_similar_items(recommendations.critics)
# print itemsim

# print recommendations.get_recommended_items(recommendations.critics, itemsim, 'Toby')

# prefs = recommendations.load_movie_lens()
# print prefs['87']
# itemsim = recommendations.calculate_similar_items(prefs, n=50)
# print recommendations.get_recommendations(prefs, '87')[0:30]


MOVIES = get_movie_titles()
PREFS = load_movielens()

# print personbased_recommend(PREFS, '1')
# print top_matches(PREFS, '1')
# print prefs['87']

print itembased_reccomend(PREFS, '1')
