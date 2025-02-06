import pyhop
import json

def check_enough(state, ID, item, num):
    """Check if the agent has enough of an item."""
    if getattr(state, item)[ID] >= num:
        return []
    return False

def produce_enough(state, ID, item, num):
    """Produce an item until the agent has enough."""
    return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
    """Ensure an item is produced if it's not already available."""
    #if item in state.__dict__ and state.__dict__[item][ID] > 0: #does not work when you need multiple of it. rails need 6 ingots. 
    #    return []  # Item already available, no need to produce
    return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)


def make_method(name, rule):
    """Generate a method for crafting an item based on the recipe."""
    def method(state, ID):
        sub_tasks = []
        if 'Requires' in rule:
            #['bench', 'furnace', "iron_axe", "stone_axe", "wooden_axe", "iron_pickaxe", "wooden_pickaxe", "stone_pickaxe"]
            for req in sorted(rule['Requires'], key=lambda x: rule['Requires'][x]):
                sub_tasks.append(('have_enough', ID, req, rule['Requires'][req]))
        
        if 'Consumes' in rule:
            for consume in sorted(rule['Consumes'], key=lambda x: rule['Consumes'][x]):
                sub_tasks.append(('have_enough', ID, consume, rule['Consumes'][consume]))
        
        op_name = 'op_{}'.format(name.replace(" ", "_"))  # Ensure consistent naming
        sub_tasks.append((op_name, ID))
        return sub_tasks
    
    return method


def declare_methods(data):
    """Declare crafting methods based on JSON data, prioritizing fastest methods first."""
    for item, rule in sorted(data['Recipes'].items(), key=lambda x: x[1]['Time']):
        method = make_method(item, rule)
        pyhop.declare_methods('produce_{}'.format(list(rule['Produces'].keys())[0]), method)

    """
    make_prior = ['bench', 'furnace', 'ingot', 'ore', 'coal', 'cobble', 'stick', 'plank', 'wood', 'iron_axe', 'wooden_axe','stone_axe', 'iron_pickaxe', 'wooden_pickaxe', 'stone_pickaxe']
    for y in make_prior:
         temp_list = []
         
         for x in data["Recipes"]:
              if( y in data["Recipes"][x]['Produces']):
                  temp_list.append((x, data['Recipes'][x]))
         sorted(temp_list, key=lambda x: x[1]["Time"])
         temp_list_2 = []
         
         for item, rule in temp_list:
            print(item ,rule)
            if item == 'iron_axe for wood':
                continue
            method = make_method(item, rule)
            temp_list_2.append(method)
         
         pyhop.declare_methods('produce_{}'.format(list(rule['Produces'].keys())[0]), *temp_list_2)
		"""

def make_operator(rule):
    """Generate an operator function based on the recipe rule."""
    def operator(state, ID):
        if 'Requires' in rule:
            for req in rule['Requires']:
                if state.__dict__.get(req, {}).get(ID, 0) < rule['Requires'][req]:
                    #print(f"Checking requirements for {ID}: {state.__dict__.get(req, {})}")
                    return False  # Missing requirement
        
        for produce in rule['Produces']:
            if getattr(state, 'wood')[ID] > 2 and produce == 'wood':
                 return False
            if getattr(state, 'stick')[ID] > 2 and produce == 'stick':
                 return False
            if getattr(state, 'plank')[ID] > 4  and produce == 'plank':
                 return False
            if getattr(state, 'ore')[ID] > 1 and produce == 'ore':
                 return False
            if getattr(state, 'ingot')[ID] > 6 and produce == 'ingot':
                 return False
            if getattr(state, 'coal')[ID] > 1 and produce == 'coal':
                 return False
            if getattr(state, 'cobble')[ID] > 8 and produce == 'cobble':
                 return False
            
        if 'Consumes' in rule:
            for consume in rule['Consumes']:
                if state.__dict__.get(consume, {}).get(ID, 0) < rule['Consumes'][consume]:
                    return False  # Not enough items to consume
            for consume in rule['Consumes']: #seperated so that it will only remove if it never returns false.
                state.__dict__[consume][ID] -= rule['Consumes'][consume]
        
        for produce in rule['Produces']:
            state.__dict__.setdefault(produce, {ID: 0})
            state.__dict__[produce][ID] += rule['Produces'][produce]
        
        if 'Time' in rule:
            state.time[ID] -= rule['Time']
        
        return state
    
    return operator


def declare_operators(data):
    """Declare operators based on crafting recipes."""
    for item, rule in data['Recipes'].items():
        op_name = 'op_{}'.format(item.replace(" ", "_"))  # Fix operator name
        operator_function = make_operator(rule)
        
        # Register operator correctly
        pyhop.declare_operators(operator_function)  # 🔴 Wrong way
        
        # ✅ Correct way: Give it the proper name
        pyhop.operators[op_name] = operator_function

        #print(f"Declared Operator: {op_name}")  # Debugging Output

    #print(f"Registered Operators: {list(pyhop.operators.keys())}")  # Print all operators




def add_heuristic(data, ID):
    """Prune impossible paths based on time constraints and prevent infinite recursion."""
    def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
        if state.time[ID] <= 0:
            return True  # Prune branches where time runs out
        
        for tool in data['Tools']:#DO NOT MAKE MORE THAN 1 TOOL
            if getattr(state, tool)[ID] > 1:
                return True
        
        if(len(calling_stack) > 10):
            if calling_stack[-10:].count(curr_task) > 2:
                 return True #if same task happens 3 times, its probably infinite recursion.
        
        if(len(tasks) / 2 > state.time[ID]):
            return True
		
            
        
        return False
    
    pyhop.add_check(heuristic)

def set_up_state(data, ID, time=0):
    """Initialize the starting state from JSON data."""
    state = pyhop.State('state')
    state.time = {ID: time}
    
    for item in data['Items'] + data['Tools']:
        setattr(state, item, {ID: 0})
    
    for item, num in data['Initial'].items():
        setattr(state, item, {ID: num})
    
    return state


def set_up_goals(data, ID):
    """Set up the goal state from JSON data."""
    return [('have_enough', ID, item, num) for item, num in data['Goal'].items()]

if __name__ == '__main__':
	rules_filename = 'crafting.json'

	with open(rules_filename) as f:
		data = json.load(f)

	state = set_up_state(data, 'agent', time=100) # allot time here
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')

	#pyhop.print_operators()
	#pyhop.print_methods()

	#Hint: verbose output can take a long time even if the solution is correct; 
	 #try verbose=1 if it is taking too long
	#pyhop.pyhop(state, goals, verbose=3)	
	#pyhop.pyhop(state, [('have_enough', 'agent', 'wooden_axe', 1), ('have_enough', 'agent', 'wooden_pickaxe', 1)], verbose=3)
	pyhop.pyhop(state, [('have_enough', 'agent', 'ingot', 3)], verbose=3)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=1)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 10)], verbose=3)
