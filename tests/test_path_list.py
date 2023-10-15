import gcoordinator as gc
import numpy as np


full_object = []
for layer in range(100):
    walls = []
    for i in range(5):
        arg = np.linspace(0, 2*np.pi, 5)
        x = 10 * np.cos(arg) + i * 10
        y = 10 * np.sin(arg)
        z = np.full_like(x, layer * 0.1)
        wall = gc.Path(x, y, z)
        walls.append(wall)
    walls = gc.PathList(walls)
    if layer > 50:
        walls.print_speed = 200

    full_object.append(walls)

gc.show(full_object)


gcode = gc.GCode(full_object)
gcode.start_gcode("/Users/taniguchitomohiro/Documents/default_gcode/start_gcode.txt")
gcode.end_gcode("/Users/taniguchitomohiro/Documents/default_gcode/end_gcode.txt")
gcode.save('test.gcode')
