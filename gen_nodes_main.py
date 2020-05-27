###
# This is the main entry for generating a node layout based on current market conditions
# See README.md for how to update values and modify program settings
###
from copy import deepcopy

from gen_nodes_greedy import gen_main


# Edit values here to match your setup and desired outcome
def main():
	# How many cp do you want to allocate to your worker empire
	# Starting at min and incrementing by step, max inclusive, will be generated
	c_cp_step = 10
	c_min_cp = 340
	c_max_cp = 360
	# how long are you away from game for "sleep"
	c_sleep = 10
	# how often do you want to feed the workers
	c_feed = 4
	# Node material that are required to get
	r_gathers = set()#{
#		"Chicken Meat"
#	}
	# resource nodes that are required to be in the resulting tree
	# Note this only supports resource node id
	r_nodes = [
#		1720,  # star's end excavation
	]
	# Non-resource nodes as required. EG Pila Ku Jail
	# node_id:city_list pairs
	# Note that this will overwrite any production and distances of that node, do not put resource nodes here
	r_monster_node = {
		1390: ['Arehaza Town'],  # Roud Sulphur
		1384: ['Muiquun'],  # Pila Ku Jail
		1619: ['Grana'],  # Tooth Fairy Forest
		1669: ['Duvencrune'],  # Blood Wolf Settlement
		1655: ['Duvencrune'],  # Sherekhan Necropolis
	}

	# List any p2w worker purchases
	# comment out a city to remove it from results
	b_workers = {
		'Altinova': 3,
		'Ancado Inner Harbor': 0,
		'Arehaza Town': 0,
		'Calpheon': 3,
		'Duvencrune': 3,
#		'Epheria Port': 0,
		'Glish': 3,
		'Grana': 3,
		'Heidel': 3,
#		'Iliya Island': 0,
		'Keplan': 3,
		"Muiquun": 0,
		'Old Wisdom Tree': 3,
		'Olvia': 3,
		'Sand Grain Bazaar': 3,
		'Shakatu': 3,
		'Tarif': 3,
		'Trent': 3,
		'Valencia City': 3,
		'Velia': 3
	}
	# This will run until all scenarios are generated.
	for val in range(c_min_cp, c_max_cp+1, c_cp_step):
		print(f"Starting {val} cp generation")
		gen_main(c_sleep, c_feed, deepcopy(r_gathers), deepcopy(r_nodes), deepcopy(r_monster_node), deepcopy(b_workers), val)


if __name__ == "__main__":
	main()