# SmolVLA x HansRobot

用 HansRobot 工业机械臂 + 夹爪 + 相机采集示教数据，微调 SmolVLA，实现真机自主抓取。

## 项目闭环

```text
HansRobot + 夹爪 + 相机
        ->
键盘 Teleop 采集数据
        ->
LeRobotDataset
        ->
SmolVLA 微调
        ->
自己的 checkpoint
        ->
相机 -> SmolVLA -> Action -> HansRobot 真机执行
```

## VS Code 一键运行与调试

本项目支持在 VS Code 中直接运行与调试各阶段验证脚本，无需在终端手动拼写模块路径：

1. **右上角一键运行**：
   - 在 VS Code 中打开任意脚本（例如 `tests/inspect_cps_signatures.py`、`tests/m1_single_joint_move.py`、`tests/m2_reverse_move.py`、`keyboard_servo_teleop.py`）。
   - 直接点击编辑器右上角的“运行”按钮（Run Python File）即可直接执行 dry-run。
   - 所有脚本均默认以安全只读（dry-run）模式启动，不会触发真机运动。

2. **“运行和调试”侧边栏配置**：
   - 按 `Ctrl+Shift+D`（macOS 为 `Cmd+Shift+D`）打开 VS Code 的“运行和调试”侧边栏。
   - 在顶部下拉菜单中选择对应任务一键启动：
     - `Inspect CPS Signatures`：检查官方 CPS SDK 关键方法签名（只读，无需连接机械臂）。
     - `M-1 dry-run`：单步关节正向运动验证骨架（只读 dry-run，默认 axis 1, delta 1）。
     - `M-2 dry-run`：单步关节反向运动验证骨架（只读 dry-run，默认 axis 1, delta -1）。
     - `M-3 dry-run`：键盘关节 Servo 验证骨架（只读 dry-run，默认 override 0.05）。
     - `Official SDK Check`：官方 SDK 只读状态与位姿读取测试。

3. **真机执行说明（安全红线）**：
   - 默认的所有配置和直接点击运行均**不带** `--execute --yes`。
   - 严禁在 `launch.json` 中预设 `--execute --yes`。
   - 真机运动前必须在终端中显式添加 `--execute --yes`，且只有在代码中确认签名并将对应的安全开关（如 `TODO_MOVE_RELJ_READY`、`TODO_GRP_STOP_READY`、`TODO_SERVO_READY`）修改为 `True` 后才会实际发送运动指令。

> [!WARNING]
> **安全提醒**：
> - 调试和运行真机运动时，请务必确保物理急停按钮在手边随时可触达！
> - 任何软件层面的停止命令（如 `GrpStop`）都不能替代物理急停。