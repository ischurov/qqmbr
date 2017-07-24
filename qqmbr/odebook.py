# encoding: utf-8
#
# Helper functions for plotting of ode's
# Previously known as nesode
#
# Copyright (c) 2013-2016 Ilya V. Schurov, Andrey Petrin.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy
from scipy import integrate


def mquiver(xs, ys, v, **kw):
    """wrapper function for quiver
    xs and ys are arrays of x's and y's
    v is a function R^2 -> R^2, representing vector field
    kw are passed to quiver verbatim"""
    X,Y = np.meshgrid(xs, ys)
    V = [[v(x,y) for x in xs] for y in ys]
    VX = [[w[0] for w in q] for q in V]
    VY = [[w[1] for w in q] for q in V]
    plt.quiver(X, Y, VX, VY, **kw)

def dirfield(xs, ys, f, **kw):
    """
    wrapper function of mquiver that plots the direction field
    xs and ys are arrays of x's and y's
    f is a function R^2->R
    kw are passed to quiver verbatim
    """
    xs, ys = list(xs), list(ys) #in case something wrong was given
    mquiver(xs, ys, lambda x,y: (1,f(x,y)), scale=90, headwidth=0.0,
                    headlength=0.0,
                    headaxislength=0.0,pivot='middle',angles='xy',**kw)

def mplot(xs, f, **kw):
    """wrapper function for plot,
    xs is an array of x's
    f is a function R^1 -> R^1
    the rest of arguments are passed to plot"""
    plt.plot(xs, list(map(f,xs)), **kw)

def axes4x4(labels=("t","x"),xmin=-4, xmax=4, ymin=-4, ymax=4, fontsize=20):
    """Set axes to [-4,4]×[-4,4] and label them
    
    args
    ====
    - labels — axes labels (x, y)
    """
    plt.axis([xmin,xmax, ymin, ymax])
    center_spines()
    xscale = (xmax - xmin) / 8.
    yscale = (ymax - ymin) / 8.
    plt.text(xmax - 0.2 * xscale, 0.2 * yscale, "$%s$" % labels[0],
             fontsize=fontsize, verticalalignment='bottom')
    plt.text(0.1 * xscale, ymax - 0.3 * yscale, "$%s$" % labels[1],
             fontsize=fontsize)

def draw_axes(xmin, xmax, ymin, ymax, labels=("x", "y")):
    plt.axis([xmin, xmax, ymin, ymax])
    center_spines()
    plt.text(xmax, 0, "$%s$" % labels[0],fontsize=20, verticalalignment='bottom', horizontalalignment='right')
    plt.text(0, ymax, "$%s$" % labels[1],fontsize=20, verticalalignment='top', horizontalalignment='right')
def normdirfield(xs,ys,f,**kw):
    """
    plot normalized direction field
    
    kwargs
    ======
    
    - length is a desired length of the lines (default: 1)
    - the rest of kwards are passed to plot
    
    uses a trick with None delimeters in plot from 
    http://exnumerus.blogspot.ru/2011/02/how-to-quickly-plot-multiple-line.html
    """
    length= kw.pop('length') if 'length' in kw else 1
    xlist = []
    ylist = []
    for x in xs:
        for y in ys:
            vy = f(x,y)
            prelen = np.sqrt(1+vy**2)
            deltax = 1/prelen*length
            deltay = vy/prelen*length
            xlist.extend([x-deltax/2,x+deltax/2,None])
            ylist.extend([(-deltax/2)*vy+y,(deltax/2)*vy+y,None])
    plt.plot(xlist,ylist,**kw)

#center_spines and CenteredFormatter are adapted from
#http://stackoverflow.com/questions/4694478/center-origin-in-matplotlib/4718438#4718438
#by Joe Kington
#licensed under CC BY-SA

def center_spines(ax=None, centerx=0, centery=0):
    """Centers the axis spines at <centerx, centery> on the axis "ax", and
    places arrows at the end of the axis spines."""
    if ax is None:
        ax = plt.gca()

    # Set the axis's spines to be centered at the given point
    # (Setting all 4 spines so that the tick marks go in both directions)
    ax.spines['left'].set_position(('data', centerx))
    ax.spines['bottom'].set_position(('data', centery))
    ax.spines['right'].set_position(('data', centerx))
    ax.spines['top'].set_position(('data', centery))

    # Hide the line (but not ticks) for "extra" spines
    for side in ['right', 'top']:
        ax.spines[side].set_color('none')

    # On both the x and y axes...
    for axis, center in zip([ax.xaxis, ax.yaxis], [centerx, centery]):
        # Turn on minor and major gridlines and ticks
        axis.set_ticks_position('both')
        axis.grid(True, 'major', ls='solid', lw=0.5, color='gray')
#        axis.grid(True, 'minor', ls='solid', lw=0.1, color='gray')
        axis.set_minor_locator(mpl.ticker.AutoMinorLocator())

        # Hide the ticklabels at <centerx, centery>
        formatter = CenteredFormatter()
        formatter.center = center
        axis.set_major_formatter(formatter)

    # Add offset ticklabels at <centerx, centery> using annotation
    # (Should probably make these update when the plot is redrawn...)
    xlabel, ylabel = map(formatter.format_data, [centerx, centery])
    if centerx != 0 or centery != 0:
        annotation = '(%s, %s)' % (xlabel, ylabel)
    else:
        annotation = xlabel
    ax.annotate(annotation, (centerx, centery),
            xytext=(-4, -4), textcoords='offset points',
            ha='right', va='top')
 
