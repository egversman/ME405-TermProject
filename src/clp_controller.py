"""! @file clp_controller.py
   This file implements a basic, general closed loop proportional controller 
   class. This class is used to control a motor in the ME 405 lab.
"""
import pyb

class CLPController:
    """! 
    closed loop proportional controller class 
    """
    def __init__ (self, Kp = 1, setpoint = 0):
        """!
        Initialize the closed loop proportional controller with Kp and setpoint.
        @param Kp Proportional gain value (default value is 1)
        @param setpoint Setpoint for the controller (default value is 0)
        """
        self.Kp = Kp
        self.setpoint = setpoint
        
        self.times = list()
        self.motor_positions = list()
        
    def __repr__(self):
        return f'CLPController(Kp={self.Kp}, init_setpoint={self.init_setpoint})'
    
    def __str__(self):
        return f'Closed-loop proportional controller:\n\tKp={self.Kp} and\n\tinit_setpoint={self.init_setpoint}'

    def run (self, setpoint, meas_output):
        """!
        Run the closed loop proportional controller.
        @param  setpoint The setpoint for the controller
        @param  meas_output The measured output value
        @return The control output calculated by the controller
        """
        self.motor_positions.append(meas_output)
        return self.Kp * (setpoint - meas_output)
    
    def set_setpoint(self, new_setpoint):
        """!
        Set a new setpoint for the controller.
        @param new_setpoint The new setpoint value
        """
        self.setpoint = new_setpoint
    
    def set_Kp(self, new_Kp):
        """!
        Set a new value for Kp.
        @param new_Kp The new value for the proportional gain
        """
        self.Kp = new_Kp
        
    def print_response(self):
        """!
        Print the response of the controller.
        """
        if not self.times or not self.motor_positions:
            print('No data available.')
            return
        
        for time, position in zip(self.times, self.motor_positions):
            print(f'{time}, {position}')
        
if __name__ == "__main__":
    pass
    