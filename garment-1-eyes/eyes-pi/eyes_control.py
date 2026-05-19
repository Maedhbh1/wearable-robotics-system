import cv2
from picamera2 import Picamera2
import time
import numpy as np
import board
import adafruit_pca9685
from adafruit_motor import servo
import threading
from datetime import datetime
import os
import glob
import requests


# Eye Control Parameters
X_SERVO_CHANNEL = 1
Y_SERVO_CHANNEL = 2
MIN_X_ANGLE = 50
MAX_X_ANGLE = 135
MIN_Y_ANGLE = 80
MAX_Y_ANGLE = 165
SERVO_MIN_PULSE = 500
SERVO_MAX_PULSE = 2500

# Lid Control Parameters
R_LID_SERVO_CHANNEL = 4
L_LID_SERVO_CHANNEL = 3

LRMAX_Y_ANGLE = 160   # Angle that physically OPENS the right lid
LRMIN_Y_ANGLE = 50  # Angle that physically CLOSES the right lid
LLMAX_Y_ANGLE = 60   # Angle that physically OPENS the left lid
LLMIN_Y_ANGLE = 170  # Angle that physically CLOSES the left lid

LID_CLOSE_DELAY = 5.0 # seconds

# Photo Deletion Parameters
PHOTO_DIR = "/home/admin/static/photos/"
MAX_PHOTOS = 50

# Camera to Eye Calibration 
CAM_NORM_X_MIN = 0.25
CAM_NORM_X_MAX = 0.75
CAM_NORM_Y_MIN = 0.25
CAM_NORM_Y_MAX = 0.75
INVERT_X_MAPPING = True
INVERT_Y_MAPPING = True

# AI Configuration 
MODEL_DIR = "/home/admin/face_detection_model/"
PROTOTXT_PATH = MODEL_DIR + "deploy.prototxt"
MODEL_PATH = MODEL_DIR + "res10_300x300_ssd_iter_140000.caffemodel"
CONFIDENCE_THRESHOLD = 0.5 # Default confidence
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Threading, Smoothing, and Timing Parameters 
latest_target_servo_scaled_x = 0.5
latest_target_servo_scaled_y = 0.5
face_detected_in_thread = False
display_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
shared_data_lock = threading.Lock()
stop_threads_event = threading.Event()

SMOOTHING_FACTOR = 0.15
current_smoothed_servo_scaled_x = 0.5
current_smoothed_servo_scaled_y = 0.5

NO_FACE_TIMEOUT = 2.0
last_face_time_from_thread = time.time()
RETURN_TO_CENTER_ON_NO_FACE = True

SERVO_UPDATE_INTERVAL = 0.03
SERVO_MOVE_DELAY = 0.005

# Text Overlay Messages 
OVERLAY_MESSAGES = [
    "PERVERT",
    "CREEP",
    "WEIRDO",
    "PEEPING TOM",
    "SICKO",
    "INCEL"
]
current_message_index = 0 

# ESP32 Network Configeration 
# Garment 2 (Tentacle)
ESP32_TENTACLE_IP = "192.168.1.X"
TENTACLE_URL = f"http://{ESP32_TENTACLE_IP}/trigger"

# Garment 3 (Worm)
ESP32_WORM_IP = "192.168.1.Y"
WORM_URL = f"http://{ESP32_WORM_IP}/trigger"

