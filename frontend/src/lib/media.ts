/** Video file extensions; must match VIDEO_EXTENSIONS in backend core/video.py. */
const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);

/** Whether a filename is one of the video formats the scanner indexes. */
export function isVideoFilename(filename: string): boolean {
	const dot = filename.lastIndexOf('.');
	return dot >= 0 && VIDEO_EXTENSIONS.has(filename.slice(dot).toLowerCase());
}
