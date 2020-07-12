


class Entity:
    _domain = ''

    def __init__(self, ha, id, state):
        # if not self._domain:
        #     raise NotImplementedError(f"{self.__class__.__name__}: '_domain' not set")
        self.ha = ha
        self.id = id
        self.state = state

    def __str__(self):
        return f"<Entity: {self.id}>"


class Light(Entity):
    _domain = 'light'

    def turn_on(self, brightness=None, temp=None, rgb=None):
        data = {'service': "turn_on"}
        self.ha.call_service(self.id, data)

    def turn_off(self):
        self.ha.call_service(self.id, {'service': "turn_off"})


class BinarySensor(Entity):
    _domain = 'binary_sensor'


class MediaPlayer(Entity):
    _domain = 'media_player'


class Sensor(Entity):
    _domain = 'sensor'


class Switch(Entity):
    _domain = 'switch'


entity_classes = {
    e._domain: e
    for e in Entity.__subclasses__()
}
