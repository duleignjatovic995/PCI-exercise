import cluster

blognames, words, data = cluster.readfile('blogdata.txt')
# clust = cluster.hcluster(data)
# cluster.printclust(clust, labels=blognames)
# cluster.draw_dendrogram(clust, blognames,jpeg='blogclust.jpg')

# rdata = cluster.rotate_matrix(data)
# wordclust = cluster.hcluster(rdata)
# cluster.draw_dendrogram(wordclust, labels=words, jpeg='wordclust.jpg')

# kclust = cluster.kcluster(data, k=10)
# print kclust

# coords = cluster.scale_down(data)
# cluster.draw_2d(coords, blognames, jpeg='blogs2d.jpg')

# rdata = cluster.rotate_matrix(data)
# coords = cluster.scale_down(rdata)
# cluster.draw_2d(coords, words, jpeg='words2d.jpg')
