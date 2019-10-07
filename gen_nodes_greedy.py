import json
import math
import os
from copy import deepcopy
import networkx as nx
import multiprocessing as mp
from functools import partial
from datetime import datetime


# Generate all city combos of a node set
def allcombo(vals, q, mystr, worker_current, worker_max):
	if q:
		for v in vals[q[0]]['distances']:
			if worker_current[v] < worker_max[v]:
				worker_current_copy = worker_current.copy()
				worker_current_copy[v] += 1
				yield from allcombo(vals, q[1:], mystr+[(q[0], v)], worker_current_copy, worker_max)
	else:
		yield mystr


# generator function to find candidates for "best" node layout, only validates worker count
def looper(node_data, len_nodes, nodes, maxlen, start, curlen, used, worker_current, worker_max):
	if curlen == maxlen:
		q = []
		for idx in range(len_nodes):
			if used[idx]:
				q.append(nodes[idx])
		yield from allcombo(node_data, q, [], worker_current, worker_max)
		return

	if start == len_nodes:
		return
	used[start] = 1
	yield from looper(node_data, len_nodes, nodes, maxlen, start+1, curlen+1, used, worker_current, worker_max)
	used[start] = 0
	yield from looper(node_data, len_nodes, nodes, maxlen, start+1, curlen, used, worker_current, worker_max)
	return


def gen_set(node_data, len_nodes, nodes, maxlen, start, curlen, used, worker_current, worker_max):
	for i in range(maxlen, maxlen+1):
		print(f"*** Now considerings {i} resource nodes out of {len_nodes}. ***")
		yield from looper(node_data, len_nodes, nodes, i, start, curlen, used, worker_current, worker_max)


# return a list of nodes that have resources "worth something"
def gen_node_set(node_data, prices, required_gathers, required_nodes, required_monster_nodes, bonus_workers):
	nodes = []
	for node in node_data:
		if node in required_monster_nodes:
			node_data[node]['workload'] = 999
			node_data[node]['distances'] = {}
			for city in required_monster_nodes[node]:
				node_data[node]['distances'][city] = 1000
			node_data[node]['output'] = {"Grilled Bird Meat": 2/3}
			required_nodes.append(node)
		if 'distances' in node_data[node]:
			for city in node_data[node]['distances'].copy():
				if city not in bonus_workers:
					print(f"Removing {city} from {node_data[node]['name']}")
					del node_data[node]['distances'][city]

		if 'distances' in node_data[node] and len(node_data[node]['distances']):
			val = 0
			for item in node_data[node]['output']:
				if item in prices:
					val += prices[item] * node_data[node]['output'][item]
			# if node has no value, skip it
			if not val:
				continue
			if required_gathers.intersection(set(node_data[node]['output'].keys())):
				required_nodes.append(node)
			nodes.append(node)

	for node in required_nodes:
		if node in nodes:
			del nodes[nodes.index(node)]
		nodes.insert(0, node)

	return nodes


# returns the cost of setting worker count at a city to a specific value
def gen_lodging_cost(bonus_workers, housing_data):
	cp_lookup = {}
	cp_total = {}
	for city in bonus_workers:
		if city not in cp_lookup:
			cp_lookup[city] = {}
			cp_total[city] = {}
		for i in range(bonus_workers[city] + 1):
			cp_lookup[city][i] = 0
			cp_total[city][i] = 0
		try:
			for val in housing_data[city]:
				cp_total[city][int(val) + bonus_workers[city]] = housing_data[city][val]['cp']
		except KeyError:
			print(f"No housing data for {city}.")
	for city in cp_total:
		for i in range(max(cp_total[city]), 0, -1):
			cp_lookup[city][i] = cp_total[city][i] - cp_total[city][i - 1]
	return cp_lookup, cp_total


