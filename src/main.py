import pyb
from machine import I2C
import cotask
import task_share
from mlx_cam import MLX_Cam
import motor_driver
import encoder_reader
import clp_controller
import gc
import utime


def process_target(coord):
    # function to process target coordinate into encoder ticks?
    return coord

def get_target_task1(shares):
    target_x_share, target_y_share, targ_acquired_share, yaw_curr_share, at_yaw_share,\
        pitch_curr_share, at_pitch_share, nerf_motor_share, solenoid_share = shares

    i2c_bus = I2C(1)
    camera = MLX_Cam(i2c_bus)

    while True:
        if not targ_acquired_share:
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
                        sum(cam_data[row + i][col + j] for j in range(block_size)) for i in range(block_size))
                    if curr_sum > max_sum:
                        row_idx, col_idx = row, col
                        max_sum = curr_sum
            mid_row = row_idx + block_size // 2
            mid_col = col_idx + block_size // 2

            target_y = process_target(mid_row)
            target_x = process_target(mid_col)

            target_x_share.put(target_x)
            target_y_share.put(target_y)
            targ_acquired_share.put(1)
            # print(mid_row, mid_col)

        yield 0


def motor_yaw_task2(shares):
    target_x_share, target_y_share, targ_acquired_share, yaw_curr_share, at_yaw_share,\
        pitch_curr_share, at_pitch_share, nerf_motor_share, solenoid_share = shares

    motor_dvr = motor_driver.MotorDriver()
    encoder = encoder_reader.EncoderReader()
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.en_pin.high()

    while True:
        if (targ_acquired_share) & (not at_yaw_share):
            setpoint = target_x_share.get()  # Must process target coordinates somehow?
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            yaw_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if yaw_curr_share == target_x_share:
                at_yaw_share.put(1)

        yield 0


def motor_pitch_task3(shares):
    target_x_share, target_y_share, targ_acquired_share, yaw_curr_share, at_yaw_share,\
        pitch_curr_share, at_pitch_share, nerf_motor_share, solenoid_share = shares

    motor_dvr = motor_driver.MotorDriver(
        pyb.Pin.board.PC1, pyb.Pin.board.PA0, pyb.Pin.board.PA1, 5
    )
    encoder = encoder_reader.EncoderReader(
        pyb.Pin.board.PB6, pyb.Pin.board.PB7, 4
    )
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.en_pin.high()

    while True:
        if (targ_acquired_share) & (at_yaw_share) & (not at_pitch_share):
            setpoint = target_y_share.get()  # Must process target coordinates somehow?
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            pitch_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if pitch_curr_share == target_y_share:
                at_pitch_share.put(1)

        yield 0


def shoot_task4(shares):
    target_x_share, target_y_share, targ_acquired_share, yaw_curr_share, at_yaw_share,\
        pitch_curr_share, at_pitch_share, nerf_motor_share, solenoid_share = shares

    nerf_motor_pin = pyb.Pin(pyb.Pin.board.PC2, pyb.Pin.OUT_PP)
    solenoid_pin = pyb.Pin(pyb.Pin.board.PC3, pyb.Pin.OUT_PP)

    if targ_acquired_share & at_yaw_share & at_pitch_share:
        nerf_motor_pin.high()
        utime.delay(200)
        solenoid_pin.high()
        utime.delay(200)
        nerf_motor_pin.low()
        solenoid_pin.low()


if __name__ == "__main__":
    target_x_share = task_share.Share('f', thread_protect=True, name="target_x")
    target_y_share = task_share.Share('f', thread_protect=True, name="target_y")
    targ_acquired_share = task_share.Share('b', thread_protect=True, name="targ_acquired")
    yaw_curr_share = task_share.Share('f', thread_protect=True, name="yaw_curr")
    pitch_curr_share = task_share.Share('f', thread_protect=True, name="pitch_curr")
    at_yaw_share = task_share.Share('b', thread_protect=True, name="nerf_motor")
    at_pitch_share = task_share.Share('b', thread_protect=True, name="solenoid")
    nerf_motor_share = task_share.Share('b', thread_protect=True, name="nerf_motor")
    solenoid_share = task_share.Share('b', thread_protect=True, name="solenoid")

    shares = target_x_share, target_y_share, targ_acquired_share, \
        yaw_curr_share, at_yaw_share, \
        pitch_curr_share, at_pitch_share, \
        nerf_motor_share, solenoid_share

    # target_x_share.put()
    # target_y_share.put()
    targ_acquired_share.put(0)
    # yaw_curr_share.put()
    at_yaw_share.put(0)
    # pitch_curr_share.put()
    at_pitch_share.put(0)
    nerf_motor_share.put(0)
    solenoid_share.put(0)

    # Move the motors such that the accelerometer is zeroed?

    t1_get_target = cotask.Task(get_target_task1, name="Task1", priority=3, shares=shares)
    t2_motor_yaw = cotask.Task(motor_yaw_task2, name="Task2", priority=4, shares=shares)
    t3_motor_pitch = cotask.Task(motor_pitch_task3, name="Task3", priority=4, shares=shares)
    t4_shoot = cotask.Task(shoot_task4, name="Task4", priority=2, shares=shares)

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
    print('Done')
