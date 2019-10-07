###
# This is the main entry for generating a node layout based on current market conditions
# See README.md for how to update values and modify program settings
###
from gen_nodes_greedy import gen_main


# Edit values here to match your setup and desired outcome
def main():
	# How many cp do you want to allocate to your worker empire
	c_max_cp = 200-8  # EXAMPLE: Tool manufacturing chain
	# how long are you away from game for "sleep"
	c_sleep = 10
	# how often do you want to feed the workers
	c_feed = 4
	# Node material that are required to get
	r_gathers = {
		"Chicken Meat"
	}
	# resource nodes that are required to be in the resulting tree
	# Note this only supports resource node id
	r_nodes = [
		1720,  # star's end excavation
	]
	# Non-resource nodes as required. EG Pila Ku Jail
	# node_id:city_list pairs
	# Note that this will overwrite any production and distances of that node, do not put resource nodes here
	r_monster_node = {
		1390: ['Valencia City', 'Ancado Inner Harbor', 'Arehaza Town'],  # Roud Sulphur
		1384: ['Muiquun']  # Pila Ku Jail
	}

	# List any p2w worker purchases
	# comment out a city to remove it from results
	b_workers = {
		'Altinova': 0,
		'Ancado Inner Harbor': 0,
		'Arehaza Town': 0,
		'Calpheon': 0,
		'Duvencrune': 0,
		'Epheria Port': 0,
		'Glish': 0,
		'Grana': 0,
		'Heidel': 3,  # EXAMPLE tool manufacturing chain - goblin worker
		'Iliya Island': 0,
		'Keplan': 0,
		"Muiquun": 0,
		'Old Wisdom Tree': 0,
		'Olvia': 0,
		'Sand Grain Bazaar': 0,
		'Shakatu': 0,
		'Tarif': 0,
		'Trent': 0,
		'Valencia City': 0,
		'Velia': 0
	}
	# This will run until you terminate it.
	gen_main(c_sleep, c_feed, r_gathers, r_nodes, r_monster_node, b_workers, c_max_cp)


if __name__ == "__main__":
	main()