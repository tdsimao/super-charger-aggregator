# Vincent Koeten
# Adapted HW1 value iteration

import numpy as np
from pprint import pprint
from math import pow, ceil
from functools import lru_cache
from EV import EV
from grid import Grid


TRANSITION_TABLE_PRINT_FLOAT_FLAG = False

nEVs = 2 		 # The number of EVs
nChargeSteps = 4 # The number of timesteps needed to charge at full charge rate
nChargeRates = 2 # Currently binary charging (full or nothing)
nPrices = 5 	 # The number of prices categories

nChargeStates = int(pow(nChargeSteps, nEVs)) # Currently assumes all EVs have the same charge rate and time
# nStates = int(nChargeStates * nPrices)
nStates = nChargeStates
nActions = int(pow(nChargeRates, nEVs))
# print("nEVs:%d, nChargeSteps:%d, nPrices:%d, nChargeStates:%d, nStates:%d, nActions:%d" % (nEVs, nChargeSteps, nPrices, nChargeStates, nStates, nActions))
horizon = 12
reward = []
transitionTable = []
evsList = []
grid = None

prices = [p for p in range(1,10)]

def MDP(discount):
	initializeTransitionTable()
	initializeRewardTable()
	optimalAction = solve(discount)
	return optimalAction


def value_iteration():
	"""

	:return: greedy policy for each time step and expected value of each state at timestep 0
	"""
	qn = np.zeros((nStates, nActions))
	policy = []
	# The value iteration algorithm
	for timestep in reversed(range(horizon)):
		qnp1 = np.zeros((nStates, nActions))
		for s in range(nStates):
			for a in getFeasibleActions(s):
				qnp1[s][a] = getReward(s, a, timestep) + future_expected_reward(qn, s, a)
		qn = qnp1
		new_policy =  [greedy_policy(qn[s], s) for s in range(nStates)]
		policy.append(new_policy)

	expected_value = [max(future_expected_reward(qn, s, a) for a in range(nActions)) for s in range(nStates)]
	return policy[::-1], expected_value


def greedy_policy(q, s):
	"""
	return list of greedy feasible actions
	"""
	result = []
	if q is None:
		return result
	max_val = q[0]
	for action in getFeasibleActions(s):
		q_value = q[action]
		if q_value == max_val:
			result.append(action)
		elif q_value > max_val:
			result = [action]
			max_val = q_value
	return result

def future_expected_reward(qn, s, a):
	result = 0
	for sp in range(nStates):
		# prob = transitionTable[s][a][sp]
		# prob = transitionTable[a][s][sp]
		prob = getTransitionProbability(a, s, sp)
		if prob is not 0:
			m = max(qn[sp])
			result += prob * m
	return result

@lru_cache(maxsize=2*nStates)
def getFeasibleActions(s):
	assert 0 <= s < nStates
	global grid, evsList
	actions = []
	sList = chargeStateToList(s)
	batAtMax = [False for x in range(len(evsList))]
	for i in range(len(evsList)):
		if sList[i] >= evsList[i].batteryMax:
			batAtMax[i] = True
	npBat = np.array(batAtMax)
	
	for action in range(nActions):
		aList = chargeActionToList(action)
		for c in aList:
			if c == 1:
				c = True
			else:
				c = False
		npA = np.array(aList)
		result = npA & npBat
		if not any(result):
			if grid.feasible(get_load(evsList, action, grid)):
				actions.append(action)
	return actions


def initializeRewardTable():
	# TODO
	global reward
	reward = [[0 for a in range(nActions)] for s in range(nStates)]
	reward[4][3] = 100.0
	reward[8][3] = 105.0
	reward[11][3] = 52.0
	reward[12][3] = 53.0
	reward[0][0] = 100.0
	reward[0][1] = 100.0
	reward[0][2] = 100.0

def getReward(state, action, timestep):
	# TODO avoid charging/rewarding charging full vehicles
	#Compute number of charging vehicles 
	chargeList = chargeActionToList(action)
	num_evs_charging = sum(chargeList)
	#multiply by price set
	return (100 - getPrice(timestep)) * num_evs_charging

def getPrice(timestep):
	if timestep < 3:
		return 70
	if timestep < 7:
		return 30
	return 90

def getPriceToPriceProb(fromPrice, toPrice):
	# return probability of going from a price to another price

	# priceLevelTable = np.load('level6PercentagesWithoutTime.npy')
	# return priceLevelTable[fromPrice, toPrice]

	# Currently return an equal probability to go from any price to any price
	return 1.0/nPrices

def getTimePriceToPriceProb(currTime, fromPrice, toPrice):
	# return probability of going from a price to another price 
	# from time currTime to currTime + 1

	# priceLevelTable = np.load('level6Percentages.npy')
	# return priceLevelTable[currTime, fromPrice, toPrice]

	# Currently return an equal probability to go from any price to any price at any time
	return 1.0/nPrices

