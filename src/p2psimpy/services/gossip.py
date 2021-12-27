from p2psimpy.config import Dist
from p2psimpy.messages import GossipMessage, MsgRequest, MsgResponse, SyncPing, SyncPong
from p2psimpy.services.base import BaseHandler, BaseRunner
from p2psimpy.utils import Cache


class GossipService(BaseHandler):
    """
    Simple gossip service to handle gossip messages and rely them to neighbors. 
    """

    def _store_message(self, msg, msg_id=None):
        if not msg_id:
            msg_id = msg.id

        self.peer.store_value('msg_time', msg_id, self.env.now)
        self.peer.store_value('msg_data', msg_id, msg)

    def __init__(self, peer, fanout=3, exclude_peers: set = None,
                 exclude_types: set = None):
        super().__init__(peer)

        self.fanout = fanout
        if exclude_peers is None:
            self.exclude_peers = set()
        else:
            self.exclude_peers = exclude_peers
        self.exclude_types = exclude_types

    def wait(self):
        yield self.env.timeout(100)

    def handle_message(self, msg):
        # Store message localy
        self._store_message(msg)
        if msg.ttl > 0:
            # Rely message further, modify the message
            exclude_peers = {msg.sender} | self.exclude_peers
            # Use peer gossip - it will sample self.config.fanout and exclude sender
            # If you need to exclude some peers: add it to the set
            self.peer.gossip(GossipMessage(self.peer, msg.id, msg.data, msg.ttl-1,
                                           pre_task=msg.pre_task, post_task=msg.post_task),
                             self.fanout, except_peers=exclude_peers, except_type=self.exclude_types)

    @property
    def messages(self):
        return GossipMessage,


class MessageResponder(BaseHandler):

    def _form_message_response(self, msg):
        response = {}
        for k in msg.data:
            response[k] = self.peer.get_value('msg_data', k)
        return response

    def handle_message(self, msg):
        self.peer.send(msg.sender, MsgResponse(
            self.peer, self._form_message_response(msg)))

    @property
    def messages(self):
        return MsgRequest,


class PullGossipService(MessageResponder, BaseRunner):

    def __init__(self, peer,
                 exclude_types: set = None, exclude_peers: set = None,
                 fanout=3, round_time=500,
                 init_timeout=Dist('norm', (200, 100))):
        super().__init__(peer)

        self.fanout = fanout
        if exclude_peers is None:
            self.exclude_peers = set()
        else:
            self.exclude_peers = exclude_peers
        self.exclude_types = exclude_types

        self.sync_time = round_time
        self.ini_time = abs(Cache(init_timeout).fetch())

    def _get_sync_indexes(self):
        """ Will return all known indexes 
        """
        # All keys from the storage 
        return self.peer.storage['msg_data'].keys()

    def run(self):
        yield self.env.timeout(self.ini_time)
        while True:
            # choose random peers and perioducally synchronize the data - by filling out the missing links
            yield self.env.timeout(self.sync_time)

            self.peer.gossip(SyncPing(self.peer, self._get_sync_indexes()), self.fanout,
                             except_peers=self.exclude_peers, except_type=self.exclude_types)

    def _self_missing(self, msg):
        known = self._get_sync_indexes()

        me_missing = set(msg.data) - set(known)
        if len(me_missing) > 0:
            # Request missing messages
            self.peer.send(msg.sender, MsgRequest(self.peer, me_missing))

    def _peer_missing(self, msg):
        known = self._get_sync_indexes()
        peer_missing = set(known) - set(msg.data)
        if len(peer_missing) > 0:
            self.peer.send(msg.sender, SyncPong(self.peer, peer_missing))

    def _store_message(self, msg, msg_id=None):
        if not msg_id:
            msg_id = msg.id

        self.peer.store_value('msg_time', msg_id, self.peer.env.now)
        self.peer.store_value('msg_data', msg_id, msg)

    def handle_message(self, msg):
        if type(msg) == GossipMessage:
            self._store_message(msg)
        elif type(msg) == SyncPing:
            # Send sync pong if there more known messages
            self._peer_missing(msg)
            self._self_missing(msg)
        elif type(msg) == SyncPong:
            self._self_missing(msg)
        elif type(msg) == MsgRequest:
            # Answer with message response
            MessageResponder.handle_message(self, msg)
        elif type(msg) == MsgResponse:
            # Apply to the local storage
            for k, v in msg.data.items():
                self._store_message(v, k)

    @property
    def messages(self):
        return GossipMessage, SyncPing, SyncPong, MsgRequest, MsgResponse

class PushPullGossipService(PullGossipService, GossipService):

    def handle_message(self, msg):

        if type(msg) == GossipMessage:
            GossipService.handle_message(self, msg)
        else:
            PullGossipService.handle_message(self, msg)
