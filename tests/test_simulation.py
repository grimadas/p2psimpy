import networkx as nx

from p2psimpy.config import Config, Dist, PeerType
from p2psimpy.consts import MBit
from p2psimpy.simulation import Simulation


class Locations(Config):
    locations = ['LocA', 'LocB']
    latencies = {
        'LocB': {'LocB': Dist('gamma', (1, 1, 1))},
        'LocA': {'LocB': Dist('norm', (12, 2)), 'LocA': Dist('norm', (2, 0.5))},
    } 

# Number of nodes
N = 10

# Generate network topology 
G = nx.erdos_renyi_graph(N, 0.5)
nx.set_node_attributes(G, {k: 'basic' for k in G.nodes()}, 'type')

class PeerConfig(Config):
    location = Dist('sample', Locations.locations)
    bandwidth_ul = Dist( 'norm', (50*MBit, 10*MBit))
    bandwidth_dl = Dist( 'norm', (50*MBit, 10*MBit))

# Let's add ConnectionManager - that will periodically ping neighbours and check if they are online 
from p2psimpy.services.connection_manager import BaseConnectionManager
# For each service you can define own configuration, or use default values.   
# Lets use base connection manager - that will periodically ping peer and disconnect unresponsive peers.

services = (BaseConnectionManager,)
peer_types = {'basic': PeerType(PeerConfig, services)}

sim = Simulation(Locations, G, peer_types)

def test_sim_run():
    sim.run(100)
    assert sim.time == 100