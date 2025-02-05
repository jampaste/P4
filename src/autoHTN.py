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
    if item in state.__dict__ and state.__dict__[item][ID] > 0:
        return []  # Item already available, no need to produce
    return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)


def make_method(name, rule):
    """Generate a method for crafting an item based on the recipe."""
    def method(state, ID):
        sub_tasks = []
        
        if 'Requires' in rule:
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


def make_operator(rule):
    """Generate an operator function based on the recipe rule."""
    def operator(state, ID):
        if 'Requires' in rule:
            for req in rule['Requires']:
                if state.__dict__.get(req, {}).get(ID, 0) < rule['Requires'][req]:
                    print(f"Checking requirements for {ID}: {state.__dict__.get(req, {})}")
                    return False  # Missing requirement
        
        if 'Consumes' in rule:
            for consume in rule['Consumes']:
                if state.__dict__.get(consume, {}).get(ID, 0) < rule['Consumes'][consume]:
                    return False  # Not enough items to consume
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
        
        if calling_stack.count(curr_task) > 2:  # Allow one recursion but prevent infinite loops
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

	state = set_up_state(data, 'agent', time=239) # allot time here
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')

	#pyhop.print_operators()
	#pyhop.print_methods()

	#Hint: verbose output can take a long time even if the solution is correct; 
	 #try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=3)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
