# -*- coding: utf-8 -*-
import rospy
import forklift_server.msg
from enum import Enum
from PBVS_Action_differential import Action
# from forklift_msg.msg import meteorcar
ParkingCameraSequence = Enum( 'ParkingCameraSequence', \
                    'initial_marker \
                    move_nearby_parking_lot \
                    parking \
                    decide \
                    cut_pliers_align_ZX \
                    cut_pliers_dead_reckoning_up \
                    cut_pliers_dead_reckoning_down \
                    cut_pliers_dead_reckoning_extend \
                    cut_pliers_dead_reckoning_retract \
                    close_pliers \
                    open_pliers \
                    stop \
                    error')
FrontSequence = Enum( 'FrontSequence', \
                        'Front \
                        stop \
                        error')
TurnSequence = Enum( 'TurnSequence', \
                        'Turn \
                        stop \
                        error')
    
class PBVS():
    def __init__(self, _as, subscriber, mode):
        self._as = _as
        self._feedback = forklift_server.msg.PBVSMegaposeFeedback()
        self._result = forklift_server.msg.PBVSMegaposeResult()
        self.subscriber = subscriber
        self.command = mode.command
        self.layer_dist = mode.layer_dist
        self.check_wait_time = 0
        self.Action = Action(self.subscriber)

    def parking_camera(self):
        current_sequence = ParkingCameraSequence.initial_marker.value
        previous_sequence = None  # 用來記錄上一次的階段

        while(not rospy.is_shutdown()):
            # 如果 current_sequence 發生變化，記錄 log
            if current_sequence != previous_sequence:
                rospy.loginfo('Current Sequence: {0}'.format(ParkingCameraSequence(current_sequence)))
                previous_sequence = current_sequence  # 更新 previous_sequence

            if(current_sequence == ParkingCameraSequence.initial_marker.value):
                self.subscriber.fnDetectionAllowed(True, self.layer_dist)  # fnDetectionAllowed(self, pose_detection, layer)
                self.is_sequence_finished = self.Action.fnSeqMarkerDistanceValid()
                
                if self.is_sequence_finished == True:
                    current_sequence = ParkingCameraSequence.move_nearby_parking_lot.value
                    self.is_sequence_finished = False
            
            elif(current_sequence == ParkingCameraSequence.move_nearby_parking_lot.value):
                self.is_sequence_finished = self.Action.fnSeqMovingNearbyParkingLot(self.subscriber.camera_desired_dist_threshold)
                
                if self.is_sequence_finished == True:
                    current_sequence = ParkingCameraSequence.parking.value
                    self.is_sequence_finished = False
            elif(current_sequence == ParkingCameraSequence.parking.value):
                self.is_sequence_finished = self.Action.fnSeqParking(self.subscriber.camera_horizon_alignment_threshold, 0.2)
                
                if self.is_sequence_finished == True:
                    current_sequence = ParkingCameraSequence.decide.value
                    self.is_sequence_finished = False
            elif(current_sequence == ParkingCameraSequence.decide.value):
                self.is_sequence_finished = self.Action.fnSeqdecide(self.subscriber.camera_desired_dist_threshold, self.subscriber.camera_horizon_alignment_threshold )
                
                if self.is_sequence_finished == True:
                    current_sequence = ParkingCameraSequence.cut_pliers_align_ZX.value
                    self.is_sequence_finished = False
                elif self.is_sequence_finished == False:
                    current_sequence = ParkingCameraSequence.move_nearby_parking_lot.value
                    self.is_sequence_finished = False

            elif(current_sequence == ParkingCameraSequence.cut_pliers_align_ZX.value):
                self.is_sequence_finished = self.Action.ClawAlignZX()
                if self.is_sequence_finished:
                    current_sequence = ParkingCameraSequence.cut_pliers_dead_reckoning_extend.value  
                    self.is_sequence_finished = False  

            elif(current_sequence == ParkingCameraSequence.cut_pliers_dead_reckoning_extend.value):
                self.is_sequence_finished = self.Action.DeadMoveX(self.subscriber.cut_pliers_blind_extend_length, speed_k=0.5)
                if self.is_sequence_finished:
                    current_sequence = ParkingCameraSequence.close_pliers.value  
                    self.is_sequence_finished = False  

            elif(current_sequence == ParkingCameraSequence.close_pliers.value):
                self.is_sequence_finished = self.Action.fnControlClaw(1)  # 關閉剪鉗
                if self.is_sequence_finished:
                    current_sequence = ParkingCameraSequence.cut_pliers_dead_reckoning_up.value  
                    self.is_sequence_finished = False

            elif(current_sequence == ParkingCameraSequence.cut_pliers_dead_reckoning_up.value):
                self.is_sequence_finished = self.Action.DeadMoveZ(target_z=120, speed_k=0.5)
                if self.is_sequence_finished:
                    current_sequence = ParkingCameraSequence.cut_pliers_dead_reckoning_retract.value  
                    self.is_sequence_finished = False
            
            elif(current_sequence == ParkingCameraSequence.cut_pliers_dead_reckoning_retract.value):
                self.is_sequence_finished = self.Action.fnRetractArm()
                if self.is_sequence_finished:
                    current_sequence = ParkingCameraSequence.cut_pliers_dead_reckoning_retract.value  
                    self.is_sequence_finished = False
            
            else:
                rospy.logerr('Error: {0} does not exist'.format(current_sequence))
                self.subscriber.fnDetectionAllowed(False, self.layer_dist)  # fnDetectionAllowed(self, shelf_detection, pallet_detection, layer)
                if self.check_wait_time > 15 :
                    self.check_wait_time = 0
                    return
                else:
                    self.check_wait_time =self.check_wait_time  +1
    
    def odom_front(self):
        current_sequence = FrontSequence.Front.value
        previous_sequence = None  # 用來記錄上一次的階段

        while(not rospy.is_shutdown()):
            # 如果 current_sequence 發生變化，記錄 log
            if current_sequence != previous_sequence:
                rospy.loginfo('Current Sequence: {0}'.format(FrontSequence(current_sequence)))
                previous_sequence = current_sequence  # 更新 previous_sequence
            self.subscriber.fnDetectionAllowed(False, self.layer_dist)  # fnDetectionAllowed(self, shelf_string, pallet_string)

            if(current_sequence == FrontSequence.Front.value):
                self.is_sequence_finished = self.Action.fnseqDeadReckoning(-self.layer_dist)
                if self.is_sequence_finished == True:
                    current_sequence = FrontSequence.stop.value
                    self.is_sequence_finished = False

            elif(current_sequence == FrontSequence.stop.value):
                    if self.check_wait_time > 15 :
                        self.check_wait_time = 0
                        return
                    else:
                        self.check_wait_time =self.check_wait_time  +1
            else:
                rospy.loginfo('Error: {0} does not exist'.format(current_sequence))
                if self.check_wait_time > 15 :
                    self.check_wait_time = 0
                    return
                else:
                    self.check_wait_time =self.check_wait_time  +1
            
    def odom_turn(self):
        current_sequence = TurnSequence.Turn.value
        previous_sequence = None  # 用來記錄上一次的階段

        while(not rospy.is_shutdown()):
            # 如果 current_sequence 發生變化，記錄 log
            if current_sequence != previous_sequence:
                rospy.loginfo('Current Sequence: {0}'.format(TurnSequence(current_sequence)))
                previous_sequence = current_sequence  # 更新 previous_sequence
            self.subscriber.fnDetectionAllowed(False, self.layer_dist)  # fnDetectionAllowed(self, shelf_string, pallet_string)

            if(current_sequence == TurnSequence.Turn.value):
                self.is_sequence_finished = self.Action.fnseqDeadReckoningAngle(self.layer_dist)
                if self.is_sequence_finished == True:
                    current_sequence = TurnSequence.stop.value
                    self.is_sequence_finished = False
                
                elif(current_sequence == TurnSequence.stop.value):
                    if self.check_wait_time > 15 :
                        self.check_wait_time = 0
                        return
                    else:
                        self.check_wait_time =self.check_wait_time  +1
            else:
                rospy.loginfo('Error: {0} does not exist'.format(current_sequence))
                if self.check_wait_time > 15 :
                    self.check_wait_time = 0
                    return
                else:
                    self.check_wait_time =self.check_wait_time  +1
