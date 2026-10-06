from review_P5R3 import *
def local():
 e=Edit('power');e.move('C76',(26.4,44.1),270)
 e.remove(ids=['047811f8'])
 e.remove(ids=['e8915ef5'])
 e.add('/+5V_MOTION',F,[(7.478,24.003),(6.978,24.503),(6.978,29.478),(7.478,29.978)],.2)
 # Attach the ADC branch squarely, without extending across its source trunk.
 e.remove(ids=['0583db36'])
 e.add('/WHEEL_ADC',F,[(44.675,21),(44.675,22.6),(44.14,22.6)],.2)
 e.save()
 print('Local electrical corrections staged')
if __name__=='__main__':local()
