# Mink 小型隔离依赖安装审批方案

只写 v0.2/.venv-sim 和 v0.2/artifacts/pip-cache，不修改既有 MuJoCo 环境、系统 Python 或 Conda base。
用已存在的 MuJoCo Python3.12.14 创建 --system-site-packages venv，只读复用 MuJoCo3.9.0/numpy2.5.2。
安装固定 mink1.2.0、qpsolvers4.13.0、daqp0.8.5、scipy1.18.1，--no-deps --only-binary=:all:，避免隐式升级。
Mink要求mujoco>=3.8.1、qpsolvers[daqp]>=4.12.0；SciPy要求Python>=3.12、numpy>=2,<2.8，现有组合满足声明。
公开PyPI cp312 Linux x86_64 wheel合计36,394,460 bytes（约36.4MB）；附少量metadata网络流量。运行兼容性仍需安装后小测试。
不安装Mink1.3.0，因为其要求MuJoCo>=3.10.0。此次不下载模型、不启动GPU、不连接硬件。
授权后用新venv的pip按 environments/sim-ik-overlay.txt 安装，验证import和pip check；不将venv加入Git。
