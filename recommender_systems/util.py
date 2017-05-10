from recommendations import *


# vraca id:title dictionary za filmove
def get_movie_titles(path='ml-latest-small/movies.csv'):
    movies = {}
    data = open(path, 'r')
    data.readline()
    for line in data:
        (id, title) = line.split(',')[0:2]
        movies[id] = title
    data.close()
    return movies


# stvara person based dictionary
def load_movielens(path='ml-latest-small/ratings.csv'):
    prefs = {}
    data = open(path)
    movies = get_movie_titles()
    data.readline()
    for line in data:
        (userId, movieId, rating, timestamp) = line.split(',')
        prefs.setdefault(userId, {})
        prefs[userId][movies[movieId]] = float(rating)
    return prefs


# vraca title na osnovu id-a
def get_movie_by_id(identifier, movies):
    return movies[identifier]



