#!/usr/bin/env python
import numpy
import rospy
import mavros
from geometry_msgs.msg import PoseStamped,Vector3
from mavros_msgs.msg import State,AttitudeTarget
from mavros_msgs.srv import CommandBool, SetMode

from std_msgs.msg import Bool,Float32
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
import tf.transformations
import sys, time
import PID

import timeit

from argparse import ArgumentParser

from pyquaternion import Quaternion

import roslaunch
class test:
	def __init__(self):
		self.vicon_cb_flag = False
		self.state_cb_flag = False
		self.pos_sp_cb_flag = False

		self.P = rospy.get_param('/attitude_thrust_publisher/position_controller_P')
		self.I = rospy.get_param('/attitude_thrust_publisher/position_controller_I')
		self.D = rospy.get_param('/attitude_thrust_publisher/position_controller_D')
		self.roll_pid = PID.PID(self.P, self.I, self.D)
		self.pitch_pid = PID.PID(self.P, self.I, self.D)

		#X axis of the vicon system should alwasy be aligned with the front of the quad

		#Rate init
		#DECIDE ON PUBLISHING RATE
		self.rate = rospy.Rate(20.0) # MUST be more then 2Hz

		self.attitude_target_pub = rospy.Publisher("/px4_quad_controllers/rpy_setpoint", PoseStamped, queue_size=10)

		#ADD SUBSCRIBER FOR VICON DATA
		vicon_sub = rospy.Subscriber("/intel_aero_quad/odom", Odometry, self.vicon_subscriber_callback)

		state_sub = rospy.Subscriber("/mavros/state", State, self.state_subscriber_callback)
		pos_sp_sub = rospy.Subscriber("/px4_quad_controllers/pos_sp", PoseStamped, self.pos_sp_subscriber_callback)

		
		while not rospy.is_shutdown():
		
			if(self.vicon_cb_flag==True and self.state_cb_flag==True):
				#Update PID
				self.P = rospy.get_param('/attitude_thrust_publisher/position_controller_P')
				self.I = rospy.get_param('/attitude_thrust_publisher/position_controller_I')
				self.D = rospy.get_param('/attitude_thrust_publisher/position_controller_D')
				self.roll_pid.setKp(self.P)
				self.roll_pid.setKi(self.I)
				self.roll_pid.setKd(self.D)
				self.pitch_pid.setKp(self.P)
				self.pitch_pid.setKi(self.I)
				self.pitch_pid.setKd(self.D)
				
				#Update setpoint
				if(self.pos_sp_cb_flag==False):
					self.pos_y_sp = rospy.get_param('/attitude_thrust_publisher/pos_y_sp')
					self.pos_x_sp = rospy.get_param('/attitude_thrust_publisher/pos_x_sp')
				else:
					self.pos_y_sp = self.pos_sp_y_traj_gen
					self.pos_x_sp = self.pos_sp_x_traj_gen
				self.roll_pid.SetPoint = self.pos_y_sp
				self.pitch_pid.SetPoint = self.pos_x_sp
				if(self.current_state=='OFFBOARD'):
					self.roll_pid.update(self.vicon_y_pos)
					self.pitch_pid.update(self.vicon_x_pos)
				else:
					self.roll_pid.clear()
					self.pitch_pid.clear()
				
				roll_output = -self.roll_pid.output
				pitch_output = -self.pitch_pid.output
				target_attitude = PoseStamped()
				target_attitude.header.frame_id = "home"
				target_attitude.header.stamp = rospy.Time.now()
				target_attitude.pose.position.x = roll_output
				target_attitude.pose.position.y = pitch_output

				self.attitude_target_pub.publish(target_attitude)

			self.rate.sleep()

	def vicon_subscriber_callback(self,state):
		self.vicon_x_pos = state.pose.pose.position.x
		self.vicon_y_pos = state.pose.pose.position.y
		self.vicon_cb_flag = True

	def pos_sp_subscriber_callback(self,state):
		self.pos_sp_x_traj_gen = state.pose.position.x
		self.pos_sp_y_traj_gen = state.pose.position.y
		self.pos_sp_cb_flag = True

	#Current state subscriber
	def state_subscriber_callback(self,state):
		self.current_state = state.mode
		self.state_cb_flag = True

		self.rate.sleep()
def main(args):
	rospy.init_node('offb_node', anonymous=True)
	ic=test()

	try:
		rospy.spin()
	except rospy.ROSInterruptException:
		pass

if __name__ == '__main__':
	main(sys.argv)
