# video_processor.py
import cv2
import os
from skimage.metrics import structural_similarity as ssim
import numpy as np
import time
from config import TEMP_DIR

def extract_distinct_frames(video_path, similarity_threshold=0.32):
    """
    Extracts distinct frames from a video.
    A frame is considered distinct if its structural similarity to the
    previously selected distinct frame is below the threshold.
    similarity_threshold: the limit below which two frames are considered dissimilar.
    """
    distinct_frames_paths = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return []

    prev_gray_frame = None
    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Process roughly 1-2 frames per second, or more if video is short
    frame_skip = max(1, int(fps / 2)) if fps > 0 else 1


    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0 and frame_skip != 1: # Process only every Nth frame to speed up
            continue
        
        h, w, _ = frame.shape
        if h < w:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        current_gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_gray_frame = cv2.resize(current_gray_frame, (300,300)) # Resize for faster SSIM

        is_distinct = False
        if prev_gray_frame is None:
            is_distinct = True
        else:
            try:
                s = ssim(prev_gray_frame, current_gray_frame)
                if s < similarity_threshold:
                    is_distinct = True
            except ValueError as e: # Catch potential size mismatch if resize fails unexpectedly
                print(f"SSIM ValueError: {e}. Considering frame distinct.")
                is_distinct = True


        if is_distinct:
            frame_filename = os.path.join(TEMP_DIR, f"frame_{time.time()}.png")
            cv2.imwrite(frame_filename, frame)
            distinct_frames_paths.append(frame_filename)
            prev_gray_frame = current_gray_frame
            # print(f"Saved distinct frame: {frame_filename}")

    cap.release()
    print(f"Extracted {len(distinct_frames_paths)} distinct frames from video.")
    return distinct_frames_paths

def extract_distinct_frames_motion(video_path, motion_threshold=1.0, stabilization_frames=3, min_ssim_diff=0.75):
    """
    Extracts frames that likely represent a new section after a scroll.
    motion_threshold: Average optical flow magnitude to consider as scrolling.
    stabilization_frames: Number of consecutive frames with low motion to consider stabilized.
    min_ssim_diff: 1.0 - SSIM value. How different a new stable frame must be from the last.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return []

    new_section_frame_paths = []
    
    ret, prev_frame_bgr = cap.read()
    # h, w, _ = prev_frame_bgr.shape
    # if h < w:
    #     prev_frame_bgr = cv2.rotate(prev_frame_bgr, cv2.ROTATE_90_CLOCKWISE)

    if not ret:
        return []
    
    prev_gray = cv2.cvtColor(prev_frame_bgr, cv2.COLOR_BGR2GRAY)
    
    # Capture the first frame as a new section
    first_frame_path = os.path.join(TEMP_DIR, f"section_0_{time.time()}.png")
    cv2.imwrite(first_frame_path, prev_frame_bgr)
    new_section_frame_paths.append(first_frame_path)
    last_captured_gray_for_ssim = prev_gray.copy() # For SSIM check later

    is_scrolling = False
    stable_count = 0
    frame_idx = 0

    while True:
        ret, current_frame_bgr = cap.read()
        # h, w, _ = current_frame_bgr.shape
        # if h < w:
        #     current_frame_bgr = cv2.rotate(current_frame_bgr, cv2.ROTATE_90_CLOCKWISE)
        if not ret:
            break
        
        frame_idx += 1
        current_gray = cv2.cvtColor(current_frame_bgr, cv2.COLOR_BGR2GRAY)

        # Calculate Farneback optical flow
        flow = cv2.calcOpticalFlowFarneback(prev_gray, current_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        avg_magnitude = np.mean(magnitude)

        if avg_magnitude > motion_threshold:
            is_scrolling = True
            stable_count = 0
            # print(f"Frame {frame_idx}: Scrolling (avg_mag: {avg_magnitude:.2f})")
        elif is_scrolling: # Was scrolling, now motion is low
            stable_count += 1
            # print(f"Frame {frame_idx}: Potentially stabilizing (avg_mag: {avg_magnitude:.2f}, stable_count: {stable_count})")
            if stable_count >= stabilization_frames:
                # View has stabilized after a scroll
                # Now, check if this stable frame is significantly different from the last captured one
                # (using SSIM or a similar metric for an additional check)                
                # Resize for faster SSIM and consistency
                resized_current_gray = cv2.resize(current_gray, (last_captured_gray_for_ssim.shape[1], last_captured_gray_for_ssim.shape[0]))
                s = ssim(last_captured_gray_for_ssim, resized_current_gray)

                if (1.0 - s) > min_ssim_diff:
                    print(f"Frame {frame_idx}: New section detected after scroll! (SSIM diff: {1-s:.2f})")
                    section_frame_path = os.path.join(TEMP_DIR, f"section_{len(new_section_frame_paths)}_{time.time()}.png")
                    cv2.imwrite(section_frame_path, current_frame_bgr)
                    new_section_frame_paths.append(section_frame_path)
                    last_captured_gray_for_ssim = current_gray.copy() # Update the reference
                else:
                    # print(f"Frame {frame_idx}: Stabilized, but not different enough from last section (SSIM diff: {1-s:.2f})")
                    pass
                
                is_scrolling = False # Reset scrolling state
                stable_count = 0
        # else: # Not scrolling, and wasn't just scrolling
            # print(f"Frame {frame_idx}: Stable (avg_mag: {avg_magnitude:.2f})")
            # pass

        prev_gray = current_gray.copy()

    cap.release()
    print(f"Extracted {len(new_section_frame_paths)} potential new section frames using motion detection.")
    return new_section_frame_paths

def cleanup_files(file_paths):
    """Deletes a list of files."""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

if __name__ == "__main__":
    # extract_distinct_frames("test_data\PXL_20250606_064422557.mp4")
    extract_distinct_frames_motion("test_data/PXL_20250606_064422557.mp4")