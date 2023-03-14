"""! @file encoder_reader.py
    This file contains an implementation of an encoder reader class. The file 
    main includes a test to make sure it works properly. 
"""
import pyb

class EncoderReader:
    """! 
    This class implements an encoder reader for the ME 405 lab kit.
    """

    def __init__ (self, pin1 = pyb.Pin.board.PC6, pin2 = pyb.Pin.board.PC7,
                  tim_num: int = 8):
        """!
        Initializes an EncoderReader object.
        @param pin1  First pin connecting the encoder to the motor.
        @param pin2  Second pin connecting the encoder to the motor.
        @param timer Selected controller timer to use for the encoder. The timer
               reads pulses from the encoder and counts the distance and 
               direction of motion.
        """
        
        #this is going to assume, for now, that we're only going to use/input 
        # the pins and timer that we know works/have already used for the 
        # encoder reader
        self.pin1 = pyb.Pin(pin1, pyb.Pin.IN) #change out_pp to in
        self.pin2 = pyb.Pin(pin2, pyb.Pin.IN)
        self.timer = pyb.Timer(tim_num, prescaler = 0, period = 0xFFFF)

        # self.pin1 = pyb.Pin(..)
        self.timer.channel(1, pyb.Timer.ENC_AB, pin=self.pin1) 
        self.timer.channel(2, pyb.Timer.ENC_AB, pin=self.pin2)
        
        self.curr_pos = 0
        self.prev_count = 0
        
    def __repr__(self):
        """!
        Return a string representation of the EncoderReader object.
        """
        return f"EncoderReader(pin1={self.pin1}, pin2={self.pin2}, timer={self.timer})"
    
    def __str__(self):
        """!
        Return a string representation of the EncoderReader object for a user-friendly output.
        """
        return f"EncoderReader\n\tpin1 = {self.pin1},\n\tpin2 = {self.pin2},\n\ttimer = {self.timer}, and\n\tcurrent position = {self.curr_pos}"

    def read (self):
        """!
        Returns the current position of the motor.
        """
    
        curr_count = self.timer.counter()
        difference = curr_count - self.prev_count
        
        if (difference) > (32768):
            difference -= 65535
            
        if (difference) < -(32768):
            difference += 65535
        
        self.curr_pos += difference
        self.prev_count = curr_count
        
        return self.curr_pos
    
    def zero (self):
        """!
        Reads the current position of the motor and sets the count to 0 at that 
        current position.
        """
        self.prev_count = self.timer.counter()
        self.curr_pos = 0
            
if __name__ == "__main__":
    '''
    Test encoder class: Turn the motor by hand and run the motor under power. 
    Does the code return reasonable results when the motor moves a revolution or 
    two one way, then back? Does it work when the motor is moving quickly? The 
    code must work if the timer overflows (counts above 216 − 1) or underflows 
    (counts below zero).
    '''
    import motor_driver
    moe = motor_driver.MotorDriver (pyb.Pin.board.PA10, pyb.Pin.board.PB4, pyb.Pin.board.PB5, 3)
    enc = EncoderReader(pyb.Pin.board.PC6, pyb.Pin.board.PC7, 8)
    moe.set_duty_cycle(100)
    moe.enable()
    
    
    moe2 = motor_driver.MotorDriver(pyb.Pin.board.PC1, pyb.Pin.board.PA0, pyb.Pin.board.PA1, 5)
    enc2 = EncoderReader(pyb.Pin.board.PB6, pyb.Pin.board.PB7, 4)
    moe2.set_duty_cycle(-100)
    moe2.enable()
    
    
    while True:
        print(enc.read(), enc2.read())
        
    # encoder flips to positive when negative??
    # spin encoder with hand to see if it counts