# PCA9685 and Servo Initialization
def initialize_servos():
    i2c = board.I2C()
    pca = adafruit_pca9685.PCA9685(i2c)
    pca.frequency = 50

    x_servo = servo.Servo(pca.channels[X_SERVO_CHANNEL], min_pulse=SERVO_MIN_PULSE, max_pulse=SERVO_MAX_PULSE)
    y_servo = servo.Servo(pca.channels[Y_SERVO_CHANNEL], min_pulse=SERVO_MIN_PULSE, max_pulse=SERVO_MAX_PULSE)
    l_lid_servo = servo.Servo(pca.channels[L_LID_SERVO_CHANNEL], min_pulse=SERVO_MIN_PULSE, max_pulse=SERVO_MAX_PULSE)
    r_lid_servo = servo.Servo(pca.channels[R_LID_SERVO_CHANNEL], min_pulse=SERVO_MIN_PULSE, max_pulse=SERVO_MAX_PULSE)
    
    print(f"Servos initialized.")
    print(f"X on channel {X_SERVO_CHANNEL}, Y on channel {Y_SERVO_CHANNEL}, Left Lid on channel {L_LID_SERVO_CHANNEL}, Right Lid on channel {R_LID_SERVO_CHANNEL}")
    print(f"X-axis angle range: {MIN_X_ANGLE}-{MAX_X_ANGLE}")
    print(f"Y-axis angle range: {MIN_Y_ANGLE}-{MAX_Y_ANGLE}")
    print(f"Left Lid angle range: 'Closed'={LLMIN_Y_ANGLE}, 'Open'={LLMAX_Y_ANGLE}")
    print(f"Right Lid angle range: 'Closed'={LRMIN_Y_ANGLE}, 'Open'={LRMAX_Y_ANGLE}")
    print(f"Camera X-axis active normalized range: {CAM_NORM_X_MIN:.2f}-{CAM_NORM_X_MAX:.2f}")
    print(f"Camera Y-axis active normalized range: {CAM_NORM_Y_MIN:.2f}-{CAM_NORM_Y_MAX:.2f}")
    print(f"X-axis mapping inverted: {INVERT_X_MAPPING}, Y-axis mapping inverted: {INVERT_Y_MAPPING}")
    print(f"Smoothing Factor: {SMOOTHING_FACTOR}, Servo Update Interval: {SERVO_UPDATE_INTERVAL}s")
    print("Tracking logic: 1 face=track; 2-3 faces=track largest; >3 faces=cycle 1s per face.")
    return x_servo, y_servo, l_lid_servo, r_lid_servo, pca

# Eye Movement Functions
def move_eye_to_angle(x_servo, y_servo, x_angle, y_angle):
    clamped_x_angle = max(MIN_X_ANGLE, min(MAX_X_ANGLE, x_angle))
    clamped_y_angle = max(min(MIN_Y_ANGLE, MAX_Y_ANGLE), min(max(MIN_Y_ANGLE, MAX_Y_ANGLE), y_angle))
    try:
        if x_servo is not None: x_servo.angle = clamped_x_angle
        if y_servo is not None: y_servo.angle = clamped_y_angle
    except OSError as e: print(f"Servo I/O Error: {e}. Check connections.")
    except Exception as e: print(f"Error setting servo angle: {e}")
    if SERVO_MOVE_DELAY > 0: time.sleep(SERVO_MOVE_DELAY)

# Lid Movement Functions
def move_lids_to_angle(l_lid_servo, r_lid_servo, l_angle, r_angle):
    try:
        if l_lid_servo is not None:
            l_clamped_angle = max(min(LLMIN_Y_ANGLE, LLMAX_Y_ANGLE), min(max(LLMIN_Y_ANGLE, LLMAX_Y_ANGLE), l_angle))
            l_lid_servo.angle = l_clamped_angle
        if r_lid_servo is not None:
            r_clamped_angle = max(min(LRMIN_Y_ANGLE, LRMAX_Y_ANGLE), min(max(LRMIN_Y_ANGLE, LRMAX_Y_ANGLE), r_angle))
            r_lid_servo.angle = r_clamped_angle
    except OSError as e: print(f"Servo I/O Error: {e}. Check connections.")
    except Exception as e: print(f"Error setting servo angle: {e}")
    if SERVO_MOVE_DELAY > 0: time.sleep(SERVO_MOVE_DELAY)

