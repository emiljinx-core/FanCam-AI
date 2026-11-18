export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface NormalizedBox {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface DetectedPerson {
  id: string;
  name: string;
  confidence: number;
  box: NormalizedBox;
  crop_url: string;
  role: string;
}

export interface DetectFrameResponse {
  video_id: string;
  frame_index: number;
  timestamp_sec: number;
  frame_width: number;
  frame_height: number;
  frame_preview_url: string;
  detected_people: DetectedPerson[];
  total_detected: number;
  device_used: string;
}

export interface VideoMetaResponse {
  video_id: string;
  width: number;
  height: number;
  fps: number;
  frame_count: number;
  duration_seconds: number;
}

export interface ExtractFrameResponse {
  video_id: string;
  frame_index: number;
  timestamp_sec: number;
  frame_width: number;
  frame_height: number;
  preview_url: string;
}

export async function getVideoMetadata(videoId: string): Promise<VideoMetaResponse> {
  const res = await fetch(`${API_BASE_URL}/api/video/${videoId}/meta`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch video metadata' }));
    throw new Error(err.detail || `Failed to fetch video metadata with status ${res.status}`);
  }
  return res.json();
}

export async function extractFramePreview(
  videoId: string,
  frameIndex?: number,
  timestampSec?: number
): Promise<ExtractFrameResponse> {
  const res = await fetch(`${API_BASE_URL}/api/video/${videoId}/extract-frame`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame_index: frameIndex,
      timestamp_sec: timestampSec,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to extract frame' }));
    throw new Error(err.detail || `Failed to extract frame with status ${res.status}`);
  }
  return res.json();
}


export interface ProcessVideoRequest {
  video_id: string;
  target_id: string;
  tracking_algorithm?: 'bytetrack' | 'deepsort';
  tracker?: 'bytetrack' | 'deepsort';
  aspect_ratio: '9:16' | '1:1' | '16:9';
  smoothing_level: number;
}

export interface ProcessVideoResponse {
  task_id: string;
  video_id: string;
  status: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  video_id: string;
  target_id: string;
  tracker: string;
  aspect_ratio: string;
  smoothing_level: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  output_video_url?: string;
  comparison_video_url?: string;
  error?: string;
}

export async function uploadVideoFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function detectFramePeople(
  videoId: string,
  frameIndex: number = 0,
  confThreshold: number = 0.35
): Promise<DetectFrameResponse> {
  const res = await fetch(`${API_BASE_URL}/api/video/${videoId}/detect-frame`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame_index: frameIndex,
      conf_threshold: confThreshold,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Frame detection failed' }));
    throw new Error(err.detail || `Frame detection failed with status ${res.status}`);
  }

  return res.json();
}

export async function selectTarget(videoId: string, targetId: string, cropUrl?: string) {
  const res = await fetch(`${API_BASE_URL}/api/video/${videoId}/select-target`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_id: targetId, crop_url: cropUrl }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Select target failed' }));
    throw new Error(err.detail || `Select target failed with status ${res.status}`);
  }

  return res.json();
}

export async function startProcessingVideo(params: ProcessVideoRequest): Promise<ProcessVideoResponse> {
  const res = await fetch(`${API_BASE_URL}/api/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Processing start failed' }));
    throw new Error(err.detail || `Processing start failed with status ${res.status}`);
  }

  return res.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/status/${taskId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Task status fetch failed' }));
    throw new Error(err.detail || `Failed to fetch status with status ${res.status}`);
  }
  return res.json();
}

export function getDownloadUrl(videoId: string): string {
  return `${API_BASE_URL}/api/download/${videoId}`;
}

export interface ContactFormPayload {
  name: string;
  email: string;
  subject: string;
  message: string;
  website?: string; // Honeypot
}

export interface ContactResponse {
  message: string;
  email_id?: string | null;
}

export async function submitContactForm(payload: ContactFormPayload): Promise<ContactResponse> {
  const res = await fetch(`${API_BASE_URL}/api/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to send message' }));
    throw new Error(errorData.detail || `Failed to send message with status ${res.status}`);
  }

  return res.json();
}

