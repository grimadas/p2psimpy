# p2psimpy

[![Tests](https://github.com/grimadas/p2psimpy/workflows/Tests/badge.svg)](https://github.com/grimadas/p2psimpy/actions?workflow=Tests)
[![PyPI](https://img.shields.io/pypi/v/p2psimpy.svg)](https://pypi.org/project/p2psimpy/)


A simple simulator for peer-to-peer protocols based on [SimPy](https://simpy.readthedocs.io/en/latest/).

  
The library provides means to simulate distributed or decentralized system run over a network.
The simulation runs as a multi-agent system each running  services and exchanging messages. 

## Installation 
If you have pip installed, just type: 
```bash
$ pip install p2psimpy 
```

## Simulation example

For each simulation you should specify what each agent should run, the latency for the messages and the physical attributes on an agent.

Here is an example in which peers are connected in a random network, and each peer runs a connection manager. The connection manager periodically pings the connected peers and disconnects them if they are unresponsive.  
 The simulation looks like this: 

```python
import networkx as nx

from p2psimpy.config import Config, Dist, PeerType
from p2psimpy.consts import MBit
from p2psimpy.simulation import Simulation
from p2psimpy.services.connection_manager import BaseConnectionManager

# Locations and latency matrix between the locations 
class Locations(Config):
	locations = ['LocA', 'LocB']
	latencies = {
				 'LocB': {'LocB': Dist('gamma', (1, 1, 1))},
				 'LocA': {'LocB': Dist('norm', (12, 2)), 
						  'LocA': Dist('norm', (2, 0.5))},
				}

N = 10
# Generate network topology
G = nx.erdos_renyi_graph(N, 0.5)
nx.set_node_attributes(G, {k: 'basic' for k in G.nodes()}, 'type')	

# Physical properties of a peer. Peer will randomly get an attribute from a given distribution.
class PeerConfig(Config):
	location = Dist('sample', Locations.locations)
	bandwidth_ul = Dist( 'norm', (50*MBit, 10*MBit))
	bandwidth_dl = Dist( 'norm', (50*MBit, 10*MBit))

# Each basic peer runs a ConnectionManager: that will periodically ping neighbours and check if they are online
services = (BaseConnectionManager,)
peer_types = {'basic': PeerType(PeerConfig, services)}

sim = Simulation(Locations, G, peer_types)
# run the simulation for 1_000 milliseconds 
sim.run(1_000)
```