def chargeStateToList(chargeState):
	chargeList = []
	baseMultiplier = 1
	for ev in evsList:
		baseMultiplier *= ev.nChargeSteps
	for i in range(len(evsList)):
		ev = evsList[i]
		baseMultiplier /= ev.nChargeSteps
		chargeList += [int(chargeState / baseMultiplier)]
		chargeState %= baseMultiplier
	return chargeList

def chargeActionToList(chargeAction):
	# NOTE: Currently works for binary charging
	# TODO: Extend for additonal and possibly variable charge rates?
	actionList = []
	for ev in range(len(evsList)):
		# actionList = actionList + [(chargeAction >> ev) & 1]
		actionList = [(chargeAction >> ev) & 1] + actionList
	return actionList

def chargeListToState(chargeList):
	if(len(chargeList) != len(evsList)):
		return None
	chargeState = 0
	baseMultiplier = 1
	for i in range(len(evsList)-1, -1, -1):
		chargeState += baseMultiplier * chargeList[i]
		baseMultiplier *= evsList[i].nChargeSteps
	return chargeState

def chargeListApplyActionList(chargeList, actionList):
	if(len(chargeList) != len(actionList)):
		# TODO throw error?
		return None
	for i in range(len(chargeList)):
		ev = evsList[i]
		newCharge = chargeList[i] + actionList[i]
		if(newCharge <= ev.batteryMax): # ensure that ev is not charging beyond capacity
			chargeList[i] = newCharge
		else:
			chargeList[i] = ev.batteryMax
	return chargeList

def chargeFromState(fromCharge, chargeAction):
	fromChargeList = chargeStateToList(fromCharge)
	chargeActionList = chargeActionToList(chargeAction)
	toChargeList = chargeListApplyActionList(fromChargeList, chargeActionList)
	toCharge = chargeListToState(toChargeList)
	return toCharge

def initializeTransitionTable():
	global transitionTable
	# transitionTable = [[[0 for s in range(nChargeStates)] for a in range(nActions)] for t in range(nChargeStates)]
	transitionTable = [[[0 for s in range(nChargeStates)] for a in range(nChargeStates)] for t in range(nActions)]
	for action in range(nActions):
	# 	for fromPrice in range(nPrices):
	# 		for toPrice in range(nPrices):
		for fromCharge in range(nChargeStates):
			for toCharge in range(nChargeStates):
				if (toCharge == chargeFromState(fromCharge, action)):
					# print("action: %d, charge: from: %d, to %d, price: from: %d, to: %d" % (action, fromCharge, toCharge, fromPrice, toPrice))
					transitionTable[action][fromCharge][toCharge] = 1
					# fromState = nChargeStates * fromPrice + fromCharge
					# toState = nChargeStates * toPrice + toCharge
					# transitionTable[action][fromState][toState] = getPriceToPriceProb(fromPrice, toPrice)

# independent of price and time
# returns probability of success of applying action on fromState resulting in toState (0 or 1)
def getTransitionProbability(action, fromState, toState):
	if toState == chargeFromState(fromState, action):
		return 1
	else:
		return 0

# independent of time
# returns the price probability or 0 if the action does not allow going to that state
def getPriceTransitionProbability(action, fromState, toState, fromPrice, toPrice):
	if getTransitionProbability(action, fromState, toState) == 1:
		return getPriceToPriceProb(fromPrice, toPrice)
	else:
		return 0

# returns the time based price probability or 0 if the action does not allow going to that state
def getTimePriceTransitionProbability(action, fromState, toState, fromPrice, toPrice, currTime):
	if getTransitionProbability(action, fromState, toState) == 1:
		return getTimePriceToPriceProb(currTime, fromPrice, toPrice)
	else:
		return 0

def printTransitionTable():
	for action in range(nActions):
		print("Action %2d" % action)
		for x in range(nStates):
			print("[", end='')
			for y in range(nStates):
				endstr = ""
				if(y < (nStates - 1)):
					endstr = ", "
				val = transitionTable[action][x][y]
				if TRANSITION_TABLE_PRINT_FLOAT_FLAG:
					formatstr = "%-4d"
					if val != 0:
						formatstr = "%1.2f" #%1.2f
					print(formatstr % val, end=endstr)
				else:
					if val == 0:
						print(" ", end = endstr)
					else:
						print("%d" % val, end=endstr)
			print("]")

def initializeIdenticalEVFleet(initBattLevel, battMax, chargeRate, gridPos, deadline):
	global evsList, nEVs, nChargeStates, nStates, nChargeRates, nActions

	for i in range(len(gridPos)):
		evsList += [EV(initBattLevel, battMax, battMax, chargeRate, gridPos[i], deadline)]

	nEVs = len(evsList)
	nChargeStates = 1
	for ev in evsList:
		nChargeStates *= ev.nChargeSteps
	nStates = nChargeStates # For now unless pricing info is kept in state then multiply by nPrices
	nChargeRates = 2
	nActions = int(pow(nChargeRates, nEVs))
	print("nEVs: %d, nPrices: %d, nChargeStates: %d, nStates: %d, nActions: %d" % (nEVs, nPrices, nChargeStates, nStates, nActions))

