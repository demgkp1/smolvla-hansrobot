# SmolVLA × HansRobot

A robotics project for building a complete manipulation pipeline with a HansRobot industrial arm, gripper, camera, and SmolVLA.

The project starts from low-level robot communication and gradually develops toward demonstration data collection, SmolVLA training, and autonomous manipulation.

## Project Goal

The long-term goal is to build a system that can:

```text
Camera + Robot State
        ↓
    Observation
        ↓
      SmolVLA
        ↓
      Action
        ↓
Robot + Gripper
        ↓
   New Observation
```

The project is developed incrementally, with each stage independently tested before moving to the next one.

## Development Roadmap

### Stage 1 — Robot Bring-up

1. TCP communication
2. Read robot state
3. Read actual robot position
4. Test single-step motion
5. Keyboard point-to-point control
6. Servo-based continuous teleoperation

### Stage 2 — Device Integration

7. Gripper driver
8. Camera driver
9. Robot + gripper + camera coordination

### Stage 3 — Demonstration Data Collection

10. Time synchronization
11. Observation recording
12. Action recording
13. Episode management
14. Dataset recording and integrity checks

### Stage 4 — SmolVLA

15. Dataset validation and cleaning
16. Dataset format conversion
17. Fine-tuning / training
18. Model validation and checkpoint management

### Stage 5 — Autonomous Manipulation

19. Camera → SmolVLA inference
20. Action decoding
21. Robot / gripper execution
22. Closed-loop autonomous grasping

## System Architecture

The final system is designed around a common observation-action interface.

```text
Human Teleoperation
        │
        ▼
 HumanActionProvider
        │
        ▼
      Action
        │
        ▼
    Controller
        │
        ▼
      Robot


SmolVLA
   │
   ▼
VLAActionProvider
   │
   ▼
 Action
   │
   ▼
Controller
   │
   ▼
 Robot
```

This allows human demonstrations and VLA inference to share the same downstream control interface.

The intended closed-loop system is:

```text
Observation_t
 ├── Camera image
 ├── Robot pose / joint state
 └── Gripper state
          │
          ▼
       SmolVLA
          │
          ▼
       Action_t
 ├── Robot motion
 └── Gripper command
          │
          ▼
    Robot / Gripper
          │
          ▼
Observation_(t+1)
```

## Development Principles

### Incremental Validation

The project is developed from the lowest layer upward:

```text
TCP communication
      ↓
Robot state reading
      ↓
Robot position reading
      ↓
Single-step motion
      ↓
Continuous teleoperation
      ↓
Device integration
      ↓
Data collection
      ↓
Model training
      ↓
Autonomous manipulation
```

Each stage should be verified before introducing the next layer.

### Safety First

Robot motion is treated as a physical-system control problem rather than ordinary application logic.

Important principles include:

* Validate communication before sending motion commands.
* Prefer explicit state verification after important robot commands.
* Keep robot motion parameters configurable.
* Avoid treating software stop commands as a replacement for a physical emergency stop.
* Introduce continuous control only after discrete motion has been verified.
* Keep monitoring, control, and safety logic separated as the project develops.

### Reproducibility

Important experiments and development milestones should be recorded in Git and documented.

The repository is intended to contain:

* Source code
* Configuration templates
* Architecture documentation
* Development notes
* Dataset specifications
* Experiment records

Large datasets, model checkpoints, local credentials, and device-specific configuration should not be committed to the public repository.

## Repository Structure

The project structure will evolve with development.

The initial structure is intentionally small:

```text
smolvla-hansrobot/
├── README.md
├── .gitignore
├── config/
├── protocol/
├── devices/
│   └── robot/
├── tests/
├── docs/
└── main.py
```

Future components will be introduced only when they become necessary, including:

```text
control/
perception/
data/
tasks/
safety/
```

## Hardware and Software

### Hardware

* HansRobot industrial robot
* Robot gripper
* RGB / RGB-D camera
* Development PC

### Software

* Ubuntu 24.04
* Python
* Git / GitHub
* PyTorch
* Hugging Face ecosystem
* SmolVLA

Specific versions and hardware configuration will be documented as the project develops.

## Current Status

**Current stage: Stage 1 — Robot Bring-up**

Current milestone:

* [x] Git repository initialized
* [x] Initial `.gitignore`
* [ ] Initial project structure
* [ ] TCP connection test
* [ ] Read robot state
* [ ] Read actual robot position
* [ ] First verified robot motion

## Repository

GitHub:

https://github.com/demgkp1/smolvla-hansrobot
