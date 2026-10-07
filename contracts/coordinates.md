# V1坐标与单位

权威机械定义为config/geometry.json和contracts/mechanical_interfaces.json，本文件只定义转换。A0的前方−Y及Wheel_R=left关系不能用于V1。

V1机械/机身M：X右、Y前、Z上；SI控制C：x前、y左、z上；C=(M.Y,-M.X,M.Z)，det=+1。控制left是机械X负侧。机身正前倾为机械−X旋转、控制+y旋转。头yaw正向左=机械+Z；头pitch抬头=机械+X=控制−y，与正机身前倾符号相反。

相机光学O：x右、y下、z前；零位转成控制C=(O.z,-O.x,-O.y)。先按头pitch绕控制−y旋转，再yaw绕控制+z，再乘机身姿态。相机安装偏置与内参来自标定，初始只使用明确标为SIMULATED的假设FOV；估计头角不得标成传感器反馈。屏幕注视x右/y下，与机械头角独立。

所有控制长度m、角度rad、速度m/s和rad/s。UI的mm/deg须转换。时间戳为设备单调ms，采样/完成/到达分开。跨机时钟不能直接相减：命令回显最新设备basis_device_ms，设备计算保守有效期；视觉回传原capture_id，由本地保存的采集单调时间判年龄，拒绝未知ID和过期帧。

视觉实现补充：目标射线先按采集时刻的头 yaw/pitch 与机身 pitch/yaw 转到世界，
再按当前机身姿态反变换到当前机身，以生成头部目标与底盘转向误差。
`target_angles` 的两个机身姿态不可混用。相机内参 fx=fy=1.2（归一化图像单位）
仅为模拟夹具假设；零点、真实内外参、头反馈和里程漂移均须实测后替换。
