import os 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import random 
def processing(M):
    #total=0
    L=[]
    H=[]
    for i in M:
        L.append(float(i))
#            L.append(int(9999999999))
    return L
g = os.walk("test_KVM_13_8_nonovercommit_hyperthreading")
g = os.walk("ht_only_time_ns")
ref=[]
files=[]
for path,dir_list,file_list in g:  
    for file_name in file_list:  
        out = (os.path.join(path, file_name) )
        files.append(out)
        out = out.split('/')
        ref.append(out[1:])

timectxsw=[[] for i in range(8)]
timetctxsw=[[] for i in range(8)]
timetctxsw2=[[] for i in range(8)]
timesyscall=[[] for i in range(8)]
for i,j in zip(ref,files):
    index=i[0]
    exactly=i[2]
   # print(index, i[1], exactly)
    f = open(j)
    tmp = (f.read().splitlines())
    tmp = processing(tmp)
    if exactly == "timetctxsw2.out":
        timetctxsw2[int(index)-1].extend(tmp)
    elif exactly == "timetctxsw.out":
        timetctxsw[int(index)-1].extend(tmp)
    elif exactly == "timectxsw.out":
        timectxsw[int(index)-1].extend(tmp)
    else:
        timesyscall[int(index)-1].extend(tmp)
    f.close()
"""
print("timetctxsw2")
for i in timetctxsw2:
    print(len(i))
print("timetctxsw")
for i in timetctxsw:
    print(len(i))
print("timectxsw")
for i in timectxsw:
    print(len(i))
print("timetctxsw2")
for i in timesyscall:
    print(len(i))
"""
_timectxsw=np.array(timectxsw)
_timetctxsw=np.array(timetctxsw)
_timetctxsw2=np.array(timetctxsw2)
_timesyscall=np.array(timesyscall)

timectxsw=pd.DataFrame(data=_timectxsw.T,columns=list(range(0,8)))
timetctxsw=pd.DataFrame(data=_timetctxsw.T,columns=list(range(0,8)))
timetctxsw2=pd.DataFrame(data=_timetctxsw2.T,columns=list(range(0,8)))
timesyscall=pd.DataFrame(data=_timesyscall.T,columns=list(range(0,8)))

print("timectxsw.mean")
for i in timectxsw.mean():
    print(i)
print("timetctxsw.mean")
for i in timetctxsw.mean():
    print(i)
print("timetctxsw2.mean")
for i in timetctxsw2.mean():
    print(i)
print("timesyscall.mean")
for i in timesyscall.mean():
    print(i)



timectxsw=pd.DataFrame(data=_timectxsw.T,columns=list(range(1,9)))
ax = sns.violinplot(data=timectxsw,scale='area')
timectxsw=pd.DataFrame(data=_timectxsw.T,columns=list(range(0,8)))
sns.lineplot(data=timectxsw.mean())
plt.savefig('pdf_13_4_ht/timectxsw.pdf')
plt.clf()

timetctxsw=pd.DataFrame(data=_timetctxsw.T,columns=list(range(1,9)))
ax = sns.violinplot(data=timetctxsw)
timetctxsw=pd.DataFrame(data=_timetctxsw.T,columns=list(range(0,8)))
sns.lineplot(data=timetctxsw.mean())
plt.savefig('pdf_13_4_ht/timetctxsw.pdf')
plt.clf()

timetctxsw2=pd.DataFrame(data=_timetctxsw2.T,columns=list(range(1,9)))
ax = sns.violinplot(data=timetctxsw2)
timetctxsw2=pd.DataFrame(data=_timetctxsw2.T,columns=list(range(0,8)))
sns.lineplot(data=timetctxsw2.mean())
plt.savefig('pdf_13_4_ht/timetctxsw2.pdf')
plt.clf()

timesyscall=pd.DataFrame(data=_timesyscall.T,columns=list(range(1,9)))
ax = sns.violinplot(data=timesyscall)
timesyscall=pd.DataFrame(data=_timesyscall.T,columns=list(range(0,8)))
sns.lineplot(data=timesyscall.mean())
plt.savefig('pdf_13_4_ht/timesyscall.pdf')
plt.clf()
#print(processing(output[3][0]))
'''
r=[]
for i in output:
    for j in i:
        r.append(processing(j))
for i in range(0,len(r)):
    if i % 4 ==0 and i != 0:
        print("")
    print(r[i][0],",",r[i][1],",",r[i][2])
'''

