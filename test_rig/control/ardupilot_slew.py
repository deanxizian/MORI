# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure port of pinned ArduPilot Filter/SlewLimiter.cpp, no device access.

Reference fb773567896014da007bca58358704d4a0d8516f. Caller supplies the
uint32 millisecond clock. Preserve event order, 25Hz filter and peak decay.
The upstream equation can return below0.1; do not invent a10percent clamp.
"""
import math

UINT32_MASK=(1<<32)-1


class SlewLimiter:
    def __init__(self,maximum,tau):
        if not all(math.isfinite(v) for v in (maximum,tau)) or maximum<0 or tau<=0:
            raise ValueError('invalid_slew_configuration')
        self.maximum=maximum;self.tau=tau
        self.filtered=0.;self.last_sample=0.
        self.positive_peak=self.negative_peak=0.
        self.positive_peak_ms=self.negative_peak_ms=0
        self.output_slew=self.modifier_slew=0.
        self.positive_events=[0,0];self.negative_events=[0,0]
        self.positive_index=self.negative_index=0
        self.positive_stored=self.negative_stored=False

    def modifier(self,sample,dt,now_ms):
        if not all(math.isfinite(v) for v in (sample,dt)):
            raise ValueError('nonfinite_slew_input')
        if type(now_ms) is not int or not 0<=now_ms<=UINT32_MASK:
            raise ValueError('uint32_slew_clock_required')
        if dt<=0:return 1.
        raw=(sample-self.last_sample)/dt
        self.filtered+=dt/(dt+1./(math.tau*25.))*(raw-self.filtered)
        rate=self.filtered;self.last_sample=sample
        decay=min(dt,self.tau)/self.tau
        attack=min(2.*decay,1.)
        if rate>self.positive_peak:
            self.positive_peak=rate;self.positive_peak_ms=now_ms
        elif (now_ms-self.positive_peak_ms)&UINT32_MASK>300:
            self.positive_peak*=1.-decay
        if -rate>self.negative_peak:
            self.negative_peak=-rate;self.negative_peak_ms=now_ms
        elif (now_ms-self.negative_peak_ms)&UINT32_MASK>300:
            self.negative_peak*=1.-decay
        raw_rate=.5*(self.positive_peak+self.negative_peak)
        self.output_slew=min((1.-attack)*self.output_slew+attack*raw_rate,raw_rate)
        if self.maximum<=0:return 1.
        limited_rate=.5*(min(self.positive_peak,10.*self.maximum)+
                          min(self.negative_peak,10.*self.maximum))
        if not self.positive_stored and rate>self.maximum:
            if self.positive_index>=2:self.positive_index=0
            self.positive_events[self.positive_index]=now_ms;self.positive_index+=1
            self.positive_stored=True;self.negative_stored=False
        if not self.negative_stored and -rate>self.maximum:
            if self.negative_index>=2:self.negative_index=0
            self.negative_events[self.negative_index]=now_ms;self.negative_index+=1
            self.negative_stored=True;self.positive_stored=False
        oldest=min(now_ms,*self.positive_events,*self.negative_events)
        age=(now_ms-oldest)&UINT32_MASK
        modifier_input=limited_rate
        if age>900:modifier_input*=math.exp(-.001*(age-900)/self.tau)
        self.modifier_slew=min((1.-attack)*self.modifier_slew+attack*modifier_input,modifier_input)
        if self.modifier_slew>self.maximum:
            return self.maximum/(self.maximum+1.5*(self.modifier_slew-self.maximum))
        return 1.