# Photo Deletion Function
def manage_photos():
    if not os.path.exists(PHOTO_DIR):
        print(f"[INFO] Photo directory '{PHOTO_DIR}' does not exist. Skipping photo management.")
        return

    photos = glob.glob(os.path.join(PHOTO_DIR, "*.jpg"))
    photos.sort(key=os.path.getctime)
    
    num_photos = len(photos)
    if num_photos > MAX_PHOTOS:
        num_to_delete = num_photos - MAX_PHOTOS
        print(f"[INFO] Photo count ({num_photos}) exceeds max limit ({MAX_PHOTOS}). Deleting {num_to_delete} oldest photos.")
        for i in range(num_to_delete):
            try:
                os.remove(photos[i])
                print(f"🗑️  Deleted: {os.path.basename(photos[i])}")
            except OSError as e:
                print(f"[ERROR] Failed to delete file {photos[i]}: {e}")

# Face Detection Thread Function (Cleaned) 
def face_detection_worker(picam2_obj, dnn_net):
    global latest_target_servo_scaled_x, latest_target_servo_scaled_y, face_detected_in_thread, display_frame, last_face_time_from_thread, shared_data_lock
    current_cycle_target_idx, last_cycle_switch_time, CYCLE_TARGET_DURATION, is_in_cycling_mode = 0, time.time(), 2.0, False
    print("[INFO] Detection thread started.")
    detection_fps_prev_time, detection_frame_count = time.time(), 0

    while not stop_threads_event.is_set():
        try:
            original_frame_data = picam2_obj.capture_array("main")
            if original_frame_data.shape[2] == 4: frame_for_processing = cv2.cvtColor(original_frame_data, cv2.COLOR_BGRA2BGR)
            else: frame_for_processing = cv2.cvtColor(original_frame_data, cv2.COLOR_RGB2BGR)
            (h, w) = frame_for_processing.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(frame_for_processing,(300,300)),1.0,(300,300),(104.0,177.0,123.0))
            dnn_net.setInput(blob); detections = dnn_net.forward()
            valid_faces_details = []
            for i in range(0, detections.shape[2]):
                confidence = detections[0,0,i,2]
                if confidence > CONFIDENCE_THRESHOLD:
                    box = detections[0,0,i,3:7]*np.array([w,h,w,h]);(startX,startY,endX,endY)=box.astype("int")
                    startX,startY,endX,endY=max(0,startX),max(0,startY),min(w-1,endX),min(h-1,endY)
                    if max(0,endX-startX)*max(0,endY-startY) > 0:
                        valid_faces_details.append({"startX":startX,"startY":startY,"endX":endX,"endY":endY,"norm_cam_centerX":(startX+endX)/(2*w),"norm_cam_centerY":(startY+endY)/(2*h),"area":max(0,endX-startX)*max(0,endY-startY),"confidence":confidence})
            num_valid_faces = len(valid_faces_details)
            found_target_this_cycle,target_norm_cam_centerX,target_norm_cam_centerY,current_target_face_details = False,0.5,0.5,None
            if num_valid_faces==0: is_in_cycling_mode,found_target_this_cycle=False,False
            elif num_valid_faces==1: is_in_cycling_mode=False;target_face=valid_faces_details[0];target_norm_cam_centerX,target_norm_cam_centerY=target_face["norm_cam_centerX"],target_face["norm_cam_centerY"];found_target_this_cycle,current_target_face_details=True,target_face
            elif num_valid_faces<=3: is_in_cycling_mode=False;valid_faces_details.sort(key=lambda f:f["area"],reverse=True);largest_face=valid_faces_details[0];target_norm_cam_centerX,target_norm_cam_centerY=largest_face["norm_cam_centerX"],largest_face["norm_cam_centerY"];found_target_this_cycle,current_target_face_details=True,largest_face
            else:
                if not is_in_cycling_mode:is_in_cycling_mode,current_cycle_target_idx,last_cycle_switch_time=True,0,time.time()
                if(time.time()-last_cycle_switch_time)>CYCLE_TARGET_DURATION:current_cycle_target_idx=(current_cycle_target_idx+1)%num_valid_faces;last_cycle_switch_time=time.time()
                current_cycle_target_idx=min(current_cycle_target_idx,num_valid_faces-1);cycled_target_face=valid_faces_details[current_cycle_target_idx];target_norm_cam_centerX,target_norm_cam_centerY=cycled_target_face["norm_cam_centerX"],cycled_target_face["norm_cam_centerY"];found_target_this_cycle,current_target_face_details=True,cycled_target_face
            for face_idx,face_detail in enumerate(valid_faces_details):
                is_current_target=(current_target_face_details is not None and face_detail["startX"]==current_target_face_details["startX"]and face_detail["startY"]==current_target_face_details["startY"])
                color,thickness,extra_text=(255,100,100),1,""
                if is_current_target:
                    thickness=2
                    if num_valid_faces==1:color,extra_text=(0,255,0),"(Tracking)"
                    elif num_valid_faces<=3:color,extra_text=(0,255,0),"(Largest)"
                    elif is_in_cycling_mode:color,extra_text=(0,255,255),f"(Cycling {current_cycle_target_idx+1}/{num_valid_faces})"
                cv2.rectangle(frame_for_processing,(face_detail["startX"],face_detail["startY"]),(face_detail["endX"],face_detail["endY"]),color,thickness)
                text_conf=f"C:{face_detail['confidence']*100:.0f}% {extra_text}";text_y_pos=face_detail["startY"]-7 if face_detail["startY"]-7>7 else face_detail["startY"]+15
                cv2.putText(frame_for_processing,text_conf,(face_detail["startX"],text_y_pos),cv2.FONT_HERSHEY_SIMPLEX,0.35,color,1)
                if is_current_target:cv2.putText(frame_for_processing,f"NRaw:{face_detail['norm_cam_centerX']:.2f},{face_detail['norm_cam_centerY']:.2f}",(face_detail["startX"],face_detail["endY"]+12),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,255),1)
            if found_target_this_cycle:
                effective_norm_x=target_norm_cam_centerX if(CAM_NORM_X_MAX-CAM_NORM_X_MIN)<=1e-5 else(target_norm_cam_centerX-CAM_NORM_X_MIN)/(CAM_NORM_X_MAX-CAM_NORM_X_MIN)
                effective_norm_y=target_norm_cam_centerY if(CAM_NORM_Y_MAX-CAM_NORM_Y_MIN)<=1e-5 else(target_norm_cam_centerY-CAM_NORM_Y_MIN)/(CAM_NORM_Y_MAX-CAM_NORM_Y_MIN)
                effective_norm_x,effective_norm_y=max(0.0,min(1.0,effective_norm_x)),max(0.0,min(1.0,effective_norm_y))
                final_target_x,final_target_y=(1.0-effective_norm_x)if INVERT_X_MAPPING else effective_norm_x,(1.0-effective_norm_y)if INVERT_Y_MAPPING else effective_norm_y
                with shared_data_lock:latest_target_servo_scaled_x,latest_target_servo_scaled_y,face_detected_in_thread,last_face_time_from_thread=final_target_x,final_target_y,True,time.time()
            else:
                with shared_data_lock:face_detected_in_thread=False
            with shared_data_lock:display_frame=frame_for_processing.copy()
            detection_frame_count+=1;current_time_fps=time.time();elapsed_time_fps=current_time_fps-detection_fps_prev_time
            if elapsed_time_fps>=2.0:fps=detection_frame_count/elapsed_time_fps;print(f"[Detection Thread] Approx. FPS: {fps:.2f}");detection_fps_prev_time,detection_frame_count=current_time_fps,0
            time.sleep(0.01)
        except Exception as e:print(f"[ERROR in Detection Thread]: {e}");import traceback;traceback.print_exc();time.sleep(0.1)
    print("[INFO] Detection thread stopped.")

