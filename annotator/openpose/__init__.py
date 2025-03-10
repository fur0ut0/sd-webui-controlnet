import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

import torch
import numpy as np
from . import util
from .body import Body
from .hand import Hand

body_estimation = None 
hand_estimation = None 

body_model_path = "https://huggingface.co/lllyasviel/ControlNet/resolve/main/annotator/ckpts/body_pose_model.pth"
hand_model_path = "https://huggingface.co/lllyasviel/ControlNet/resolve/main/annotator/ckpts/hand_pose_model.pth"
modeldir = os.path.dirname(os.path.realpath(__file__))

def unload_openpose_model():
    global body_estimation, hand_estimation
    if body_estimation is not None:
        body_estimation.model.cpu()
        hand_estimation.model.cpu()

def apply_openpose(oriImg, hand=False):
    global body_estimation, hand_estimation
    if body_estimation is None:
        body_modelpath = os.path.join(modeldir, "body_pose_model.pth")
        hand_modelpath = os.path.join(modeldir, "hand_pose_model.pth")
        
        if not os.path.exists(hand_modelpath):
            from basicsr.utils.download_util import load_file_from_url
            load_file_from_url(body_model_path, model_dir=modeldir)
            load_file_from_url(hand_model_path, model_dir=modeldir)
            
        body_estimation = Body(body_modelpath)
        hand_estimation = Hand(hand_modelpath)
    
    oriImg = oriImg[:, :, ::-1].copy()
    with torch.no_grad():
        candidate, subset = body_estimation(oriImg)
        canvas = np.zeros_like(oriImg)
        canvas = util.draw_bodypose(canvas, candidate, subset)
        if hand:
            hands_list = util.handDetect(candidate, subset, oriImg)
            all_hand_peaks = []
            for x, y, w, is_left in hands_list:
                peaks = hand_estimation(oriImg[y:y+w, x:x+w, :])
                peaks[:, 0] = np.where(peaks[:, 0] == 0, peaks[:, 0], peaks[:, 0] + x)
                peaks[:, 1] = np.where(peaks[:, 1] == 0, peaks[:, 1], peaks[:, 1] + y)
                all_hand_peaks.append(peaks)
            canvas = util.draw_handpose(canvas, all_hand_peaks)
        return canvas, dict(candidate=candidate.tolist(), subset=subset.tolist())
