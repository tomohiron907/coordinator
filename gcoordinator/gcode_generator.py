import os
import json
import numpy as np
from gcoordinator.settings                   import get_default_settings, load_settings
from gcoordinator.path_generator             import Path
from gcoordinator.path_generator             import flatten_path_list
from gcoordinator.utils.coords               import get_distances_between_coords
from gcoordinator.kinematics.kin_bed_rotate  import BedRotate
from gcoordinator.kinematics.kin_cartesian   import Cartesian
from gcoordinator.kinematics.kin_bed_tilt_bc import BedTiltBC
from gcoordinator.kinematics.kin_nozzle_tilt import NozzleTilt
from gcoordinator.settings                   import template_settings

class GCode:
    """
    Represents a G-code generator for 3D printing.

    Attributes:
        full_object (list): A list of `Path` objects representing the paths to be printed.
        settings_path (str): The path to the settings pickle file.
        default_settings (dict): A dictionary containing the default settings.
        gcode (file object): The file object for the generated G-code.
        start_gcode_path (str): The path to the file containing the start G-code.
        start_gcode_txt (str): The text of the start G-code.
        end_gcode_path (str): The path to the file containing the end G-code.
        end_gcode_txt (str): The text of the end G-code.

    Methods:
        __init__(self, full_object:list) -> None: Initializes a new `GCode` object with the given `full_object`.
        save(self, file_path:str) -> None: Saves the generated G-code to a file at the specified file path.
        generate_gcode(self) -> None: Generates G-code instructions for the full object.
        print_path(self, path:Path) -> None: Generates G-code instructions for printing a given path.
        travel_from_path_to_path(self, curr_path:Path, next_path:Path) -> None: Generates G-code instructions for traveling from the end of `curr_path` to the start of `next_path`.
        travel_to_first_point(self, first_path:Path) -> None: Generates G-code instructions for traveling to the first point of the first path in the full object.
        set_initial_settings(self) -> str: Generates G-code commands to set the initial printer settings.
        apply_path_settings(self, path) -> None: Generate G-code commands to apply the settings of the given `path` object.
        start_gcode(self, file_path) -> None: Sets the path to the start G-code file.
        end_gcode(self, file_path) -> None: Sets the file path for the end G-code script.
        apply_defaults_to_instances(self, full_object, default_settings) -> None: Applies the default settings to the given `full_object`.
    """

    def __init__(self, full_object: list) -> None:
        """
        Initializes a new `GCode` object with the given `full_object`.

        Args:
            full_object (list): A list of `Path` objects representing the paths to be printed.

        Returns:
            None
        """
        self.full_object = flatten_path_list(full_object) # list of Path objects
        
        try:
            self.settings_path = '.temp_config.json'
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
            
        except:
            self.settings = template_settings # gcoordinator/settings.py

        self.default_settings = get_default_settings(self.settings)
        self.apply_defaults_to_instances(self.full_object, self.default_settings)

        self.gcode            = None              # gcode file object
        self.start_gcode_path = 'start_gcode.txt'
        self.start_gcode_txt  = ''
        self.end_gcode_path   = 'end_gcode.txt'
        self.end_gcode_txt    = ''

    def save(self, file_path:str) -> None:
        """
        Saves the generated G-code to a file at the specified file path.

        Args:
            file_path (str): The path to the file where the G-code will be saved.

        Returns:
            None.
        """
        self.gcode = open(file_path, 'w', encoding='utf-8')
        
        with open(self.start_gcode_path, 'r') as f:
            self.start_gcode_txt = f.read()
        self.gcode.write(self.start_gcode_txt)
        
        self.set_initial_settings()
        self.generate_gcode()
        
        with open(self.end_gcode_path, 'r') as f:
            self.end_gcode_txt = f.read()   
        self.gcode.write(self.end_gcode_txt)
        
        self.gcode.close()
        if os.path.exists(".temp_config.json"):
            # remove the temporary config file
            os.remove(".temp_config.json")
        else:
            print(".temp_config.json does not exist")

    def generate_gcode(self) -> None:
        """
        Generates G-code instructions for the full object by iterating over its paths and calling
        the `apply_path_settings` and `print_path` methods for each path.

        Returns:
            None
        """
        self.travel_to_first_point(self.full_object[0])
        for i in range(len(self.full_object)):
            curr_path = self.full_object[i]
            self.apply_path_settings(curr_path)
            self.print_path(curr_path)
            if i < len(self.full_object)-1:
                next_path = self.full_object[i+1]
                self.travel_from_path_to_path(curr_path, next_path)
            else:
                pass

    def print_path(self, path:Path) -> None:
        """
        Generates G-code instructions for printing a given path.

        Args:
            path (Path): The path to print.

        Returns:
            None

        Raises:
            None
        """
        
        if path.kinematics == 'Cartesian':
            txt = Cartesian.generate_gcode_of_path(path)

        elif path.kinematics == 'NozzleTilt':
            NozzleTilt.load_settings()
            txt = NozzleTilt.generate_gcode_of_path(path)
        
        elif path.kinematics == 'BedTiltBC':
            BedTiltBC.load_settings()
            txt = BedTiltBC.generate_gcode_of_path(path)
        
        elif path.kinematics == 'BedRotate':
            BedRotate.load_settings()
            txt = BedRotate.generate_gcode_of_path(path)
            

        self.gcode.write(txt)

    def travel_from_path_to_path(self, curr_path:Path, next_path:Path) -> None:
        """
        Generates G-code instructions for traveling from the end of `curr_path` to the start of `next_path`.

        Args:
            curr_path (Path): The path to travel from.
            next_path (Path): The path to travel to.

        Returns:
            None

        Raises:
            None
        """
        txt = ''
        txt += f'G91\n'

        if curr_path.retraction:
            txt += f'G1 E{-curr_path.retraction_distance}\n'
        
        if curr_path.z_hop:
            txt += f'G0 Z{curr_path.z_hop_distance}\n'
        
        # travel to the start of the nextent path
        travel_x = next_path.x[0] - curr_path.x[-1]
        travel_y = next_path.y[0] - curr_path.y[-1]
        travel_z = next_path.z[0] - curr_path.z[-1]
        txt += f'G0 F{next_path.travel_speed} '
        txt += f'X{travel_x} '
        txt += f'Y{travel_y} '
        txt += f'Z{travel_z}\n'

        if curr_path.z_hop:
            txt += f'G0 Z{-curr_path.z_hop_distance}\n'
        
        if curr_path.retraction:
            txt += f'G1 E{curr_path.unretraction_distance}\n'
        
        # In some 3D printers, such as Bambulab, when absolute coordinates are specified with the G90 command, 
        # the E value is also specified as an absolute amount at the same time, 
        # so the M83 command is used to specify the extrusion amount as relative. 
        # Will be rewritten to program using M82 absolute extrusion.
        txt += f'G90 \nM83 \n'
        self.gcode.write(txt)

    def travel_to_first_point(self, first_path:Path) -> None:
        """
        Generates G-code instructions for traveling to the first point of the first path in the full object.

        Args:
            first_path (Path): The first path in the full object.

        Returns:
            None

        Raises:
            None
        """
        txt = ''
        txt += f'G1 F{first_path.travel_speed} '
        txt += f'X{first_path.x[0]+first_path.x_origin} '
        txt += f'Y{first_path.y[0]+first_path.y_origin} '
        txt += f'Z{first_path.z[0]}\n'
        self.gcode.write(txt)

    def set_initial_settings(self) -> str:
        """
        Generates G-code commands to set the initial printer settings, such as bed and nozzle temperature, extrusion mode,
        and fan speed, based on the values defined in the `print_settings` module.

        Returns:
            str: A string containing the G-code commands to set the initial printer settings.
        """
        txt = '\n'
        txt += f'M140 S{self.default_settings["bed_temperature"]} \n'
        txt += f'M190 S{self.default_settings["bed_temperature"]} \n'
        txt += f'M104 S{self.default_settings["nozzle_temperature"]} \n'
        txt += f'M109 S{self.default_settings["nozzle_temperature"]} \n'
        txt += f'M106 S{self.default_settings["fan_speed"]} \n'
        txt += f'M83 ;relative extrusion mode \n'
        self.gcode.write(txt)
    
    def apply_path_settings(self, path):
        """
        Generate G-code commands to apply the settings of the given `path` object.
        The method returns a string containing the G-code commands that should be
        sent to the printer to apply the settings of the path.
        
        :param path: a `Path` object containing the settings to apply.
        :type path: Path
        :return: a string containing the G-code commands to apply the settings.
        :rtype: str
        """
        txt = ''
        if path.nozzle_temperature != self.default_settings['nozzle_temperature']:
            txt += f'M104 S{path.nozzle_temperature} \n'
        if path.bed_temperature != self.default_settings['bed_temperature']:
            txt += f'M140 S{path.bed_temperature} \n'
        if path.fan_speed != self.default_settings['fan_speed']:
            txt += f'M106 S{path.fan_speed} \n'
        self.gcode.write(txt)

    def start_gcode(self, file_path):
        """
        Sets the path to the start G-code file.
    
        Args:
            file_path (str): The path to the start G-code file.

        Returns:
            None
        """
        self.start_gcode_path = file_path
        

    def end_gcode(self, file_path):
        """
        Sets the file path for the end G-code script.

        Args:
            file_path (str): The file path for the end G-code script.

        Returns:
            None
        """
        self.end_gcode_path = file_path

    def extrusion_calculator(self, path):
        """
        Calculates the extrusion required for a given path.

        Args:
            path (Path): The path for which to calculate the extrusion.

        Returns:
            numpy.ndarray: An array of extrusion values, one for each segment of the path.

        Raises:
            None.
        """
        coords = path.coords
        distances = get_distances_between_coords(coords)
        extrusion = np.zeros(len(distances))
        for i, distance in enumerate(distances):
            # Calculate the extrusion for each distance
            # for more details, see formula 3 in the following paper:
            # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7600913/
            numerator    = 4 * path.nozzle_diameter * path.layer_height * distance
            denominator  = np.pi * path.filament_diameter**2
            extrusion[i] = numerator / denominator * path.extrusion_multiplier
        
        return extrusion
    
    
    def apply_defaults_to_instances(self, full_object, default_settings):
            """
            Applies default settings to instances of a given object.

            Args:
                full_object (list): A list of instances of the object to apply default settings to.
                default_settings (dict): A dictionary of default settings to apply to the instances.

            Returns:
                None
            """
            for path in full_object:
                for key, value in default_settings.items():
                    if getattr(path, key) is None:
                        setattr(path, key, value)