def printEVs():
	for i in range(len(evsList)):
		print(evsList[i])

def get_load(evs, action, grid):
	global evsList
	evsList = evs
	load = np.zeros(grid.n_nodes)
	for ev_ind, charging_rate in enumerate(chargeActionToList(action)):
		if charging_rate > 0:
			ev = evsList[ev_ind]
			power_consumption = 200.  # power consumption should be a parameter of the EV
			# multiply by charging in case of multiple chargin states
			load[ev.gridPosition] += ev.chargeRate * power_consumption * charging_rate
	total_load = sum(load)
	load[0] = -total_load
	return load
#----------------------------------------
#			TEST CODE BELOW
#----------------------------------------
def initTestEVFleet():
	global evsList, nEVs, nChargeStates, nStates, nChargeRates, nActions

	evsList =  [EV(0, 2, 2, 1, 0, 23)]
	evsList += [EV(0, 3, 3, 1, 1, 23)]
	evsList += [EV(0, 4, 4, 1, 2, 23)]

	nEVs = len(evsList)
	nChargeStates = 1
	for ev in evsList:
		nChargeStates *= ev.nChargeSteps
	nStates = nChargeStates # For now unless pricing info is kept in state then multiply by nPrices
	nChargeRates = 2
	nActions = int(pow(nChargeRates, nEVs))
	print("nEVs: %d, nPrices: %d, nChargeStates: %d, nStates: %d, nActions: %d" % (nEVs, nPrices, nChargeStates, nStates, nActions))

def testStateToListToState():
	for state in range(nStates):
		print("state: %2d -> " % state, end='')
		csl = chargeStateToList(state)
		print(csl, end=" -> ")
		print(chargeListToState(csl))

def testActionToList():
	for action in range(nActions):
		print("action: %d -> " % action, end='')
		print(chargeActionToList(action))

def testStatePlusAction():
	for state in range(nStates):
		for action in range(nActions):
			print("state + action: %2d+%d -> " % (state, action), end='')
			csl = chargeListApplyActionList(chargeStateToList(state), chargeActionToList(action))
			print(csl, end=" -> ")
			print(chargeListToState(csl))

def test_get_load():
	global evsList, nEVs, nChargeStates, nStates, nChargeRates, nActions, grid

	evsList =  [EV(0, 3, 3, 1, gridPos=2, deadline=23)]
	evsList += [EV(0, 4, 4, 1, gridPos=1, deadline=23)]

	nEVs = len(evsList)
	nChargeStates = 1
	for ev in evsList:
		nChargeStates *= ev.nChargeSteps
	nStates = nChargeStates # For now unless pricing info is kept in state then multiply by nPrices
	nChargeRates = 2
	nActions = int(pow(nChargeRates, nEVs))
	print("nEVs: %d, nPrices: %d, nChargeStates: %d, nStates: %d, nActions: %d" % (nEVs, nPrices, nChargeStates, nStates, nActions))

	grid = Grid.load_grid_from_file('grids/grid_1.txt')
	for action in range(nActions):
		print("action: ", action, chargeActionToList(action))
		load = get_load(evsList, action=action, grid=grid)
		print("load: ", load)
		print("flow", grid.compute_flow(load))
		if grid.feasible(load):
			print("feasible")
		else:
			print("not feasible")
		print("")

	policy, expected_value = value_iteration()

	for i in range(horizon):
		print("time step: | EVs Charging State |  best actions  ")

		for s in range(nStates):
			actions = [chargeActionToList(a) for a in policy[i][s]]
			print("{:11}| {:19}| {}".format(i, str(chargeStateToList(s)), actions))
		print("")

	print("EVs Charging State |  expected value time step 0")
	for s in range(nStates):
		print("{:19}| {}".format(str(chargeStateToList(s)), expected_value[s]))


def test_with_unfeasible_loads():
	evsList =  [EV(0, 3, 3, 1, gridPos=2, deadline=23)]
	evsList += [EV(0, 4, 4, 1, gridPos=2, deadline=23)]

	grid = Grid.load_grid_from_file('grids/grid_1.txt')
	for action in range(nActions):
		print("action: ", action, chargeActionToList(action))
		load = get_load(evsList, action=action, grid=grid)
		print("load: ", load)
		print("flow", grid.compute_flow(load))
		if grid.feasible(load):
			print("feasible")
		else:
			print("not feasible")
		print("")


if __name__ == "__main__":
	test_get_load()
	# test_with_unfeasible_loads()
	# initializeIdenticalEVFleet(0, 2, 1, [0,1,2,3], 23)
	# initTestEVFleet()

	# testStateToListToState()
	# testActionToList()
	# testStatePlusAction()

	# printEVs()

	# initializeTransitionTable()
	# printTransitionTable()
	# OR
	# pprint(transitionTable)

	pass
