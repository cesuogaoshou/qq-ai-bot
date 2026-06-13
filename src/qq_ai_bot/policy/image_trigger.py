from __future__ import annotations

from dataclasses import dataclass


_IMAGE_TRIGGER_TERMS = (
    "看图",
    "读图",
    "图片",
    "截图",
    "图中",
    "图里",
    "图上",
    "这张图",
    "张图",
    "照片",
    "提取文字",
    "识别文字",
    "ocr",
    "OCR",
)


@dataclass(frozen=True)
class ImageTrigger:
    should_process: bool
    prompt: str = ""


def detect_image_trigger(message: str) -> ImageTrigger:
    stripped = message.strip()
    if any(term in stripped for term in _IMAGE_TRIGGER_TERMS):
        return ImageTrigger(should_process=True, prompt=stripped)
    return ImageTrigger(should_process=False)
