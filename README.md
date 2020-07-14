# HassPy
The goal of this project is to expand the capabilities of [HomeAssistant](home-assistant.io) through an easy-to-use python library.


Creating a Basic script
----

Setup a HomeAssistant connection:
```python
from hass import HomeAssistant
ha = HomeAssistant("url:port", "api_authentication_token")
```

Turn on a light when motion sensor is triggered: (we will work on turing it back off in the next step)
```python
@ha.onchange('binary_sensor.motion_sensor_1')
def detect_motion(entity):
    if entity.state == "on":
        ha.entities['light.light_1'].turn_on()
```

Now we will create a separate function to turn off the light:
```python
def turn_off_light():
    ha.entities['light.light_1'].turn_off()
```

Now we just need to modify our detect_motion() function to call turn_off_light() when there's no longer any motion detected:
```python
@ha.onchange('binary_sensor.motion_sensor_1')
def detect_motion(entity):
    if entity.state == "on":
        ha.entities['light.light_1'].turn_on()
    elif entity.state == "off":
        turn_off_light()
```

Perfect! So here's what we have so far:
1. Motion is detected: Turn light on
2. Motion is not detected: Turn light off

And the resulting code:
```python
from hass import HomeAssistant
ha = HomeAssistant("url:port", "api_authentication_token")

@ha.onchange('binary_sensor.motion_sensor_1')
def detect_motion(entity):
    if entity.state == "on":
        ha.entities['light.light_1'].turn_on()
    elif entity.state == "off":
        turn_off_light()

def turn_off_light():
    ha.entities['light.light_1'].turn_off()
```

So this is great and all, but we probably don't want the lights to turn off immediately when the motion stops. We want to delay our turn_off_light() function, with the option to cancel it if motion is detected again.<br>
We solve this with the @postpone() decorator:
```python
from hass import HomeAssistant
ha = HomeAssistant("url:port", "api_authentication_token")

@ha.onchange('binary_sensor.motion_sensor_1')
def detect_motion(entity):
    if entity.state == "on":
        ha.entities['light.light_1'].turn_on()
        turn_off_light(cancel=True)  # cancel turn_off_lights() when motion is detected
    elif entity.state == "off":
        turn_off_light()

@ha.postpone(60)  # Delays the function by 60 seconds
def turn_off_light():
    ha.entities['light.light_1'].turn_off()
```
Notice we also added turn_off_light(cancel=True). This ensures that the function will not run when it's not supposed to (while motion is detected).

*Note: if turn_off_light() is called again before the 60 seconds is up, the timer is simply reset in order to keep it from running multiple times*

License
----

MIT
