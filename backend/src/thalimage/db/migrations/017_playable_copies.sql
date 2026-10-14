-- Whether a video needs a playable copy (core/video.py): 1 when iOS is not
-- expected to play the original, 0 when it is. NULL until a scan has probed
-- the video, and always for still images.
ALTER TABLE images ADD COLUMN needs_playable_copy BOOLEAN;
