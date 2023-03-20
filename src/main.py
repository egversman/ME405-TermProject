"""! @file main.py
    This file implements the nerf turret term project for ME 405. For this 
    project, four tasks and one helper function are defined. In the file main,
    the system is configured and set up to compete in a dual as defined by the 
    term project guidelines.
"""

import pyb
from machine import I2C
import cotask
import task_share
from mlx_cam import MLX_Cam
from mlx_raw.mlx90640.calibration import NUM_ROWS, NUM_COLS
import motor_driver
import encoder_reader
import clp_controller
import gc
import utime


def process_target(coord, axis):
    """!
        This helper function, used by 'get_target_task1,' converts an x or y
        coordinate from the thermal camera into a distance in encoder ticks. 
        Task 1 will call this function twice upon finding the optimal coordinate 
        in the csv output of the thermal camera. This conversion is based on the 
        55 by 35 degree field of view of the thermal camera and the 16384 
        encoder ticks in a 360 degree rotation.
        @param  coord  An x or y coordinate from the thermal camera.
        @param  axis  A boolean representing whether the given coord is an x or 
                y coordinate. True is for x coordinates and False for y.
        @return A distance in encoder ticks that either the pitch or yaw motor 
                will need to rotate.
        """
    if axis:
        cam_dist = coord - NUM_ROWS / 2
        angle = (55 / 2) * (cam_dist / (NUM_ROWS / 2))
    else:
        cam_dist = coord - NUM_COLS / 2
        angle = (35 / 2) * (cam_dist / (NUM_COLS / 2))

    return angle * (16384 / 360)


def get_target_task1(shares):
    """!
        This task acquires the optimal target from the thermal camera. First, 
        the csv data from the thermal camera is parsed. Then an algorithm is 
        implemented to determine the best target. This algorithm divides the 
        output grid from the camera into 5 by 5 blocks and calculates the total
        sum of each block. The optimal target is considered to be the center 
        coordinate of the block with the greatest sum. This coordinate is 
        processed into encoder ticks, which are added to the relevent shares. 
        Lastly, a flag is set indicating that a target has been acquired.
        @param  shares  This task requires access to the 'target_x,' 'target_y,'
                and 'targ_acquired' shares, to which it will write values.
        """
    target_x_share, target_y_share, targ_acquired_share, = shares

    i2c_bus = I2C(1)
    camera = MLX_Cam(i2c_bus)

    while True:
        if not targ_acquired_share.get():
            cam_data = []
            image = camera.get_image()
            for line in camera.get_csv(image, limits=(0, 99)):
                row_data = list(map(int, line.split(',')))
                cam_data.append(row_data)

            max_sum = 0
            block_size = 5
            row_idx, col_idx = 0, 0
            for row in range(len(cam_data) - block_size + 1):
                for col in range(len(cam_data[0]) - block_size + 1):
                    curr_sum = sum(
                        sum(cam_data[row+i][col+j] for j in range(block_size)
                            ) for i in range(block_size)
                        )
                    if curr_sum > max_sum:
                        row_idx, col_idx = row, col
                        max_sum = curr_sum
            mid_row = row_idx + block_size // 2
            mid_col = col_idx + block_size // 2

            dist_y = process_target(mid_row, False)
            dist_x = process_target(mid_col, True)

            target_x_share.put(dist_x)
            target_y_share.put(dist_y)
            targ_acquired_share.put(1)
            print("Target acquired.")

        yield 0


def motor_pitch_task2(shares):
    """!
        This task controls the pitch motor of the turret. The task uses the 
        the class default pin parameters to initialize motor driver and encoder
        objects, and also initializes a proportional controller object. If a 
        target has been acquired and the pitch has not yet reached the target,
        the motor will rotate into position. Once the pitch has reached its 
        target, a 1 is written to the 'at_pitch' share and the motor is disbled.
        @param  shares  This task requires access to the 'target_x,' 
                'targ_acquired,' 'pitch_curr', and 'at_pitch' shares.
        """
    target_x_share, targ_acquired_share, pitch_curr_share, at_pitch_share,  = shares

    motor_dvr = motor_driver.MotorDriver()
    encoder = encoder_reader.EncoderReader()
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.enable()

    while True:
        if targ_acquired_share.get() & (not at_pitch_share.get()):
            setpoint = target_x_share.get()
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            yaw_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if abs(pitch_curr_share.get() - target_x_share.get()) < 5:
                at_pitch_share.put(1)
                motor_dvr.disable()
                print("Pitch angle positioned.")

        yield 0


