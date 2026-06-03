from __future__ import annotations


def gpu_summary() -> dict[str, object]:
    try:
        import torch

        available = torch.cuda.is_available()
        return {
            "cuda_available": available,
            "device_count": torch.cuda.device_count() if available else 0,
            "device_name": torch.cuda.get_device_name(0) if available else None,
        }
    except ImportError:
        return {"cuda_available": False, "device_count": 0, "device_name": None}

