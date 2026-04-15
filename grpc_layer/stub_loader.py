from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def load_stubs() -> tuple[ModuleType, ModuleType]:
    root = Path(__file__).resolve().parents[1]
    generated_dir = root / "grpc_layer" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    pb2_file = generated_dir / "scheduler_pb2.py"
    pb2_grpc_file = generated_dir / "scheduler_pb2_grpc.py"
    if not (pb2_file.exists() and pb2_grpc_file.exists()):
        _generate_stubs(root, generated_dir)
    if str(generated_dir) not in sys.path:
        sys.path.insert(0, str(generated_dir))
    scheduler_pb2 = importlib.import_module("scheduler_pb2")
    scheduler_pb2_grpc = importlib.import_module("scheduler_pb2_grpc")
    return scheduler_pb2, scheduler_pb2_grpc


def _generate_stubs(root: Path, generated_dir: Path) -> None:
    proto_path = root / "grpc_layer" / "scheduler.proto"
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"-I{proto_path.parent}",
                f"--python_out={generated_dir}",
                f"--grpc_python_out={generated_dir}",
                str(proto_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - dependency dependent
        raise RuntimeError(
            "Failed to generate gRPC stubs. Install grpcio-tools and rerun."
        ) from exc
