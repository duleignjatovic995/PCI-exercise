from math import sqrt
from PIL import Image, ImageDraw
import random


def readfile(filename):
    # Read row by row from blogdata.txt
    lines = [line for line in file(filename)]

    # First line is the column titles
    colnames = lines[0].strip().split('\t')[1:]
    rownames = []
    data = []
    for line in lines[1:]:
        p = line.strip().split('\t')
        # First column in each row is the row-name
        rownames.append(p[0])
        # The data for this row is the remainder of the row
        data.append([float(x) for x in p[1:]])
    return rownames, colnames, data


# Measure pearson correlation
def pearson(v1, v2):
    # Simple sums
    sum1 = sum(v1)
    sum2 = sum(v2)

    # Sums of the squares
    sum1Sq = sum([pow(v, 2) for v in v1])
    sum2Sq = sum([pow(v, 2) for v in v2])

    # Sum of the products
    pSum = sum([v1[i] * v2[i] for i in range(len(v1))])

    # Calculate Pearson score
    num = pSum - (sum1 * sum2 / len(v1))
    den = sqrt((sum1Sq - pow(sum1, 2) / len(v1)) * (sum2Sq - pow(sum2, 2) / len(v1)))
    if den == 0:
        return 0
    # Subtract result from 1 to get relative distance - like euclidian
    return 1.0 - num / den


# Define a class that represent nodes or merged nodes and clusters
class Bicluster:
    def __init__(self, vec, left=None, right=None, distance=0.0, id=None):
        self.vec = vec
        self.left = left
        self.right = right
        self.distance = distance
        self.id = id


def hcluster(rows, distance=pearson):
    distances = {}
    currentclusid = -1

    # Clusters are initially just the rows
    # "clust" contains "Bicluster" classes that contains rows from data
    clust = [Bicluster(rows[i], id=i) for i in range(len(rows))]

    while len(clust) > 1:
        lowestpair = (0, 1)
        closest = distance(clust[0].vec, clust[1].vec)

        # Loop through every pair looking for the smallest distance
        for i in range(len(clust)):
            for j in range(i + 1, len(clust)):
                # Distances is the cache of distance calculations
                if (clust[i].id, clust[j].id) not in distances:
                    distances[(clust[i].id, clust[j].id)] = distance(clust[i].vec, clust[j].vec)

                d = distances[(clust[i].id, clust[j].id)]

                if d < closest:
                    closest = d
                    lowestpair = (i, j)

        # Calculate average of the two clusters
        mergevec = [(clust[lowestpair[0]].vec[i] + clust[lowestpair[1]].vec[i]) / 2.0 for i in
                    range(len(clust[0].vec))]

        # Create the new cluster
        new_cluster = Bicluster(mergevec, left=clust[lowestpair[0]], right=clust[lowestpair[1]], distance=closest,
                                id=currentclusid)

        # Cluster ids that werent in the original set are negative
        currentclusid -= 1
        del clust[lowestpair[1]]
        del clust[lowestpair[0]]
        clust.append(new_cluster)
    return clust[0]


def printclust(clust, labels=None, n=0):
    # Indent to make hierrarchy layout
    for i in range(n):
        print ' ',
    if clust.id < 0:
        # Negative id means this is branch
        print '-'
    else:
        # Positive id means that tis is an endpoint
        if labels is None:
            print clust.id
        else:
            print labels[clust.id]
    # Now print the right and left branches
    if clust.left is not None:
        printclust(clust.left, labels=labels, n=n + 1)
    if clust.right is not None:
        printclust(clust.right, labels=labels, n=n + 1)


def get_height(clust):
    # Is this an endpoint? Then the height is just 1
    if clust.left is None and clust.right is None:
        return 1
    # Otherwise the height is the same of the heights of each branch
    return get_height(clust.left) + get_height(clust.right)


def get_depth(clust):
    # The distance of an endpoint is 0.0
    if clust.left is None and clust.right is None:
        return 0
    # The distance of a branch is the greater of its two sides plus its own distance
    return max(get_depth(clust.left), get_depth(clust.right)) + clust.distance


def draw_dendrogram(clust, labels, jpeg='clusters.jpg'):
    # Height and width
    h = get_height(clust) * 20
    w = 1200
    depth = get_depth(clust)

    # Width is fixed, so scale distances accordingly
    scaling = float(w - 150) / depth

    # Create a new image with a white background
    img = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.line((0, h / 2, 10, h / 2), fill=(255, 0, 0))

    # Draw the first node
    drawnode(draw, clust, 10, (h / 2), scaling, labels)
    img.save(jpeg, 'JPEG')


