# v154 fresh-start comparison

Only initial attitude P/D change from v153 to the actually exercised trial86
values P2.75/D0.050. I0.60/speedP0.25, native wheel damping, velocity backend,
frame timestamps, position origin/return, integral gate, duration1800s and all
actuator/attitude/temperature/travel/communication guards are unchanged.

Trial86 raw SHA256:
cf15f9f534de0f15e9896f8f4e8b4699138e8dd581d85c816e0f2a2c51b0d381.
The trial stopped at921.519s on one8.139872ms feedback response against the
original8ms deadline, both final mode0 verified; max temperature71C.
The operator confirmed unsupported quiet and two light pushes. Finite
stationary windows exist, but fast/repeatable startup or post-push settling
has not been established. Gain-history and uncertain exact contact times
prevent treating within-run coincidences as identified actuator dynamics.

Suspended native-rate repeat used the pre-existing v112 diagnostic, four
phases each<=2s/target0.20rad/s/NET0.08Nm/speed0.6rad/s/travel20deg/temp70C.
The operator eventually observed visually continuous, basically smooth
rotation. Rotor feedback was continuous on the sampled0.4-1.2s plateaus;
independent output-angle scatter was larger. Neither establishes loaded
smoothness, accuracy, actual backlash or a need to replace the motors.

The new entry is inert without its explicit start flag. A fresh grounded
upright setup, current read checks and deliberate local unlock remain
necessary. No automatic start or fault rearm. Physical outcome NOT_TESTED.
