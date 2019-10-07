import json
from copy import deepcopy

import networkx as nx
import matplotlib.pyplot as plt

with open('resources_mine/hr_cleaned_nodes.json', 'r') as f:
	node_data_json = json.load(f)
nodes = {}
for node in node_data_json:
	nodes[int(node)] = deepcopy(node_data_json[node])

#  Only change this with last line from results
my_nodes = [1, 21, 22, 24, 45, 48, 132, 136, 144, 171, 183, 184, 301, 302, 304, 321, 322, 323, 345, 347, 432, 438, 439, 440, 480, 488, 601, 602, 608, 621, 622, 624, 628, 629, 632, 633, 638, 652, 653, 661, 674, 703, 708, 715, 717, 718, 834, 835, 840, 841, 842, 852, 853, 855, 901, 902, 905, 908, 951, 952, 1133, 1138, 1141, 1149, 1153, 1161, 1163, 1203, 1204, 1206, 1219, 1301, 1314, 1318, 1319, 1321, 1327, 1328, 1329, 1330, 1379, 1380, 1381, 1383, 1384, 1385, 1387, 1388, 1389, 1390, 1510, 1517, 1554, 1555, 1556, 1558, 1561, 1562, 1618, 1619, 1621, 1622, 1623, 1624, 1627, 1629, 1630, 1638, 1639, 1640, 1642, 1704, 1720]

G = nx.Graph()
G.add_nodes_from(nodes)
colors = []
for n in nodes:
	G.node[n]['pos'] = (nodes[n]['location']['x'], nodes[n]['location']['y'])
	if n in my_nodes:
		G.node[n]['name'] = nodes[n]['name']
	colors.append('blue' if n in my_nodes else 'red')
	for k in nodes[n]['links']:
		if k in nodes:
			G.add_edge(k, n, weight=nodes[n]['contribution'])


pos = nx.get_node_attributes(G, 'pos')
labeldic = nx.get_node_attributes(G, 'name')

fig = plt.figure()
nx.draw(G, node_size=20, with_labels=True, labels=labeldic, font_size=8, pos=pos, node_color=colors, width=.1, alpha=.8, edge_color='white', font_color='white')
plt.show()
