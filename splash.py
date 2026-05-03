#!/usr/bin/env python3
import tkinter as tk
import threading,subprocess,time,math
BRAND="AndrobianOS";SUB="debian for android";LOAD="loading joydip's profile"
DESKTOP=["python3","/opt/androbian/launcher.py"]
GL=["#08306b","#0f52ba","#2468d0","#dc143c","#e84060","#ffffff","#e84060","#dc143c","#0f52ba"]
def cl(v,a=0.0,b=1.0):return max(a,min(b,v))
def ez(t):t=cl(t);return 1-(1-t)**3
def rgb(r,g,b):return f"#{int(cl(r,0,255)):02x}{int(cl(g,0,255)):02x}{int(cl(b,0,255)):02x}"
def h2r(h):h=h.lstrip("#");return int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
class S(tk.Tk):
 def __init__(self):
  super().__init__();self.overrideredirect(True);self.configure(bg="#000000")
  self.attributes("-fullscreen",True);self.attributes("-topmost",True)
  self.update_idletasks();self.W=self.winfo_screenwidth();self.H=self.winfo_screenheight()
  self.cv=tk.Canvas(self,bg="#000000",highlightthickness=0,width=self.W,height=self.H)
  self.cv.pack(fill="both",expand=True);self.t0=time.time();self.rdy=False;self.p3t=None
  cx=self.W//2;cy=self.H//2;self.cx=cx;self.cy=cy
  bsz=max(28,int(self.W*0.042));self.bsz=bsz;self.or_=max(40,int(self.W*0.06))
  self.glo=self.cv.create_oval(0,0,1,1,fill="",outline="#000000",width=0)
  self.spk=self.cv.create_oval(0,0,1,1,fill="#000000",outline="")
  r=self.or_;self.rng=self.cv.create_oval(cx-r,cy-r,cx+r,cy+r,fill="",outline="#000000",width=1,dash=(3,9))
  self.grn=self.cv.create_oval(0,0,1,1,fill="#000000",outline="")
  self.red=self.cv.create_oval(0,0,1,1,fill="#000000",outline="")
  self.brd=self.cv.create_text(cx,cy,text=BRAND,fill="#000000",font=("monospace",bsz,"bold"),anchor="center")
  ssz=max(10,int(self.W*0.011));lsz=max(9,int(self.W*0.010))
  self.sub=self.cv.create_text(cx,cy+bsz+14,text=SUB,fill="#000000",font=("monospace",ssz),anchor="center")
  self.by0=cy;self.sy0=cy+bsz+14;self.by1=int(self.H*0.36);self.sy1=self.by1+bsz+14
  self.ldy=int(self.H*0.90)
  self.lod=self.cv.create_text(cx,self.ldy,text=LOAD,fill="#000000",font=("monospace",lsz),anchor="center")
  self.dts=[]
  dy=self.ldy+lsz+14
  for i in range(3):
   d=self.cv.create_oval(cx-14+i*14-3,dy-3,cx-14+i*14+3,dy+3,fill="#000000",outline="")
   self.dts.append(d)
  self.fos=None
  threading.Thread(target=self._go,daemon=True).start()
  self.after(16,self._fr)
 def _go(self):
  try:subprocess.Popen(DESKTOP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(2.5)
  except:time.sleep(4)
  self.rdy=True
 def _fr(self):
  if self.rdy:
   if not self.fos:self.fos=time.time()
   self._fo();return
  t=time.time()-self.t0
  if t<3:self._p1(t)
  elif t<6:self._p2(t)
  else:self._p3()
  self.after(16,self._fr)
 def _p1(self,t):
  cx=self.cx;cy=self.cy
  if t<1:
   p=cl(t/0.5 if t<0.5 else(1-t)/0.5);sr=int(2+p*4);bv=int(p*255);c=rgb(bv,bv,bv)
   self.cv.coords(self.spk,cx-sr,cy-sr,cx+sr,cy+sr);self.cv.itemconfig(self.spk,fill=c)
   gr=sr*7;gv=int(p*45);self.cv.coords(self.glo,cx-gr,cy-gr,cx+gr,cy+gr);self.cv.itemconfig(self.glo,outline=rgb(gv,gv,gv),width=14)
  else:
   self.cv.itemconfig(self.spk,fill="#000000");self.cv.itemconfig(self.glo,outline="#000000")
  if t<1:return
  ot=cl((t-1)/2);al=ez(ot/0.2) if ot<0.2 else(1-ez((ot-0.75)/0.25) if ot>0.75 else 1.0)
  sc=ez(ot/0.5) if ot<0.5 else 1-ez((ot-0.5)/0.5)*0.6;r=max(4,int(self.or_*sc))
  sp=ot*360;sep=ez(cl(ot/0.4 if ot<0.4 else(1-ot)/0.6))*90*sc
  ga=math.radians(sp);gx=cx+r*math.cos(ga)-sep;gy=cy+r*math.sin(ga)
  ra=math.radians(sp+180);rx=cx+r*math.cos(ra)+sep;ry=cy+r*math.sin(ra)
  os_=max(3,int(8*al));rv=int(al*28)
  self.cv.coords(self.rng,cx-r,cy-r,cx+r,cy+r);self.cv.itemconfig(self.rng,outline=rgb(rv,rv,rv))
  g2,gg,gb=h2r("#a4c639");self.cv.coords(self.grn,gx-os_,gy-os_,gx+os_,gy+os_);self.cv.itemconfig(self.grn,fill=rgb(g2*al,gg*al,gb*al))
  rr2,rg,rb=h2r("#d70a53");self.cv.coords(self.red,rx-os_,ry-os_,rx+os_,ry+os_);self.cv.itemconfig(self.red,fill=rgb(rr2*al,rg*al,rb*al))
 def _p2(self,t):
  pt=cl((t-3)/3);ba=ez(pt/0.6) if pt<0.6 else 1.0
  br,bg2,bb=h2r("#0f52ba");self.cv.itemconfig(self.brd,fill=rgb(br*ba,bg2*ba,bb*ba))
  for i in(self.grn,self.red,self.spk,self.glo):self.cv.itemconfig(i,fill="#000000")
  self.cv.itemconfig(self.rng,outline="#000000")
  if pt>0.35:sv=int(ez((pt-0.35)/0.65)*136);self.cv.itemconfig(self.sub,fill=rgb(sv,sv,sv))
 def _p3(self):
  if not self.p3t:self.p3t=time.time()
  se=ez(cl((time.time()-self.p3t)/1.5))
  self.cv.coords(self.brd,self.cx,int(self.by0+(self.by1-self.by0)*se))
  self.cv.coords(self.sub,self.cx,int(self.sy0+(self.sy1-self.sy0)*se))
  gi=int((time.time()-self.p3t)/0.1)%len(GL);self.cv.itemconfig(self.brd,fill=GL[gi])
  self.cv.itemconfig(self.sub,fill="#888888")
  if se>0.5:
   la=ez((se-0.5)/0.5);lv=int(la*102);self.cv.itemconfig(self.lod,fill=rgb(lv,lv,lv))
   ds=int((time.time()-self.p3t)/0.5)%4
   for i,d in enumerate(self.dts):dv=int((102 if i<ds else 22)*la);self.cv.itemconfig(d,fill=rgb(dv,dv,dv))
   self.cv.itemconfig(self.lod,text=LOAD+("."*(ds%4)).ljust(3))
 def _fo(self):
  inv=cl(1-(time.time()-self.fos)/1.0);gi=int(time.time()*10)%len(GL)
  r2,g2,b2=h2r(GL[gi]);self.cv.itemconfig(self.brd,fill=rgb(r2*inv,g2*inv,b2*inv))
  sv=int(136*inv);self.cv.itemconfig(self.sub,fill=rgb(sv,sv,sv))
  lv=int(102*inv);self.cv.itemconfig(self.lod,fill=rgb(lv,lv,lv))
  for d in self.dts:self.cv.itemconfig(d,fill=rgb(lv,lv,lv))
  if inv<=0:self.destroy()
  else:self.after(16,self._fo)
if __name__=="__main__":S().mainloop()
