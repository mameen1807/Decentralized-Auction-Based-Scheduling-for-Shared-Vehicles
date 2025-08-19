"""
Decentralized auction-based scheduling POC
Run: python decentralized_auction_scheduling.py
Requires: numpy, matplotlib (optional)
"""
import numpy as np
import random
from math import hypot
import matplotlib.pyplot as plt

random.seed(0); np.random.seed(0)

# ---------------- Scenario ----------------
NUM_DEPOTS = 3
NUM_SHARED_VEHICLES = 4
NUM_STATIC_VEHICLES_PER_DEPOT = 1
NUM_ORDERS_INITIAL = 9
AREA_SIZE = 100

# generate depot locations
depots = [(20, 20), (80, 20), (50, 80)]

# shared vehicles start at a central hub (50,50)
shared_vehicles = [{'pos': (50,50), 'id': f'S{idx}', 'assigned': None} for idx in range(NUM_SHARED_VEHICLES)]

# each depot has a local small fleet
local_vehicles = []
for d in range(NUM_DEPOTS):
    for v in range(NUM_STATIC_VEHICLES_PER_DEPOT):
        local_vehicles.append({'depot': d, 'pos': depots[d], 'id': f'L{d}_{v}'})

# orders: each is (depot_id, pickup, dropoff, created_time)
def rand_point_around(center, spread=10):
    cx, cy = center
    return (cx + random.uniform(-spread, spread), cy + random.uniform(-spread, spread))

orders = []
for i in range(NUM_ORDERS_INITIAL):
    depot_id = i % NUM_DEPOTS
    pickup = rand_point_around(depots[depot_id], spread=12)
    drop = rand_point_around((random.uniform(0,AREA_SIZE), random.uniform(0,AREA_SIZE)), spread=15)
    orders.append({'id': f'O{i}', 'depot': depot_id, 'pickup': pickup, 'drop': drop, 'created': 0, 'assigned_vehicle': None})

# ---------------- Helpers ----------------
def dist(a,b): return hypot(a[0]-b[0], a[1]-b[1])

def route_cost_for_order(vehicle_pos, pickup, drop):
    return dist(vehicle_pos, pickup) + dist(pickup, drop)

# ---------------- Local scheduling (simple greedy) ----------------
def local_schedule(depot_id, orders_pool, local_vehicles, shared_allocations):
    """
    For a depot: select unassigned orders and try to allocate local vehicles first.
    Returns list of order-> vehicle proposals (for auction if needed)
    """
    proposals = []  # (order_id, vehicle_id, marginal_cost, vehicle_type)
    # local vehicles
    loc_vs = [v for v in local_vehicles if v['depot']==depot_id]
    unassigned = [o for o in orders_pool if o['depot']==depot_id and o['assigned_vehicle'] is None]
    # assign greedily to local vehicles
    for v in loc_vs:
        if not unassigned: break
        o = unassigned.pop(0)
        cost = route_cost_for_order(v['pos'], o['pickup'], o['drop'])
        proposals.append({'order': o, 'vehicle': v['id'], 'marginal_cost': cost, 'vehicle_obj': v, 'type':'local'})
    # propose shared vehicles if orders remain
    for o in unassigned:
        # propose best shared vehicle (lowest cost)
        best_shared = None; best_cost = 1e9; best_obj=None
        for sv in shared_vehicles:
            if sv['assigned'] and sv['assigned']!=depot_id:
                continue
            c = route_cost_for_order(sv['pos'], o['pickup'], o['drop'])
            if c < best_cost:
                best_cost = c; best_shared = sv['id']; best_obj=sv
        if best_shared:
            proposals.append({'order': o, 'vehicle': best_shared, 'marginal_cost': best_cost, 'vehicle_obj': best_obj, 'type':'shared'})
    return proposals

# ---------------- Auctioneer (central but could be decentralized message exchange) ----------------
def run_auction(all_proposals):
    """
    all_proposals: list of proposals from depots
    chooses winner per order by lowest marginal cost, and assigns vehicle
    """
    # group by order
    winners = {}
    for p in all_proposals:
        oid = p['order']['id']
        if oid not in winners or p['marginal_cost'] < winners[oid]['marginal_cost']:
            winners[oid] = p
    # allocate
    for oid,p in winners.items():
        o = p['order']
        vobj = p['vehicle_obj']
        # mark assignment
        o['assigned_vehicle'] = vobj['id']
        if p['type']=='shared':
            vobj['assigned'] = o['depot']  # reserve shared vehicle for depot (simple)
    return list(winners.values())

# ---------------- Dynamic rescheduling event (new orders arrive) ----------------
def inject_new_orders(tim, count=2):
    start_idx = len(orders)
    for i in range(count):
        depot_id = random.randrange(NUM_DEPOTS)
        pickup = rand_point_around(depots[depot_id], spread=12)
        drop = rand_point_around((random.uniform(0,AREA_SIZE), random.uniform(0,AREA_SIZE)), spread=15)
        orders.append({'id': f'O{start_idx+i}', 'depot': depot_id, 'pickup': pickup, 'drop': drop, 'created': tim, 'assigned_vehicle': None})

# ---------------- Simulation loop ----------------
def simulate(time_horizon=10, inject_times=[3,6]):
    metrics = {'total_cost':0, 'assignments':0, 'reassignments':0}
    for t in range(time_horizon):
        # at times, new orders
        if t in inject_times:
            inject_new_orders(t, count=2)
        # each depot proposes
        all_props=[]
        for d in range(NUM_DEPOTS):
            props = local_schedule(d, orders, local_vehicles, shared_vehicles)
            all_props.extend(props)
        winners = run_auction(all_props)
        metrics['assignments'] += len(winners)
        # compute cost tally
        for w in winners:
            metrics['total_cost'] += w['marginal_cost']
        # simplistic: vehicles move to last service point (simulate time passing)
        for v in local_vehicles:
            # if they served something, update pos
            pass
        for sv in shared_vehicles:
            pass
        # For demo: print summary at each time
        assigned_count = sum(1 for o in orders if o['assigned_vehicle'])
        print(f"t={t}: orders={len(orders)} assigned={assigned_count} total_cost={metrics['total_cost']:.1f}")
    return metrics

if __name__ == "__main__":
    metrics = simulate()
    print("SIM DONE:", metrics)
