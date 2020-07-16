import asyncio, asyncws, threading, json, requests
from functools import wraps
from .schedule import Schedule
from .entity import Entity

loop = asyncio.get_event_loop()
scheduler = Schedule(loop)


class Event(Entity):
    def __getattr__(self, item):
        # Override in case attribute doesn't exist yet
        return None


class EventListener:

    """ Listen for HA event on specific entity

    :param event_type: HomeAssistant event to subscribe to
    :param id: period-separated string representing the entity id path in the event json
    :return:
    """

    def __init__(self, event_type, id):
        self.event_type = event_type
        self.entity_id_json_keys = id.split('.')
        self.id_listeners = {}

    def add_id_listener(self, ha, id, entity):
        ha.ensure_subscribed(self)
        self.id_listeners.setdefault(ha, {})[id] = entity

    def call(self, hass_parent, msg):
        # Extract entity_id
        id = msg
        for key in self.entity_id_json_keys:
            id = id[key]

        # Call entity
        if id in self.id_listeners[hass_parent]:
            entity = self.id_listeners[hass_parent][id]
            entity._set_attributes_from_json(msg['data'])
            entity.call(msg)


    def __call__(self, ha, id):
        event = Event(ha, id)
        self.add_id_listener(ha, id, event)
        return event


entity_state_changed_event = EventListener('state_changed', id='data.new_state.entity_id')
class HomeAssistant:

    def __init__(self, url, token):
        # Connection
        self.rest_url = f"http://{url}/api/"
        self.ws_url = f"ws://{url}/api/websocket"
        self.token = token
        self._message_id = 10

        # Events+Entities
        self._event_listeners = {}

        # Run
        loop.run_until_complete(self._connect_websocket())
        threading.Thread(target=lambda: loop.run_until_complete(self._callback_loop())).start()

    def init_entities(self):
        i = 0
        if (active_entity_list := entity_state_changed_event.id_listeners.get(self)):
            entity_list = requests.get(self.rest_url + "states", headers={
                "Authorization": f"Bearer {self.token}",
                "content-type": "application/json",
            }).json()
            for o in entity_list:
                entity_id = o['entity_id']

                if (entity := active_entity_list.get(entity_id)):
                    entity._set_attributes_from_json(o['attributes'], state=o.get('state'))
                    i += 1

        print(f"Loaded {i} entities")

    @property
    def message_id(self):
        self._message_id += 1
        return self._message_id

    def ensure_subscribed(self, event_listener):
        event_type = event_listener.event_type
        if event_type not in self._event_listeners:
            print("Subscribing to", event_type)
            loop.create_task(
                self.ws.send(json.dumps({
                    'id': self.message_id,
                    'type': 'subscribe_events',
                    'event_type': event_type
                }))
            )
            self._event_listeners[event_type] = event_listener

    def call_service(self, entity, data):
        data.update({'entity_id': entity.id})
        call = {
            'id': self.message_id,
            'domain': entity.id.split('.')[0],
            'type': "call_service",
            'service': entity.compute_service(),
            'service_data': data
        }
        print("call:", call)
        loop.create_task(self.ws.send(json.dumps(call)))

    def add_entity_listener(self, id, entity):
        entity_state_changed_event.add_id_listener(self, id, entity)

    async def _connect_websocket(self):
        self.ws = await asyncws.connect(self.ws_url)

        # Authenticate
        await self.ws.send(json.dumps({'type': 'auth', 'access_token': self.token}))

    async def _callback_loop(self):
        while True:
            message = await self.ws.recv()
            message = json.loads(message)

            if message is None:
                break
            print(message)

            if message['type'] == 'event':
                event_msg = message['event']
                event_type = event_msg['event_type']
                if event_type in self._event_listeners:
                    self._event_listeners[event_type].call(self, event_msg)


import inspect
class Room:

    _methods_to_watch = {}

    def __init__(self):
        # Get all entities
        self._entities = inspect.getmembers(self, lambda a: isinstance(a, Entity))

        # Assign onchange() functions to their respective entities
        for func, entities in self._methods_to_watch.items():
            func = getattr(self, func.__name__)
            if not entities:
                for name, entity in self._entities:
                    entity.add_event_call(func)
            else:
                for entity in entities:
                    entity.add_event_call(func)

    def onchange(*entities):
        def decorator(func):
            Room._methods_to_watch[func] = entities
            @wraps(func)
            def inner(*args, **kwargs):
                return func(*args, **kwargs)
            return inner
        return decorator
