#!/usr/bin/env python

"""
Script to plot rise and set times for QUOCKA sources
Hard coded to accept csv files used for scheduling
Could be adapted later to make it more general ...

V1 GHH 26 December 2018
"""

import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import numpy as np
import matplotlib.pyplot as plt
import argparse

# Stuff for updating plot with hover action derived from answer here:
# https://stackoverflow.com/questions/7908636/possible-to-make-labels-appear-when-hovering-over-a-point-in-matplotlib

def update_annot(ind,annot,ll,name):
    x,y = ll.get_data()
    annot.xy = (x[ind["ind"][0]].value, y[ind["ind"][0]].value)
    annot.set_text(name)
    annot.get_bbox_patch().set_alpha(0.4)


def hover(event,fig,ax,annot,all_lines,names):
    vis = annot.get_visible()
    if event.inaxes == ax:
	for i,ll in enumerate(all_lines):
        	cont, ind = ll.contains(event)
        	if cont:
            		update_annot(ind,annot,ll,names[i])
            		annot.set_visible(True)
            		fig.canvas.draw_idle()
        	else:
            		if vis:
                		annot.set_visible(False)
                		fig.canvas.draw_idle()

def main(args):

	if args.noplot:
		show_plots = False
	else:
		show_plots = True
	date = args.date+' 00:00:00'
	if args.aest:
		work_in_utc = False
	else:
		work_in_utc = True

	ATCA = EarthLocation(lat=-30.3128846*u.deg, lon=149.5501388*u.deg, height=236.87*u.m)
	if work_in_utc:
		utoffset = 0.*u.hour
		timezone = 'UTC'
	else:
		utoffset = 10*u.hour
		timezone = 'AEST'

	print 'Creating source list'
	sources = {}
	for line in open(args.csvfile):
		if line[0]==',': continue
		sline = line.split()[0].split(',')
		sources[sline[2]]=[float(sline[3]),float(sline[4]),sline[6],line]
	print 'Working with',len(sources.keys()),'sources'

	midnight = Time(date) - utoffset
	delta_midnight = np.linspace(0,24,1500)*u.hour # time resolution of ~ 1 minute
	taxis = midnight + delta_midnight
	taxis.delta_ut1_utc = 0.
	lst = taxis.sidereal_time('apparent',ATCA.longitude)
	sind = np.argsort(lst)
	sorted_lst = lst[sind]
	sorted_taxis = taxis[sind]
	frame = AltAz(obstime=sorted_taxis, location=ATCA)

	sortdict = {}
	risedict = {}
	setlist = []

	print 'Looking at each source individually'
	print 'Reporting rise,set times in LST for elevation=%f'%(args.elevation)
	outfile = open('poltimes.txt','w')
	all_lines = []
	names = sorted(sources.keys())
	for source in names:
		s = sources[source]
		c = SkyCoord(s[0],s[1],unit='deg')
		altaz = c.transform_to(frame)
		sdalt = np.sign(altaz.alt - args.elevation*u.deg)
		jumps = np.diff(sdalt)
		setind=np.where(jumps==-2) # should only be one
		riseind = np.where(jumps==2) # should only be one
		assert(len(setind)==1)
		assert(len(riseind)==1)
		setind = setind[0]+1
		riseind = riseind[0]+1
		settime = sorted_taxis[setind]
		setlst = sorted_lst[setind]
		setlst.format = 'iso'
		risetime = sorted_taxis[riseind]
		riselst = sorted_lst[riseind]
		riselst.format='iso'
		print source,riselst[0],setlst[0]
		print >>outfile, source,riselst[0],setlst[0]
		sortdict[source] = setlst[0]
		risedict[source] = riselst[0]
		setlist.append(setlst.hour)
		if show_plots:
			l = plt.plot(sorted_lst, altaz.alt, 'k-', alpha=0.3)
			all_lines.append(l[0])
			plt.plot(riselst,20.,'g.',markersize=3,alpha=0.3)
			plt.plot(setlst,20.,'r.',markersize=3,alpha=0.3)

	outfile.close()

	sortout = open('poltimes_sorted_by_set.txt','w')
	print 'Reporting rise,set times in LST (sorted by set time)'
	for key,val in sorted(sortdict.iteritems(), key=lambda (k,v): (v,k)):
		print key,'rise',risedict[key],'set',val
		print >>sortout, sources[key][-1][:-1]
	sortout.close()

	if show_plots: 
		plt.fill_between(sorted_lst,0,20,color='0.75',zorder=0)
		plt.fill_between(sorted_lst,0,12,color='0.5',zorder=0)
		plt.axhline(args.elevation,color='black',zorder=0)
		plt.ylim(0,90)
		plt.xlim(0,24)
		plt.xlabel('LST')
		plt.ylabel('Altitude (deg)')
		print 'Plotting elevations vs LST ...'
		plt.savefig('source_uptimes.png',bbox_inches='tight',dpi=150)
		ax = plt.gca()
		annot = ax.annotate("", xy=(0,0), xytext=(-20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->"))
		annot.set_visible(False)
		fig = plt.gcf()
		fig.canvas.mpl_connect("motion_notify_event", lambda event: hover(event,fig,ax,annot,all_lines,names))
		plt.show()
		print 'Plotting histogram ...'
		plt.hist(np.array(setlist),bins=np.linspace(0.,24.,97))
		plt.xlabel('LST (bin width 15min)')
		plt.ylabel('Number of sources setting')
		plt.savefig('source_sethist.png',bbox_inches='tight',dpi=150)
		plt.show()

ap = argparse.ArgumentParser()
ap.add_argument('csvfile',help='Input CSV file name, must be QUOCKA formatted')
ap.add_argument('date',help='Date to use for calculations [format yyyy-mm-dd]')
ap.add_argument('--aest','-a',help='Work in AEST times instead of UTC? [default False]',action='store_true')
ap.add_argument('--noplot','-n',help='Suppress plots? [default False]',action='store_true')
ap.add_argument('--elevation','-e',help='Elevation value to treat as horizon [default 20]',default=20.,type=float)
args = ap.parse_args()
main(args)

