import pyb
from machine import I2C
import cotask
import task_share
# from mlx_cam import MLX_Cam
# from mlx_raw.mlx90640.calibration import NUM_ROWS, NUM_COLS
import motor_driver
import encoder_reader
import clp_controller
import gc
import utime


def process_target(coord, axis):
    if axis:
        cam_dist = coord - NUM_ROWS / 2
        angle = (55 / 2) * (cam_dist / (NUM_ROWS / 2))
    else:
        cam_dist = coord - NUM_COLS / 2
        angle = (35 / 2) * (cam_dist / (NUM_COLS / 2))

    return angle * (16384 / 360)


def get_target_task1(shares):
    start_share, target_x_share, target_y_share, targ_acquired_share,\
        yaw_curr_share, at_yaw_share,pitch_curr_share, at_pitch_share,\
        nerf_motor_share, solenoid_share = shares

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


def motor_yaw_task2(shares):
    start_share, target_x_share, target_y_share, targ_acquired_share,\
        yaw_curr_share, at_yaw_share,pitch_curr_share, at_pitch_share,\
        nerf_motor_share, solenoid_share = shares

    motor_dvr = motor_driver.MotorDriver()
    encoder = encoder_reader.EncoderReader()
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.enable()

    while True:
        if targ_acquired_share & (not at_yaw_share):
            setpoint = target_x_share.get()
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            yaw_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if yaw_curr_share == target_x_share:
                at_yaw_share.put(1)
                motor_dvr.disable()
                print("Yaw angle positioned.")

        yield 0


def motor_pitch_task3(shares):
    start_share, target_x_share, target_y_share, targ_acquired_share,\
        yaw_curr_share, at_yaw_share,pitch_curr_share, at_pitch_share,\
        nerf_motor_share, solenoid_share = shares

    motor_dvr = motor_driver.MotorDriver(
        pyb.Pin.board.PC1, pyb.Pin.board.PA0, pyb.Pin.board.PA1, 5
    )
    encoder = encoder_reader.EncoderReader(
        pyb.Pin.board.PB6, pyb.Pin.board.PB7, 4
    )
    controller = clp_controller.CLPController(Kp=0.01)
    motor_dvr.enable()

    while True:
        print("here")
        if start_share.get():
            motor_dvr.set_setpoint(16384 / 2)
            motor_dvr.set_kp(0.5)
#             motor_dvr.en_pin.high()
            motor_dvr.set_duty_cycle(100)
            
            start_share.put(0)
            print("Turret started")
#         motor_dvr.en_pin.low()
        if targ_acquired_share & (not at_pitch_share):
            setpoint = target_y_share.get()
            controller.set_setpoint(setpoint)
            motor_dvr.set_duty_cycle(
                controller.run(setpoint, encoder.read())
            )
            pitch_curr_share.put(
                controller.motor_positions[len(controller.motor_positions) - 1]
            )

            if pitch_curr_share == target_y_share:
                at_pitch_share.put(1)
                motor_dvr.disable()
                print("Pitch angle positioned.")

        yield 0


def shoot_task4(shares):
    start_share, target_x_share, target_y_share, targ_acquired_share,\
        yaw_curr_share, at_yaw_share,pitch_curr_share, at_pitch_share,\
        nerf_motor_share, solenoid_share = shares

    nerf_motor_pin = pyb.Pin(pyb.Pin.board.PC2, pyb.Pin.OUT_PP)
    solenoid_pin = pyb.Pin(pyb.Pin.board.PC3, pyb.Pin.OUT_PP)

    if targ_acquired_share.get() & at_yaw_share.get() & at_pitch_share.get():
        nerf_motor_pin.high()
        utime.sleep_ms(2000)
#         solenoid_pin.high()
#         utime.sleep_ms(1000)
        nerf_motor_pin.low()
#         solenoid_pin.low()
        print("motor on -- Shot fired.")


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

    shares = start_share, target_x_share, target_y_share, targ_acquired_share, \
        yaw_curr_share, at_yaw_share, \
        pitch_curr_share, at_pitch_share, \
        nerf_motor_share, solenoid_share

    start_share.put(1)
    # target_x_share.put()
    # target_y_share.put()
    targ_acquired_share.put(0)
    # yaw_curr_share.put()
    at_yaw_share.put(0)
    # pitch_curr_share.put()
    at_pitch_share.put(0)
    nerf_motor_share.put(0)
    solenoid_share.put(0)

    # Move the motors to a set home position? Rotate 180deg?

    # t1_get_target = cotask.Task(
    #     get_target_task1, name="Task1", priority=1, shares=shares
    #     )
    # t2_motor_yaw = cotask.Task(
    #     motor_yaw_task2, name="Task2", priority=2, shares=shares
    #     )
    t3_motor_pitch = cotask.Task(
        motor_pitch_task3, name="Task3", priority=2, period=20, shares=shares
        )
#     t4_shoot = cotask.Task(
#         shoot_task4, name="Task4", priority=3, shares=shares
#         )

    # cotask.task_list.append(t1_get_target)
    # cotask.task_list.append(t2_motor_yaw)
    cotask.task_list.append(t3_motor_pitch)
#     cotask.task_list.append(t4_shoot)

    gc.collect()

    while True:
        try:
            cotask.task_list.pri_sched()
        except KeyboardInterrupt:
            break
    print('Done.')
