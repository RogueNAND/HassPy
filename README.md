# HassPy
The goal of this project is to expand the automation capabilities of [HomeAssistant](home-assistant.io) through an easy-to-use python micro-framework.


Creating a Basic script
----

Setup a HomeAssistant connection:
```python
from hass import HomeAssistant
ha = HomeAssistant("10.0.0.16:8123", "api_authentication_token")
```

Setup a room with one light and one sensor
```python
from hass import Room
from hass.entity import Light, Sensor  # Entity definitions

class MasterBedroom(Room):
    light = Light(ha, 'light.master_bedroom_0')
    motion_sensor = Sensor(ha, 'binary_sensor.master_bedroom_motion_0')
```

Now we just have to create the logic for triggering the light on and off.<br>
This function is triggered by the motion_sensor using tbe @Room.onchange() decorator:
```python
class MasterBedroom(Room):

    light = Light(ha, 'light.master_bedroom_0')
    motion_sensor = Sensor(ha, 'binary_sensor.master_bedroom_motion_0')

    @Room.onchange(motion_sensor)  # Multiple entities are allowed (comma separated)
    def detect_motion(self, entity, msg):

        """
        :param entity: the entity that triggered onchange()
        :param msg: unmodified HomeAssistant event message
        :return: 
        """

        if self.motion_sensor.state is True:
            self.light.state = True
        else:
            self.light.state = False
```

Perfect! So here's what we have so far:
1. Motion is detected: Turn light on
2. Motion is not detected: Turn light off

And the resulting code:
```python
from hass import HomeAssistant, Room
from hass.entity import Light, Sensor  # Entity definitions

ha = HomeAssistant("10.0.0.16:8123", "api_authentication_token")

class MasterBedroom(Room):

    light = Light(ha, 'light.master_bedroom_0')
    motion_sensor = Sensor(ha, 'binary_sensor.master_bedroom_motion_0')

    @Room.onchange(motion_sensor)  # Multiple entities are allowed (comma separated)
    def detect_motion(self, entity, msg):

        if self.motion_sensor.state is True:
            self.light.state = True
        else:
            self.light.state = False
```

So this is great and all, but we probably don't want the lights to turn off immediately when <i>motion_sensor.state</i> is False. On to Scenes!!

# Scenes
----

Instead of directly manipulating the <i>light.state</i> in our example, we can create an all-powerful <i>Scene</i> to manipulate entities, and even set a delay.

I recommend starting out with two scenes: <i>occupied</i> and <i>unoccupied:</i>
```python
from hass import Scene

occupied = Scene(
    light={'state': True, 'brightness': 255, 'color_temp': 350}
)
unoccupied = Scene(
    light={'state': False}
)
```

To use the scenes in our <i>detect_motion()</i> function, we call our new scene with the appropriate arguments:
```python
def detect_motion(self, entity, msg):

    if self.motion_sensor.state is True:
        occupied(self.light)
    else:
        unoccupied(self.light, delayed=60)  # Add a 60 second delay so our light doesn't turn off immediately when motion stops
```

And that's it!<br>
Scenes are capable of so much more, but that will be covered more in dedicated examples.

# Entity groups
----

Entities can be placed in groups to assist with controlling lots of them.
```python
from hass.entity import Light, Group

class MasterBedroom(Room):
    light_0 = Light(ha, 'light.master_bedroom_0')
    light_1 = Light(ha, 'light.master_bedroom_1')
    light_2 = Light(ha, 'light.master_bedroom_2')
    light_3 = Light(ha, 'light.master_bedroom_3')
    
    lights = Group(light_0, light_1, light_2, light_3)
```
This new <i>lights</i> group can be controlled and manipulated by scenes just like a regular entity.

License
----

MIT