# Determine the raw silver value of ever resource node per city that it can connect to
def gen_node_values(sleep, feed, nodes, node_data, prices):
	node_values = {}
	remainder = (24 - sleep) % feed
	normal_workers = {}
	grana_workers = {}
	with open('worker_stats.csv', 'r') as f:
		f.readline()
		for line in f:
			lstr = line.strip().split(',')
			if lstr[0] == 'all':
				normal_workers[lstr[1]] = {'workspeed': float(lstr[2]), 'movespeed': float(lstr[3]), 'stamina': float(lstr[4])}
			elif lstr[0] == 'grana':
				grana_workers[lstr[1]] = {'workspeed': float(lstr[2]), 'movespeed': float(lstr[3]), 'stamina': float(lstr[4])}
			else:
				print(f"Unknown worker: {repr(line)}")

	for node in nodes:
		node_values[node] = {}
		base_val = 0
		for item in node_data[node]['output']:
			if item in prices:
				base_val += prices[item] * node_data[node]['output'][item]
			else:
				print(f"Missing value for {item}")
		for dest in node_data[node]['distances']:
			node_values[node][dest] = {'max': 0, 'results': {}}
			if dest in ["Grana", "Old Wisdom Tree"]:
				workers = grana_workers
			else:
				workers = normal_workers
			for worker in workers:
				# cycle(seconds) = (distance/speed) * 2 + ceiling(workload/work speed)*600
				time = ((node_data[node]['distances'][dest] / workers[worker]['movespeed']) * 2 + math.ceil(node_data[node]['workload'] / workers[worker]['workspeed']) * 600) / 60
				trips = min(sleep * 60 / time, workers[worker]['stamina']) + \
						min(feed * 60 / time, workers[worker]['stamina']) * ((24 - sleep) // feed) + \
						min(remainder * 60 / time, workers[worker]['stamina'])
				value = trips * base_val - trips * prices['Grilled Bird Meat'] * 2 / 3
				node_values[node][dest]['results'][worker] = int(value)
				if value > node_values[node][dest]['max']:
					node_values[node][dest]['max'] = int(value)
					node_values[node][dest]['trips'] = trips
	return node_values


def gen_best_node_id(maxcp, available_nodes, capitals, node_data, add_worker_cp, graph, node_value, selected):
	ratio = 0
	n_id = None
	ret_city = None
	r_cp = 0
	r_chain = []
	for node_id in available_nodes:
		for city in node_data[node_id]['distances']:
			if node_value[node_id][city]['max'] / node_data[node_id]['contribution'] <= ratio:
				continue
			if city in add_worker_cp:
				cp_current = add_worker_cp[city]
				p = nx.shortest_path(graph, node_id, capitals[city], weight='weight')
				if city == 'Ancado Inner Harbor' and 1339 not in selected:
					p.append(1339)
				for n in p:
					if n not in selected:
						cp_current += node_data[n]['contribution']
				if cp_current <= maxcp and node_value[node_id][city]['max'] / cp_current > ratio:
					ratio = node_value[node_id][city]['max'] / cp_current
					n_id = node_id
					ret_city = city
					r_cp = cp_current
					r_chain = p[:]
	return n_id, ret_city, r_cp, r_chain


# Remove the top maxcp//5 nodes from nodes as they will always be selected in the end result
def remove_good(maxcp, required_nodes, nodes, capitals, node_data, graph, node_value, silver_cp_threshold):
	remove_count = maxcp//5
	available_nodes = nodes.copy()
	good_nodes = []
	add_worker_cp = {}
	for n in required_nodes:
		del available_nodes[available_nodes.index(n)]
	for city in capitals:
		add_worker_cp[city] = 0
	for n in node_value:
		_max = max([node_value[n][city]['max'] for city in node_value[n]])
		if n in available_nodes and _max / node_data[n]['contribution'] < silver_cp_threshold:
			del available_nodes[available_nodes.index(n)]
			remove_count += 1
	print(f"Removing {remove_count} nodes from consideration for base graph out of {len(nodes)}.")

	while len(good_nodes) < remove_count:
		n_id, ret_city, r_cp, r_chain = gen_best_node_id(maxcp, available_nodes, capitals, node_data, add_worker_cp, graph, node_value, [])
		if not n_id:
			break
		good_nodes.append(n_id)
		del available_nodes[available_nodes.index(n_id)]

	sub_nodes = list(set(nodes) - set(good_nodes))
	for n in required_nodes:
		del sub_nodes[sub_nodes.index(n)]
		sub_nodes.insert(0, n)
	return sub_nodes


# given a weighted graph, list of nodes and what they are connected to, determine the cost/value of the resulting graph
# If input graph is less than threshold, fill out with "best choice" nodes
def gen_graph(max_cp, n_graph, capitals, nodes, required_monster_nodes, node_data, cp_lookup, cp_total, node_value, nodestates):
	selected = set()
	trips = 0
	choices = {}
	worker_count = {}
	for city in cp_total:
		worker_count[city] = 0

	# expensive, do after set is validated
	graph = n_graph.copy()
	available_nodes = nodes.copy()

	totalvalue = 0
	for node_id, city in nodestates:
		del available_nodes[available_nodes.index(node_id)]
		if city not in choices:
			choices[city] = []
		choices[city].append(node_id)
		if node_id not in required_monster_nodes:
			worker_count[city] += 1
		if 'trips' in node_value[node_id][city]:
			trips += node_value[node_id][city]['trips']
		totalvalue += node_value[node_id][city]['max']
		p = nx.shortest_path(graph, node_id, capitals[city], weight='weight')
		if city == 'Ancado Inner Harbor' and '1339' not in selected:
			p.append(1339)
		selected = selected.union(p)
		for p_node in p:
			for n in node_data[p_node]['links']:
				graph[n][p_node]['weight'] = 0

	totalcp = 0
	for node in selected:
		totalcp += node_data[node]['contribution']
	for city in worker_count:
		totalcp += cp_total[city][worker_count[city]]

	# while we can add a worker to our current node layout
	while totalcp < max_cp:
		# generate dict of cities that can have a worker added, and how much cp it would cost
		add_worker_cp = {}
		for city in cp_lookup:
			if worker_count[city] + 1 in cp_lookup[city]:
				add_worker_cp[city] = cp_lookup[city][worker_count[city] + 1]
		best_node_id, r_city, r_cp, r_chain = gen_best_node_id(max_cp - totalcp, available_nodes, capitals, node_data, add_worker_cp, graph, node_value, selected)
		if not best_node_id:
			break
		del available_nodes[available_nodes.index(best_node_id)]
		if r_city not in choices:
			choices[r_city] = []
		choices[r_city]. append(best_node_id)
		totalcp += r_cp
		if best_node_id not in required_monster_nodes:
			worker_count[r_city] += 1
		if 'trips' in node_value[best_node_id][r_city]:
			trips += node_value[best_node_id][r_city]['trips']
		totalvalue += node_value[best_node_id][r_city]['max']
		selected = selected.union(r_chain)
		for p_node in r_chain:
			for n in node_data[p_node]['links']:
				graph[n][p_node]['weight'] = 0

	return selected, choices, worker_count, trips, totalvalue, totalcp, nodestates


def gen_main(sleep, feed, required_gathers, required_nodes, required_monster_nodes, bonus_workers, max_cp):
	with open('resources_mine/hr_cleaned_nodes.json', 'r') as f:
		node_data_json = json.load(f)
	node_data = {}
	for node in node_data_json:
		node_data[int(node)] = deepcopy(node_data_json[node])
	with open('resources_mine/hr_capital_housing.json', 'r') as f:
		housing_data = json.load(f)
	with open("items.csv", "r") as f:
		prices = {}
		for line in f:
			lstr = line.strip().split(',')
			prices[lstr[0]] = int(lstr[1])

	# capitals so that possible new nodes can find shortest path
	capitals = {
		'Altinova': 1101,
		'Ancado Inner Harbor': 1343,
		'Arehaza Town': 1380,
		'Calpheon': 601,
		'Duvencrune': 1649,
		'Epheria Port': 604,
		'Glish': 302,
		'Grana': 1623,
		'Heidel': 301,
		'Iliya Island': 1002,
		'Keplan': 602,
		"Muiquun": 1381,
		'Old Wisdom Tree': 1604,
		'Olvia': 61,
		'Sand Grain Bazaar': 1319,
		'Shakatu': 1314,
		'Tarif': 1141,
		'Trent': 608,
		'Valencia City': 1301,
		'Velia': 1
	}
	# Set up our graph in networkx for shortest path calculations
	n_graph = nx.DiGraph()
	n_graph.add_nodes_from(node_data.keys())
	for n in node_data:
		for k in node_data[n]['links']:
			n_graph.add_edge(k, n, weight=node_data[n]['contribution'])
	# Get a list of nodes that have resources
	nodes = gen_node_set(node_data, prices, required_gathers, required_nodes, required_monster_nodes, bonus_workers)
	# Load vendor items after node loop so that we don't consider nodes that only have vendor items
	with open("vendor_items.csv", "r") as f:
		for line in f:
			lstr = line.strip().split(',')
			prices[lstr[0]] = int(lstr[1])
	# create a cost increase relationship tracker for worker counts
	cp_lookup, cp_total = gen_lodging_cost(bonus_workers, housing_data)
	# get the max number of workers per city
	worker_max = {}
	worker_current = {}
	for city in cp_lookup:
		worker_current[city] = 0
		worker_max[city] = max(cp_lookup[city])
	# Calculate all potential raw silver node values
	node_value = gen_node_values(sleep, feed, nodes, node_data, prices)

	sub_nodes = remove_good(max_cp, required_nodes, nodes, capitals, node_data, n_graph, node_value, 100000)

	bon_workers = ', '.join([f"{x}: {bonus_workers[x]}" for x in sorted(bonus_workers)])
	forced_nodes = '\n'.join([f'{node_data[node_data[node]["parent"]]["name"]}->{node_data[node]["name"]}' if 'parent' in node_data[node] else f'{node_data[node]["name"]}' for node in required_nodes])
	mat_prices = '\n'.join([f"{x}: {prices[x]:,}" for x in prices if prices[x]])
	maxval = 0
	maxratio = 0
	count = 0
	goodcount = 0
	gen_graph_partial = partial(gen_graph, max_cp, n_graph, capitals, nodes, required_monster_nodes, node_data, cp_lookup, cp_total, node_value)
	pool = mp.Pool(processes=mp.cpu_count()-2 if mp.cpu_count() > 2 else 1)
	len_cur = len(required_nodes)
	used = [0] * len(nodes)
	for i in range(len_cur):
		used[i] = 1

	newnode = set()
	nextnode = set()

	# Ensure we have a directory to store results
	if not os.path.isdir("results"):
		os.mkdir("results")

	while True:
		if newnode:
			if nextnode == newnode:
				print("Execution terminated as a better +1 node was not found.")
				break
			for node in newnode - nextnode:
				print(f"Adding {node}: {node_data[node_data[node]['parent']]['name'] + ' -> ' if 'parent' in node_data[node] else ''}{node_data[node]['name']} to permanently seeded nodes.")
				used[len_cur] = 1
				len_cur += 1
				sub_nodes.insert(0, sub_nodes.pop(sub_nodes.index(node)))
			nextnode = newnode

		for selected, choices, worker_count, trips, totalvalue, totalcp, nodestates in pool.imap_unordered(gen_graph_partial, gen_set(node_data, len(sub_nodes), sub_nodes, len_cur+1, len_cur, len_cur, used, worker_current, worker_max), chunksize=1):
			count += 1
			ratio = round(totalvalue / totalcp, 2)
			b_value = totalvalue > maxval
			b_ratio = ratio > maxratio
			if b_value or b_ratio and totalcp <= max_cp:
				goodcount += 1
				print(f"New best.  Completed {count:,} checks with {goodcount:,} results so far. This result value {totalvalue:,} and ratio {ratio:,}")
				output = {}
				newnode = set([x[0] for x in nodestates]) - set(required_nodes)
				buf = f'Generated: {datetime.utcnow().strftime("%m/%d/%Y(m/d/y) %H:%M:%S")} UTC\n\n***\nValue: ${totalvalue:,} per day\nContribution: {totalcp}\nSleep Duration: {sleep}\nFood interval: {feed}\nTotal trips(network): {trips:,.2f}, beer {trips/2:,.2f} or chicken {trips/3:,.2f}\n\nBonus workers: {bon_workers}\n\nSeeded Node(s): {newnode}\n\nRequired Nodes:\n{forced_nodes}\n***\n\n'

				for city in sorted(choices):
					workers = worker_count[city] - bonus_workers[city]
					buf += f'***\n{city}\n{housing_data[city][str(workers if workers > 0 else 1)]}\n'
					for node in sorted(choices[city]):
						vals = [(x, round(node_data[node]["output"][x] * node_value[node][city]['trips'], 2)) for x in node_data[node]["output"] if 'trips' in node_value[node][city]]
						vals.sort()
						for item, quant in vals:
							if item not in output:
								output[item] = 0
							output[item] += quant
						buf += f'\n{node_data[node_data[node]["parent"]]["name"] + " -> " if "parent" in node_data[node] else ""}{node_data[node]["name"]}\n{vals}, ${node_value[node][city]["max"]:,}\n{sorted( ((f"{v:,}",k) for k,v in node_value[node][city]["results"].items()), reverse=True)}\n'
					buf += '***\n'

				buf += '\n** Nodes to allocate **\n\n'
				for node in sorted(selected):
					buf += f'{node}: '
					if 'parent' in node_data[node]:
						buf += f'{node_data[node_data[node]["parent"]]["name"]} -> '
					buf += f'{node_data[node]["name"]}\n'

				output_text = '\n'.join([f"{x}: {output[x]:,.2f}" for x in sorted(output)])
				buf += f'\nOutputs:\n{output_text}\n\n'

				buf += f'\nPrices:\n{mat_prices}\n\n'
				buf += f'\nset: {sorted(selected)}\n'

				if b_value:
					with open(f'results/bestvalue.txt', 'w') as f:
						f.write(buf)
						maxval = totalvalue

				if b_ratio:
					with open(f'results/bestratio.txt', 'w') as f:
						f.write(buf)
						maxratio = ratio

			if not count % 1000:
				print(f"Completed {count:,} checks with {goodcount:,} results so far. Best Value {maxval:,} and ratio {maxratio:,}")
		print(f"Completed {count:,} checks with {goodcount:,} results so far. Best Value {maxval:,} and ratio {maxratio:,}")