class CenteredFormatter(mpl.ticker.ScalarFormatter):
    """Acts exactly like the default Scalar Formatter, but yields an empty
    label for ticks at "center"."""
    center = 0
    def __call__(self, value, pos=None):
        if value == self.center:
            return ''
        else:
            return mpl.ticker.ScalarFormatter.__call__(self, value, pos)


def eulersplot(f, xa, xb, ya, n = 500, toolarge = 1E10, **kw):
    """plots numerical solution y'=f

    args
    ====

    - f(x,y): a function in rhs
    - xa: initial value of independent variable
    - xb: final value of independent variable
    - ya: initial value of dependent variable
    - n : number of steps (higher the better)
    """
    h = (xb - xa) / float(n)
    x = [xa] 
    y = [ya]
    for i in range(1,n+1):
        newy = y[-1] + h * f(x[-1], y[-1])
        if abs(newy) > toolarge:
            break
        y.append(newy)
        x.append(x[-1] + h)
    plt.plot(x,y, **kw)


def normvectorfield(xs,ys,fs,**kw):
    """
    plot normalized vector field
    
    kwargs
    ======
    
    - length is a desired length of the lines (default: 1)
    - the rest of kwards are passed to plot
    """
    length = kw.pop('length') if 'length' in kw else 1
    x, y = np.meshgrid(xs, ys)
    # calculate vector field
    vx,vy = fs(x,y)
    # plot vecor field
    norm = length /np.sqrt(vx**2+vy**2)
    plt.quiver(x, y, vx * norm, vy * norm, angles='xy',**kw)


def vectorfield(xs,ys,fs,**kw):
    """
    plot vector field (no normalization!)

    args
    ====
    fs is a function that returns tuple (vx,vy)
    
    kwargs
    ======
    
    - length is a desired length of the lines (default: 1)
    - the rest of kwards are passed to plot
    """
    length= kw.pop('length') if 'length' in kw else 1
    x, y=np.meshgrid(xs, ys)
    # calculate vector field
    vx,vy=fs(x,y)
    # plot vecor field
    norm = length 
    plt.quiver(x, y, vx * norm, vy * norm, angles='xy',**kw)


def plottrajectories(fs, x0, t=np.linspace(1,400,10000), **kw):
    """
    plots trajectory of the solution
    
    f  -- must accept an array of X and t=0, and return a 2D array of \dot y and \dot x
    x0 -- vector
    
    Example
    =======

    plottrajectories(lambda X,t=0:array([ X[0] -   X[0]*X[1] ,
                   -X[1] + X[0]*X[1] ]), [ 5,5], color='red')
    """
    x0 = np.array(x0)
    #f = lambda X,t=0: array(fs(X[0],X[1]))
    #fa = lambda X,t=0:array(fs(X[0],X[1]))
    X = integrate.odeint( fs, x0, t)
    plt.plot(X[:,0], X[:,1], **kw)