# esp32 function
def send_tentacle_trigger():
    """Sends a background request to the ESP32 to trigger motors/pumps."""
    try:
        requests.get(TENTACLE_URL, timeout=0.2)
        print("🐙 Signal sent to Tentacle Monster!")
    except Exception as e:
        print(f"🐙 Tentacle Monster offline: {e}")

def send_worm_trigger():
    """Sends a background request to Garment 3 (Worm) ESP32."""
    try:
        requests.get(WORM_URL, timeout=0.2)
        print("🪱 Signal sent to Worm Garment!")
    except Exception as e:
        print(f"🪱 Worm Garment offline: {e}")

# Main Program 
if __name__ == "__main__":    
    picam2 = None
    x_servo_obj, y_servo_obj, l_lid_servo_obj, r_lid_servo_obj, pca_obj = None, None, None, None, None
    detection_thread = None
    lid_is_open = False 
    last_detection_timestamp_from_thread = time.time()
    photo_saved_for_current_detection = False

    try:
        print("[INFO] Initializing Camera...")
        picam2=Picamera2();cam_config=picam2.create_preview_configuration(main={"format":'XRGB8888',"size":(FRAME_WIDTH,FRAME_HEIGHT)},controls={"FrameDurationLimits":(33333,66667)})
        picam2.configure(cam_config);picam2.start()
        actual_fps_limit=1e6/picam2.camera_controls['FrameDurationLimits'][0] if'FrameDurationLimits'in picam2.camera_controls and picam2.camera_controls['FrameDurationLimits'][0]>0 else"N/A"
        print(f"[INFO] Camera started. Target sensor FPS ~{actual_fps_limit}");time.sleep(2.0)
        print("[INFO] Loading face detection model...")
        net=cv2.dnn.readNetFromCaffe(PROTOTXT_PATH,MODEL_PATH)
        if net.empty():raise RuntimeError("Failed to load neural network model.")
        x_servo_obj, y_servo_obj, l_lid_servo_obj, r_lid_servo_obj, pca_obj = initialize_servos()
        
        # Calculate center angles
        center_x_angle = MIN_X_ANGLE + (MAX_X_ANGLE - MIN_X_ANGLE) * 0.5
        center_y_angle = MIN_Y_ANGLE + (MAX_Y_ANGLE - MIN_Y_ANGLE) * 0.5

        print(f"[INFO] Centering eyes...");move_eye_to_angle(x_servo_obj, y_servo_obj, center_x_angle, center_y_angle)
        time.sleep(0.5)
        
        if l_lid_servo_obj and r_lid_servo_obj:
            print(f"[INFO] Initializing lids to closed (Left: {LLMIN_Y_ANGLE} deg, Right: {LRMIN_Y_ANGLE} deg).")
            move_lids_to_angle(l_lid_servo_obj, r_lid_servo_obj, LLMIN_Y_ANGLE, LRMIN_Y_ANGLE)
            lid_is_open=False
            time.sleep(0.5)

        detection_thread=threading.Thread(target=face_detection_worker,args=(picam2,net),daemon=True);detection_thread.start()
        print("\n[INFO] Single eye tracking and dual lid control active. Press 'q' in OpenCV window to quit.")
        main_loop_fps_prev_time,main_loop_frame_count=time.time(),0

        while True:
            loop_start_time=time.time()
            with shared_data_lock:
                target_x_from_thread,target_y_from_thread=latest_target_servo_scaled_x,latest_target_servo_scaled_y
                is_face_detected_main_loop=face_detected_in_thread
                last_detection_timestamp_from_thread=last_face_time_from_thread
                current_display_frame=display_frame.copy()
            time_since_last_detection=time.time()-last_detection_timestamp_from_thread

            if is_face_detected_main_loop:
                if not photo_saved_for_current_detection and picam2 and picam2.started:
                    manage_photos()
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"/home/admin/static/photos/person_detected_{timestamp}.jpg"
                    
                    text_to_overlay = OVERLAY_MESSAGES[current_message_index]
                    current_message_index = (current_message_index + 1) % len(OVERLAY_MESSAGES)

                    if text_to_overlay == "CREEP":
                        print(f"🐙 Word is '{text_to_overlay}'! Triggering Tentacle Monster...")
                        threading.Thread(target=send_tentacle_trigger, daemon=True).start()
                        
                    elif text_to_overlay == "PEEPING TOM":
                        print(f"🪱 Word is '{text_to_overlay}'! Triggering Worm Garment...")
                        threading.Thread(target=send_worm_trigger, daemon=True).start()

                    try:
                        frame_for_photo_rgba = picam2.capture_array("main")
                        if frame_for_photo_rgba.shape[2] == 4:
                            frame_for_photo_bgr = cv2.cvtColor(frame_for_photo_rgba, cv2.COLOR_BGRA2BGR)
                        else:
                            frame_for_photo_bgr = frame_for_photo_rgba
                        
                        # Text drawing settings
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 2
                        font_color = (0, 0, 255)
                        thickness = 3
                        line_type = cv2.LINE_AA
                        
                        image_height, image_width = frame_for_photo_bgr.shape[:2]
                        (text_width, text_height), baseline = cv2.getTextSize(text_to_overlay, font, font_scale, thickness)
                        
                        text_x = int((image_width - text_width) / 2)
                        text_x = max(0, text_x)
                        text_y = 50
                        text_position = (text_x, text_y)
                        
                        cv2.putText(frame_for_photo_bgr, text_to_overlay, text_position, font, font_scale, font_color, thickness, line_type)
                        cv2.imwrite(filename, frame_for_photo_bgr)
                        print(f"📸 Saved photo with text: {filename}")
                        photo_saved_for_current_detection = True
                        
                    except Exception as e:
                        print(f"[ERROR] Could not capture/save photo with text: {e}")
                        import traceback
                        traceback.print_exc()
            else:
                photo_saved_for_current_detection = False

            if not is_face_detected_main_loop and RETURN_TO_CENTER_ON_NO_FACE:
                if time_since_last_detection > NO_FACE_TIMEOUT:
                    final_target_scaled_x, final_target_scaled_y = 0.5, 0.5
                else:
                    final_target_scaled_x, final_target_scaled_y = target_x_from_thread, target_y_from_thread
            elif not is_face_detected_main_loop and not RETURN_TO_CENTER_ON_NO_FACE:
                final_target_scaled_x, final_target_scaled_y = target_x_from_thread, target_y_from_thread
            else:
                final_target_scaled_x, final_target_scaled_y = target_x_from_thread, target_y_from_thread
            
            # Eye Calculations
            current_smoothed_servo_scaled_x = (SMOOTHING_FACTOR * final_target_scaled_x) + ((1 - SMOOTHING_FACTOR) * current_smoothed_servo_scaled_x)
            current_smoothed_servo_scaled_y = (SMOOTHING_FACTOR * final_target_scaled_y) + ((1 - SMOOTHING_FACTOR) * current_smoothed_servo_scaled_y)
            target_x_angle = MIN_X_ANGLE + (MAX_X_ANGLE - MIN_X_ANGLE) * current_smoothed_servo_scaled_x
            target_y_angle = MIN_Y_ANGLE + (MAX_Y_ANGLE - MIN_Y_ANGLE) * current_smoothed_servo_scaled_y

            if x_servo_obj and y_servo_obj:
                move_eye_to_angle(x_servo_obj, y_servo_obj, target_x_angle, target_y_angle)

            if l_lid_servo_obj and r_lid_servo_obj:
                if is_face_detected_main_loop:
                    if not lid_is_open:
                        print(f"[LID CTRL] Person detected. Opening lids (Left: {LLMAX_Y_ANGLE} deg, Right: {LRMAX_Y_ANGLE} deg).")
                        move_lids_to_angle(l_lid_servo_obj, r_lid_servo_obj, LLMAX_Y_ANGLE, LRMAX_Y_ANGLE)
                        lid_is_open=True
                else:
                    if lid_is_open:
                        if time_since_last_detection > LID_CLOSE_DELAY:
                            print(f"[LID CTRL] No person for >{LID_CLOSE_DELAY:.1f}s. Closing lids (Left: {LLMIN_Y_ANGLE} deg, Right: {LRMIN_Y_ANGLE} deg).")
                            move_lids_to_angle(l_lid_servo_obj, r_lid_servo_obj, LLMIN_Y_ANGLE, LRMIN_Y_ANGLE)
                            lid_is_open=False
            
            if current_display_frame.size==0:current_display_frame=np.zeros((FRAME_HEIGHT,FRAME_WIDTH,3),dtype=np.uint8);cv2.putText(current_display_frame,"No Frame",(50,FRAME_HEIGHT//2),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)
            info_text_servo=f"Scl: {current_smoothed_servo_scaled_x:.2f},{current_smoothed_servo_scaled_y:.2f}";cv2.putText(current_display_frame,info_text_servo,(10,FRAME_HEIGHT-15),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,0),1)
            lid_status_text=f"Lid: {'Open'if lid_is_open else'Closed'}";
            if not is_face_detected_main_loop and lid_is_open:lid_status_text+=f" (Closing in {max(0,LID_CLOSE_DELAY-time_since_last_detection):.1f}s)"
            cv2.putText(current_display_frame,lid_status_text,(10,FRAME_HEIGHT-50),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,0),1)
            main_loop_frame_count+=1;elapsed_time_main_fps=time.time()-main_loop_fps_prev_time
            if elapsed_time_main_fps>=1.0:main_fps=main_loop_frame_count/elapsed_time_main_fps;cv2.putText(current_display_frame,f"Main FPS: {main_fps:.2f}",(10,20),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2);main_loop_fps_prev_time,main_loop_frame_count=time.time(),0
            #cv2.imshow("Single Eye Tracking & Lid Control",current_display_frame);key=cv2.waitKey(1)&0xFF
            #if key==ord("q"):print("[INFO] 'q' pressed, shutting down...");break
            #time_to_sleep=max(0,SERVO_UPDATE_INTERVAL-(time.time()-loop_start_time));time.sleep(time_to_sleep)
    except RuntimeError as e:print(f"[FATAL ERROR] Runtime error: {e}");import traceback;traceback.print_exc()
    except KeyboardInterrupt:print("[INFO] Program interrupted by user (Ctrl+C).")
    finally:
        print("[INFO] Cleaning up...");stop_threads_event.set()
        if detection_thread and detection_thread.is_alive():print("[INFO] Waiting for detection thread to finish...");detection_thread.join(timeout=3.0);
        if detection_thread and detection_thread.is_alive():print("[WARN] Detection thread did not finish cleanly.")
        #cv2.destroyAllWindows()
        if picam2 is not None and picam2.started:picam2.stop();print("[INFO] Camera stopped.")
        
        # Center eyes before exiting
        center_x_angle = MIN_X_ANGLE + (MAX_X_ANGLE - MIN_X_ANGLE) * 0.5
        center_y_angle = MIN_Y_ANGLE + (MAX_Y_ANGLE - MIN_Y_ANGLE) * 0.5

        if x_servo_obj and y_servo_obj:print(f"[INFO] Centering eyes before exit...");move_eye_to_angle(x_servo_obj, y_servo_obj, center_x_angle, center_y_angle)
        time.sleep(0.2)
        if l_lid_servo_obj and r_lid_servo_obj:print(f"[INFO] Setting lids to closed (Left: {LLMIN_Y_ANGLE} deg, Right: {LRMIN_Y_ANGLE} deg) before exit...");move_lids_to_angle(l_lid_servo_obj, r_lid_servo_obj, LLMIN_Y_ANGLE, LRMIN_Y_ANGLE)
        time.sleep(0.5)
        if pca_obj:
            try:pca_obj.deinit();print("[INFO] PCA9685 deinitialized.")
            except Exception as e:print(f"[WARN] Error deinitializing PCA9685: {e}")
        print("[INFO] Cleanup complete. Exiting.")