def motor_yaw_task3(shares):
    """!
        This task controls the yaw motor of the turret. The task initializes 
        motor driver, encoder and proportional controller objects. If the turret
        is started for the first time, the yaw motor will rotate 180 degrees. If ]
        a target has been acquired and the yaw has not yet reached the target, 
        the motor will rotate into position. Once the yaw has reached its 
        target, a 1 is written to the 'at_yaw' share and the motor is disbled.
        @param  shares  This task requires access to the 'start,' 'target_y,' 
                'targ_acquired,' 'yaw_curr', and 'at_yaw' shares.
        """
    start_share, target_y_share, targ_acquired_share, yaw_curr_share, \
        at_yaw_share, = shares

    motor_dvr = motor_driver.MotorDriver(
        pyb.Pin.board.PC1, pyb.Pin.board.PA0, pyb.Pin.board.PA1, 5
    )
    encoder = encoder_reader.EncoderReader(
        pyb.Pin.board.PB6, pyb.Pin.board.PB7, 4
    )
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.enable()

    while True:
        if start_share.get():
            controller.set_setpoint(16384 / 2)
#             controller.set_Kp(0.5)
            motor_dvr.set_duty_cycle(-100)
            utime.sleep_ms(1100)
            motor_dvr.en_pin.low()
            motor_dvr.set_duty_cycle(0)
            
            start_share.put(0)
            print("Turret started")
        if targ_acquired_share.get() & (not at_yaw_share.get()):
            setpoint = target_y_share.get()
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            pitch_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if abs(yaw_curr_share.get() - target_x_share.get()) < 5:
                at_yaw_share.put(1)
                motor_dvr.disable()
                print("Yaw angle positioned.")

        yield 0


def shoot_task4(shares):
    """!
        This task controls the triggering of the turret. Pins for the internal 
        nerf trigger motor and the solonoid are initialized. Then, if a target
        has been acquired and both pitch and yaw motors are positioned 
        appropriately, the internal motor will turn on the solonoid will extend
        after a 0.2 second delay. Then, after another 0.5 second delay, the nerf 
        motor is turned off and the solonoid plunger is retracted.
        @param  shares  This task requires access to the 'targ_acquired,' 
                'at_yaw', and 'at_pitch' shares.
        """
    targ_acquired_share, at_yaw_share, at_pitch_share, = shares

    nerf_motor_pin = pyb.Pin(pyb.Pin.board.PC2, pyb.Pin.OUT_PP)
    solenoid_pin = pyb.Pin(pyb.Pin.board.PC3, pyb.Pin.OUT_PP)

    if targ_acquired_share.get() & at_yaw_share.get() & at_pitch_share.get():
        nerf_motor_pin.high()
        utime.sleep_ms(200)
        solenoid_pin.high()
        utime.sleep_ms(500)
        nerf_motor_pin.low()
        solenoid_pin.low()
        print("Shot fired.")


if __name__ == "__main__":
    start_share = task_share.Share('b', name="start")
    target_x_share = task_share.Share('f', name="target_x")
    target_y_share = task_share.Share('f', name="target_y")
    targ_acquired_share = task_share.Share('b', name="targ_acquired")
    yaw_curr_share = task_share.Share('f', name="yaw_curr")
    pitch_curr_share = task_share.Share('f', name="pitch_curr")
    at_yaw_share = task_share.Share('b', name="nerf_motor")
    at_pitch_share = task_share.Share('b', name="solenoid")
    nerf_motor_share = task_share.Share('b', name="nerf_motor")
    solenoid_share = task_share.Share('b', name="solenoid")

    shares = [
              start_share, 
              target_x_share, 
              target_y_share, 
              targ_acquired_share,
              yaw_curr_share, 
              at_yaw_share,
              pitch_curr_share, 
              at_pitch_share,
              nerf_motor_share, 
              solenoid_share
              ]

    start_share.put(1)
    target_x_share.put(0)
    target_y_share.put(0)
    targ_acquired_share.put(0)
    yaw_curr_share.put(0)
    at_yaw_share.put(0)
    pitch_curr_share.put(0)
    at_pitch_share.put(0)
    nerf_motor_share.put(0)
    solenoid_share.put(0)

    t1_get_target = cotask.Task(
        get_target_task1, name="Task1", priority=1, period=20, shares=shares
        )
    t2_motor_yaw = cotask.Task(
        motor_pitch_task2, name="Task2", priority=2, period=10, shares=shares
        )
    t3_motor_pitch = cotask.Task(
        motor_yaw_task3, name="Task3", priority=2, period=20, shares=shares
        )
    t4_shoot = cotask.Task(
        shoot_task4, name="Task4", priority=3, period=20, shares=shares
        )

    cotask.task_list.append(t1_get_target)
    cotask.task_list.append(t2_motor_yaw)
    cotask.task_list.append(t3_motor_pitch)
    cotask.task_list.append(t4_shoot)

    gc.collect()

    while True:
        try:
            cotask.task_list.pri_sched()
        except KeyboardInterrupt:
            break
    print("Done.")
