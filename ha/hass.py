from .entity import Entity, entity_classes
import asyncio, asyncws, threading
import json, time, requests
from functools import wraps

loop = asyncio.get_event_loop()

watch_entities = {}


class Schedule:
    def __init__(self):
        self.scheduled_functions = {}

    def delay_function(self, func, seconds, *args, **kwargs):
        self.scheduled_functions[func] = (time.time() + seconds, args, kwargs)
        print("Scheduler:", func)

    def cancel_function(self, func):
        if func in self.scheduled_functions:
            del self.scheduled_functions[func]
            print("Scheduler canceled:", func)

    def run(self):
        current_time = time.time()
        functions_to_run = []
        for func, values in self.scheduled_functions.items():
            t, args, kwargs = values
            if current_time > t:
                functions_to_run.append((func, args, kwargs))

        for func, args, kwargs in functions_to_run:
            print("Running delayed function:", func)
            func(*args, **kwargs)
            del self.scheduled_functions[func]


class HomeAssistant:

    def __init__(self, url, token):
        self.rest_url = f"http://{url}/api/"
        self.ws_url = f"ws://{url}/api/websocket"
        self.token = token
        self.entities = {}
        self.scheduler = Schedule()
        self.load_entities()
        self.message_id = 10
        threading.Thread(target=self._start_all).start()
        # threading.Thread(target=self._run_scheduler).start()

    def get_entity(self, entity_id) -> Entity:
        return self.entities.get(entity_id, None)

    def _start_all(self):
        loop.run_until_complete(self._connect_websocket())

    def load_entities(self):
        entity_list = requests.get(self.rest_url + "states", headers={
            "Authorization": f"Bearer {self.token}",
            "content-type": "application/json",
        }).json()
        for o in entity_list:
            entity_id = o['entity_id']
            domain = entity_id.split('.')[0]

            if entity_id not in self.entities and domain in entity_classes:
                new_entity = entity_classes[domain](ha=self, id=entity_id, state=o['state'])
                # for attr, value in o['attributes'].items():
                #     setattr(new_entity, attr, value)
                self.entities[entity_id] = new_entity
        print(f"Loaded {len(self.entities)} entities")

    def call_service(self, entity_id, data):
        self.message_id += 1
        data.update({
            'id': self.message_id,
            'domain': entity_id.split('.')[0],
            'type': "call_service",
            'service_data': {
                'entity_id': entity_id
            }
        })
        print("call:", data)
        loop.create_task(self.ws.send(json.dumps(data)))

    def onchange(self, *entity_ids):

        """ Calls wrapped function when the specified entity_id is updated """

        def decorator(func):
            # Add function to watch list
            for entity_id in entity_ids:
                if entity_id not in watch_entities:
                    watch_entities[entity_id] = []
                watch_entities[entity_id].append(func)

            @wraps(func)
            def inner(*args, **kwargs):
                func(*args, **kwargs)
            return inner
        return decorator

    def postpone(self, seconds):

        """ Delays the calling of a function

        When the wrapped function is called, it is placed in a holding area until:
            - The delay time has passed
            - The function is called again, in which case the delay timer is reset
            - The function is cancelled (called with 'cancel=True') and removed from the scheduler entirely
        When the delay time runs out, the function is finally called
        """

        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                if kwargs.get('cancel'):
                    self.scheduler.cancel_function(func)
                else:
                    self.scheduler.delay_function(func, seconds, *args, **kwargs)
            return inner
        return decorator

    async def _connect_websocket(self):
        self.ws = await asyncws.connect(self.ws_url)

        # Authenticate
        await self.ws.send(json.dumps({'type': 'auth', 'access_token': self.token}))

        # Subscribe all
        await self.ws.send(json.dumps(
            {'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'}
        ))

        loop.create_task(self._callback_loop())
        while True:
            await asyncio.sleep(1)
            self.scheduler.run()

    async def _callback_loop(self):
        while True:
            message = await self.ws.recv()
            message = json.loads(message)

            if message is None:
                break

            if message['type'] == 'event':
                data = message['event']['data']
                entity = self.get_entity(data['entity_id'])

                if entity:
                    entity.state = data['new_state']['state']
                    for func in watch_entities.get(entity.id, []):
                        func(entity)
