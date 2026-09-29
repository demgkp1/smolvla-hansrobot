import argparse
import shutil
from pathlib import Path

import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset


def record_episodes(num_episodes: int = 3, num_frames: int = 100, repo_id: str = "hansrobot/smoke_test"):
    root = Path("data/datasets/smoke_test")
    if root.exists():
        shutil.rmtree(root)

    features = {
        "observation.images.camera1": {
            "dtype": "video",
            "shape": (224, 224, 3),
            "names": ["height", "width", "channels"],
        },
        "observation.state": {
            "dtype": "float32",
            "shape": (7,),
            "names": ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "gripper"],
        },
        "action": {
            "dtype": "float32",
            "shape": (7,),
            "names": ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "gripper"],
        },
    }

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=30,
        features=features,
        root=root,
        use_videos=True,
    )

    for ep_idx in range(num_episodes):
        print(f"Generating episode {ep_idx + 1}/{num_episodes} ({num_frames} frames)...")
        for _ in range(num_frames):
            frame = {
                "observation.images.camera1": np.random.randint(0, 256, size=(224, 224, 3), dtype=np.uint8),
                "observation.state": np.random.randn(7).astype(np.float32),
                "action": np.random.randn(7).astype(np.float32),
                "task": "smoke_test",
            }
            dataset.add_frame(frame)
        dataset.save_episode()

    dataset.finalize()
    print(f"Dataset generated successfully at {root}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fake smoke_test dataset for SmolVLA")
    parser.add_argument("--num_episodes", type=int, default=3, help="Number of episodes to generate (default: 3)")
    parser.add_argument("--num_frames", type=int, default=100, help="Frames per episode (default: 100)")
    args = parser.parse_args()

    record_episodes(num_episodes=args.num_episodes, num_frames=args.num_frames)
