from review_P5R5 import *
import close_P5 as c
c.paths=paths
c.run('power',nets=['/M5_EN','/C5_EN','/WHEEL_ADC','/CHG_N','/+5V_MOTION','/+5V_CAM'],widths={'/+5V_MOTION':.2,'/+5V_CAM':.2})