def phaseportrait(fs, inits, t=(-5, 5), n=100, firstint=None, arrow=True,
                  xmin=None, ymin=None, xmax=None, ymax=None, 
                  head_width = 0.13, 
                  head_length=0.3, arrow_size=1, singpoint_size=0, 
                  singcolor='steelblue', contourcolor='steelblue', **kw):
    """
    plots phase portrait of the differential equation (\dot x,\dot y)=fs(x,y)

    fs  -- must accept an array X=(x, y), and return a 2D array of \dot y and \dot x
    firstint -- first integral function, must accept an array X=(x, y) and
        return real number. If specified, no integration of equation will be
        performed. Instead, contours of firstint will be drawn. fs will be used
        to draw vectors. xmin, xmax, ymin, ymax should be specified
    inits -- list of vectors representing inital conditions
    t -- is either a tuple (tmin, tmax), where tmin <= 0 and tmax >= 0,
         or scalar; in the latter case, tmin = 0, tmax = t
    n -- number of points

    Example
    =======
    
    from itertools import product
    phaseportrait(lambda X: array([X[0],2*X[1]]), product(linspace(-4,4,15),linspace(-4,4,15)), [-2,0.3], n=20)
    """
    try:
        tmin = t[0]
        tmax = t[1]
        assert tmin <= 0 and tmax >= 0 
    except TypeError:
        tmin = 0
        tmax = t
    head_width *= arrow_size
    head_length *= arrow_size

    points = []
    inits = np.array(inits)
    integrator = integrate.ode(lambda t, X: fs(X)).set_integrator('vode')
    if firstint is None:
        for x0 in inits:
            if tmin < 0:
                segments=[(tmin, tmin/n), (tmax, tmax/n)]
            else:
                segments=[(tmax, tmax/n)]
            
            for T, delta_t in segments:
                integrator.set_initial_value(x0)
                points.append(x0)
                sign = np.sign(delta_t)
                
                while (sign * integrator.t < sign * T):
                    point = integrator.integrate(integrator.t + delta_t)
                    if not integrator.successful():
                        break
                    if ((xmin is not None and point[0] < xmin) or
                        (xmax is not None and point[0] > xmax) or
                        (ymin is not None and point[1] < ymin) or
                        (ymax is not None and point[1] > ymax)):
                        point = [None, None]
                    points.append(point)
                points.append([None, None])
        points = np.array(points)
        plt.plot(points[:, 0], points[:, 1],**kw)
    else:
        assert None not in [xmin, xmax, ymin, ymax], \
                ("Please, specify xmin, xmax, ymin, ymax "
                 "if you use first integral")
        X = np.linspace(xmin, xmax, n * 10)
        Y = np.linspace(xmin, xmax, n * 10)
        # Z = np.array([[firstint(np.array([x, y])) for x in X] for y in Y])
        try:
            Z = firstint(np.meshgrid(X, Y))
            # fast version for ufunc-compatible firstint
        except:
            Z = np.array([[firstint(np.array([x, y])) for x in X] for y in Y])
            # fallback if something goes wrong
        levels = sorted({firstint(x0) for x0 in inits})
        plt.contour(X, Y, Z, levels=levels, colors=contourcolor)
        
    for x0 in inits:
        vector = np.array(fs(x0))
        if arrow:
            if scipy.linalg.norm(vector) > 1E-5:
                direction = vector / scipy.linalg.norm(vector) * 0.01
            else:
                direction = None
            if 'color' in kw:
                arrow_params = dict(fc=kw['color'],
                                    ec=kw['color'])
            else:
                arrow_params = {}
            if direction is not None:
                plt.arrow(x0[0] - direction[0],
                          x0[1] - direction[1],
                          direction[0],
                          direction[1], 
                          head_width=head_width, 
                          head_length=head_length, 
                          lw=0.0, **arrow_params)
            else:
                plt.plot([x0[0]], [x0[1]], 
                         marker='o', mew=2 * singpoint_size, 
                         lw=0, markersize=5 * singpoint_size,
                         markerfacecolor='white', markeredgecolor=singcolor)




def mcontour(xs, ys, fs, levels=None, **kw):
    """
    wrapper function for contour

    example
    ======
    mcontour(linspace(-4,4),linspace(-4,4),lambda x,y: x*y)
    """
    x,y=np.meshgrid(xs,ys)
    z=fs(x,y)
    if levels!=None:
        plt.contour(x,y,z,sorted(set(levels)),**kw)
    else:
        plt.contour(x,y,z,**kw)

def get_default(from_, **kwargs):
    return {k:from_.get(k, v) for k, v in kwargs.items()}

def onedim_phasecurves(left, right, singpoints, directions, 
                       orientation='vertical', shift=0, 
                       delta=0.05, **kwargs):
    """
    Draws phase curves of one-directional vector field;
    left and right are borders
    singpoints is a list of singular points (equilibria)
    directions is a list of +1 and -1 that gives a direction

    Example:


    plt.ylim(-4, 4)
    plt.xlim(-4, 4)
    onedim_phasecurves(-4, 4, [-1, 1], [1, -1, 1], orientation='horizontal', 
                       shift=1)

    """
    assert len(directions) == len(singpoints) + 1
    assert orientation in ['vertical', 'horizontal']
    n = len(singpoints)
    defaultcolor = 'Teal'
    plot_params = get_default(kwargs, color=defaultcolor, marker='o', 
                       fillstyle='none', mew=5, lw=0, markersize=2)
    quiver_params = dict(angles='xy', 
                         scale_units='xy', scale=1, units='inches')
    quiver_params.update(get_default(kwargs, width=0.03, 
                                      color=defaultcolor))

    baseline = np.zeros(n) + shift
    if orientation == 'vertical':
        plt.plot(baseline, singpoints, **plot_params)
    else:
        plt.plot(singpoints, baseline, **plot_params)

    # We have to process special case when left or right border is singular
    # move them to special list lonesingpoints to process later
    if singpoints:
        if singpoints[0] == left:
            singpoints.pop(0)
            directions.pop(0)
            n -= 1
    if singpoints:
        if singpoints[-1] == right:
            singpoints.pop()
            directions.pop()
            n -= 1

    xs = np.zeros(n + 1) + shift
    ys = []
    us = np.zeros(n + 1)
    vs = []

    
    endpoints = [left] + list(singpoints) + [right]
    for i, direction in enumerate(directions):
        if direction > 0:
            beginning = endpoints[i]
            ending = endpoints[i+1]
        elif direction < 0:
            beginning = endpoints[i+1]
            ending = endpoints[i]
        else:
            raise Exception("direction should be >0 or <0")
        ys.append(beginning + np.sign(direction) * delta)
        vs.append(ending - beginning - np.sign(direction)*2*delta)
    if orientation == 'vertical':
        plt.quiver(xs, ys, us, vs, **quiver_params, **kwargs)
    else:
        plt.quiver(ys, xs, vs, us, **quiver_params, **kwargs)