def drawnode(draw, clust, x, y, scaling, labels):
    if clust.id < 0:
        h1 = get_height(clust.left) * 20
        h2 = get_height(clust.right) * 20
        top = y - (h1 + h2) / 2
        bottom = y + (h1 + h2) / 2
        # Line length
        ll = clust.distance * scaling
        # Vertical line from this cluster to children
        draw.line((x, top + h1 / 2, x, bottom - h2 / 2), fill=(255, 0, 0))

        # Horizontal line to left item
        draw.line((x, top + h1 / 2, x + ll, top + h1 / 2), fill=(255, 0, 0))

        # Horizontal line to right item
        draw.line((x, bottom - h2 / 2, x + ll, bottom - h2 / 2), fill=(255, 0, 0))

        # Call the function to draw the left and right nodes
        drawnode(draw, clust.left, x + ll, top + h1 / 2, scaling, labels)
        drawnode(draw, clust.right, x + ll, bottom - h2 / 2, scaling, labels)
    else:
        # If this is an endpoint, draw the item label
        draw.text((x + 5, y - 7), labels[clust.id], (0, 0, 0))


def rotate_matrix(data):
    new_data = []
    for i in range(len(data[0])):
        new_row = [data[j][i] for j in range(len(data))]
        new_data.append(new_row)
    return new_data


def kcluster(rows, distance=pearson, k=4):
    # Determine the minimum and maximum values for each point
    ranges = [((min([row[i] for row in rows])), (max([row[i] for row in rows]))) for i in range(len(rows[0]))]

    # Create k randomly placed centroids
    clusters = [[random.random() * (ranges[i][1] - ranges[i][0]) + ranges[i][0] for i in range(len(rows[0]))]
                for _ in range(k)]

    last_matches = None
    for t in range(100):
        print 'Iteration %d' % t
        best_matches = [[] for _ in range(k)]

        # Find which centroid is the closest for each row
        for j in range(len(rows)):
            row = rows[j]
            best_match = 0
            # For every centroid
            for i in range(k):
                # Calculate distance between i-th centroid and the giver example(row)
                d = distance(clusters[i], row)
                # Find the closest centroid
                if d < distance(clusters[best_match], row):
                    best_match = i
            best_matches[best_match].append(j)

        # If the results are the same as last time, this is complete
        if best_matches == last_matches:
            break
        last_matches = best_matches

        # Move the centroids to the average of their members
        for i in range(k):
            avgs = [0.0] * len(rows[0])
            if len(best_matches[i]) > 0:
                # For every example in cluster
                for rowid in best_matches[i]:
                    # For every feature of centroid
                    for m in range(len(rows[rowid])):
                        # Sum by features for cluster
                        avgs[m] += rows[rowid][m]
                for j in range(len(avgs)):
                    avgs[j] /= len(best_matches[i])
                # New value for centroids
                clusters[i] = avgs
    return best_matches


def tanamoto(v1, v2):
    c1, c2, shr = 0, 0, 0
    for i in range(len(v1)):
        if v1[i] != 0:
            c1 += 1
        if v2[i] != 0:
            c2 += 1
        if v1[i] != 0 and v2[i] != 0:
            shr += 1
    return 1.0 - (float(shr) / (c1 + c2 - shr))


def scale_down(data, distance=pearson, rate=0.01):
    n = len(data)

    # The real distances between every pair of items
    real_dist = [[distance(data[i], data[j]) for j in range(n)] for i in range(0, n)]

    # Random initialize the starting points of the locations in 2D
    location = [[random.random(), random.random()] for i in range(n)]
    fake_dist = [[0.0 for j in range(n)] for i in range(n)]

    last_error = None
    for m in range(0, 1000):
        # Find projected distances
        for i in range(n):
            for j in range(n):
                fake_dist[i][j] = sqrt(sum([pow(location[i][x] - location[j][x], 2) for x in range(len(location[i]))]))

        # Move points
        grad = [[0.0, 0.0] for _ in range(n)]

        total_error = 0
        for k in range(n):
            for j in range(n):
                if j == k:
                    continue
                # The error is percent difference between the distances
                error_term = (fake_dist[j][k] - real_dist[j][k]) / real_dist[j][k]

                # Each point needs to be moved away from or towards the other point in proportion to how much error
                # it has
                grad[k][0] += ((location[k][0] - location[j][0]) / fake_dist[j][k]) * error_term
                grad[k][1] += ((location[k][1] - location[j][1]) / fake_dist[j][k]) * error_term

                # Keep track of the total error
                total_error += abs(error_term)
        print 'Total error: ', total_error

        # If the answer got worse bu moving the points, we are done
        if last_error and last_error < total_error:
            break
        last_error = total_error

        # Move each of the points by the learning rate times the gradient
        for k in range(n):
            location[k][0] -= rate * grad[k][0]
            location[k][1] -= rate * grad[k][1]

    return location


def draw_2d(data, labels, jpeg='mds2d.jpg'):
    img = Image.new('RGB', (2000, 2000), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i in range(len(data)):
        x = (data[i][0] + 0.5) * 1000
        y = (data[i][1] + 0.5) * 1000
        draw.text((x, y), labels[i], (0, 0, 0))
    img.save(jpeg, 'JPEG')
