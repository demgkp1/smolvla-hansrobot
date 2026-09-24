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